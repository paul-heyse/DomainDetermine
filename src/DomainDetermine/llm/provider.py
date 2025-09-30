"""LLM provider abstractions backed by Triton TensorRT-LLM endpoints."""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping, MutableMapping, Optional, Sequence

import httpx

from DomainDetermine.governance import ArtifactRef, GovernanceEventLog, log_llm_observability_alert

from .observability import LLMObservability
from .tokenizer import TokenizerInfoCache


@dataclass(slots=True)
class ProviderConfig:
    """Configuration for the Triton-based LLM provider."""

    endpoint: str
    model_name: str
    tokenizer_dir: Path
    engine_hash: str
    quantisation: str
    cache_dir: Optional[Path] = None
    timeout: float = 30.0
    observability: Optional[LLMObservability] = None
    template_costs: Optional[Mapping[str, float]] = None
    price_per_token: Optional[float] = None
    readiness_thresholds: Mapping[str, float] = field(default_factory=dict)
    governance_log: Optional[GovernanceEventLog] = None
    governance_artifact: Optional[ArtifactRef] = None
    governance_actor: str = "llm-runtime"


class TritonLLMProvider:
    """High-level client for interacting with the Triton TensorRT-LLM backend."""

    def __init__(self, config: ProviderConfig, *, client: Optional[httpx.Client] = None) -> None:
        self._config = config
        self._client = client or httpx.Client(timeout=config.timeout)
        self._logger = logging.getLogger("DomainDetermine.llm.provider")
        self._tokenizer_cache = TokenizerInfoCache(config.tokenizer_dir, cache_dir=config.cache_dir)
        self._observability = config.observability

    @property
    def config(self) -> ProviderConfig:
        return self._config

    def generate_json(
        self,
        schema: Mapping[str, Any],
        prompt: str,
        *,
        schema_id: str,
        max_tokens: int = 256,
    ) -> Mapping[str, Any]:
        info_path = str(self._tokenizer_cache.get_or_create())
        payload = {
            "inputs": prompt,
            "parameters": {
                "guided_decoding_backend": "xgrammar",
                "guided_decoding": {
                    "type": "json_schema",
                    "schema": schema,
                    "xgrammar_tokenizer_info_path": info_path,
                },
                "max_tokens": max_tokens,
                "temperature": 0.0,
                "return_perf_metrics": True,
            },
        }
        response = self._invoke("generate_json", payload, schema_id=schema_id)
        return json.loads(response["text"][0])

    def rank_candidates(self, payload: Mapping[str, Any]) -> Mapping[str, Any]:
        request_payload = {
            "inputs": json.dumps(payload),
            "parameters": {
                "max_tokens": 1,
                "temperature": 0.0,
                "return_perf_metrics": True,
            },
        }
        response = self._invoke("rank_candidates", request_payload)
        return json.loads(response["text"][0])

    def judge(
        self,
        prompt: str,
        reference: Optional[str] = None,
        *,
        max_tokens: int = 512,
    ) -> Mapping[str, Any]:
        full_prompt = prompt
        if reference:
            full_prompt = f"{prompt}\n\nReference:\n{reference}"
        payload = {
            "inputs": full_prompt,
            "parameters": {
                "max_tokens": max_tokens,
                "temperature": 0.1,
                "top_p": 0.9,
                "return_perf_metrics": True,
            },
        }
        response = self._invoke("judge", payload)
        return {
            "text": response["text"][0],
            "metadata": self._extract_perf_metrics(response),
        }

    def warmup(
        self,
        schema: Mapping[str, Any],
        prompts: Sequence[str],
        *,
        schema_id: str,
        max_tokens: int = 32,
    ) -> None:
        for prompt in prompts:
            result = self.generate_json(schema, prompt, schema_id=schema_id, max_tokens=max_tokens)
            if not isinstance(result, Mapping):
                msg = "Warm-up response is not a mapping"
                raise RuntimeError(msg)

    def _invoke(
        self,
        operation: str,
        payload: Mapping[str, Any],
        *,
        schema_id: Optional[str] = None,
    ) -> Mapping[str, Any]:
        request = {
            "model_name": self._config.model_name,
            "inputs": payload["inputs"],
            "parameters": payload.get("parameters", {}),
        }
        headers = {
            "Content-Type": "application/json",
            "X-Engine-Hash": self._config.engine_hash,
            "X-Quantisation": self._config.quantisation,
        }
        url = f"{self._config.endpoint}/v2/models/{self._config.model_name}/infer"
        start = time.perf_counter()
        response = self._client.post(url, json=request, headers=headers)
        elapsed_ms = (time.perf_counter() - start) * 1000.0
        response.raise_for_status()
        payload_json = response.json()
        self._log_request(operation, payload_json, elapsed_ms, schema_id=schema_id)
        return payload_json

    def _build_enum_grammar(self, candidates: list[str]) -> str:
        escaped = [candidate.replace('"', '\\"') for candidate in candidates]
        grammar_body = " | ".join(f'"{value}"' for value in escaped)
        return f"start ::= {grammar_body}"

    def _extract_perf_metrics(self, response: Mapping[str, Any]) -> Mapping[str, Any]:
        perf = response.get("perf_metrics")
        if isinstance(perf, Mapping):
            return perf
        metadata = response.get("metadata")
        if isinstance(metadata, Mapping):
            perf = metadata.get("perf_metrics")
            if isinstance(perf, Mapping):
                return perf
        return {}

    def _log_request(
        self,
        operation: str,
        response: Mapping[str, Any],
        duration_ms: float,
        *,
        schema_id: Optional[str],
    ) -> None:
        perf = self._extract_perf_metrics(response)
        queue_delay = self._coerce_number(perf.get("queue_delay_us"))
        tokens_in = self._coerce_number(
            perf.get("tokens_in")
            or perf.get("prompt_tokens")
            or perf.get("input_tokens")
        )
        tokens_out = self._coerce_number(
            perf.get("tokens_out")
            or perf.get("completion_tokens")
            or perf.get("output_tokens")
        )
        kv_metrics = perf.get("kv_cache") if isinstance(perf.get("kv_cache"), Mapping) else {}
        speculative = perf.get("speculative") if isinstance(perf.get("speculative"), Mapping) else {}
        error_code: Optional[str] = None
        if isinstance(response.get("error"), Mapping):
            error_code = str(response["error"].get("code"))
        cost = self._calculate_cost(operation, tokens_in, tokens_out, schema_id)
        log_payload: MutableMapping[str, Any] = {
            "event": "llm.request",
            "operation": operation,
            "model": self._config.model_name,
            "engine_hash": self._config.engine_hash,
            "quantisation": self._config.quantisation,
            "schema_id": schema_id,
            "duration_ms": round(duration_ms, 3),
            "queue_delay_us": queue_delay,
            "tokens_in": tokens_in,
            "tokens_out": tokens_out,
            "kv_cache_reuse": kv_metrics,
            "speculative": speculative,
            "cost_usd": cost,
            "error_code": error_code,
        }
        if queue_delay is not None:
            overrun = self._check_threshold("max_queue_delay_us", queue_delay)
            log_payload["queue_delay_budget_overrun"] = overrun
            if overrun:
                self._log_threshold_warning(
                    "Queue delay threshold exceeded",
                    {
                        "operation": operation,
                        "schema_id": schema_id,
                        "queue_delay_us": queue_delay,
                        "threshold": float(self._config.readiness_thresholds.get("max_queue_delay_us", 0.0)),
                    },
                )
                self._record_governance_alert(
                    reason="queue_delay",
                    payload={
                        "operation": operation,
                        "schema_id": schema_id,
                        "queue_delay_us": queue_delay,
                        "threshold": self._config.readiness_thresholds.get("max_queue_delay_us"),
                    },
                )

        if tokens_in is not None or tokens_out is not None:
            total_tokens = (tokens_in or 0.0) + (tokens_out or 0.0)
            overrun = self._check_threshold("max_tokens", total_tokens)
            log_payload["token_budget_overrun"] = overrun
            if overrun:
                self._log_threshold_warning(
                    "Token budget threshold exceeded",
                    {
                        "operation": operation,
                        "schema_id": schema_id,
                        "tokens_total": total_tokens,
                        "threshold": float(self._config.readiness_thresholds.get("max_tokens", 0.0)),
                    },
                )
                self._record_governance_alert(
                    reason="token_budget",
                    payload={
                        "operation": operation,
                        "schema_id": schema_id,
                        "tokens_total": total_tokens,
                        "threshold": self._config.readiness_thresholds.get("max_tokens"),
                    },
                )
        self._logger.info("llm.request", extra={"llm": log_payload})
        if self._observability:
            self._observability.record_request(log_payload)

    @staticmethod
    def _coerce_number(value: Any) -> Optional[float]:
        if value is None:
            return None
        if isinstance(value, (int, float)):
            return float(value)
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    def _calculate_cost(
        self,
        operation: str,
        tokens_in: Optional[float],
        tokens_out: Optional[float],
        schema_id: Optional[str],
    ) -> Optional[float]:
        pricing = self._config.price_per_token
        if pricing is None:
            return None
        total_tokens = 0.0
        if isinstance(tokens_in, (int, float)):
            total_tokens += float(tokens_in)
        if isinstance(tokens_out, (int, float)):
            total_tokens += float(tokens_out)
        if total_tokens == 0.0:
            return None
        cost = pricing * total_tokens
        template_costs = self._config.template_costs or {}
        if schema_id and schema_id in template_costs:
            cost = template_costs[schema_id]
        budget = self._config.readiness_thresholds.get("max_cost_usd")
        if isinstance(budget, (int, float)) and cost > float(budget):
            self._logger.warning(
                "llm.cost.threshold_exceeded",
                extra={
                    "llm": {
                        "operation": operation,
                        "schema_id": schema_id,
                        "cost_usd": cost,
                        "budget_usd": float(budget),
                    }
                },
            )
            self._record_governance_alert(
                reason="cost_budget",
                payload={
                    "operation": operation,
                    "schema_id": schema_id,
                    "cost_usd": cost,
                    "budget_usd": float(budget),
                },
            )
        return round(cost, 6)

    def _check_threshold(self, key: str, value: float) -> bool:
        threshold = self._config.readiness_thresholds.get(key)
        if isinstance(threshold, (int, float)):
            return value > float(threshold)
        return False

    def _log_threshold_warning(self, message: str, data: Mapping[str, Any]) -> None:
        payload = {"warning": message, **data}
        self._logger.warning("llm.threshold_exceeded", extra={"llm": payload})

    def _record_governance_alert(self, reason: str, payload: Mapping[str, Any]) -> None:
        if not (self._config.governance_log and self._config.governance_artifact):
            return
        if isinstance(payload, dict):
            event_payload: Mapping[str, object] = {**payload, "reason": reason}
        else:
            event_payload = {"reason": reason, "details": dict(payload)}
        log_llm_observability_alert(
            self._config.governance_log,
            self._config.governance_artifact,
            self._config.governance_actor,
            event_payload,
        )
