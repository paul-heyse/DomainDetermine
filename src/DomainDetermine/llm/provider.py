"""LLM provider abstractions backed by Triton TensorRT-LLM endpoints."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Optional

import httpx


@dataclass(slots=True)
class ProviderConfig:
    """Configuration for the Triton-based LLM provider."""

    endpoint: str
    model_name: str
    tokenizer_dir: Path
    engine_hash: str
    quantisation: str


class TritonLLMProvider:
    """High-level client for interacting with the Triton TensorRT-LLM backend."""

    def __init__(self, config: ProviderConfig) -> None:
        self._config = config
        self._client = httpx.Client(timeout=30.0)

    @property
    def config(self) -> ProviderConfig:
        return self._config

    def generate_json(self, schema: Mapping[str, Any], prompt: str, max_tokens: int = 256) -> Mapping[str, Any]:
        payload = {
            "inputs": prompt,
            "parameters": {
                "guided_decoding_backend": "xgrammar",
                "guided_decoding": {
                    "type": "json_schema",
                    "schema": schema,
                },
                "max_tokens": max_tokens,
                "temperature": 0.0,
                "return_perf_metrics": True,
            },
        }
        response = self._invoke(payload)
        return json.loads(response["text"][0])

    def rank_candidates(self, prompt: str, candidates: list[str]) -> Mapping[str, Any]:
        grammar = self._build_enum_grammar(candidates)
        payload = {
            "inputs": prompt,
            "parameters": {
                "guided_decoding_backend": "xgrammar",
                "guided_decoding": {
                    "type": "ebnf",
                    "grammar": grammar,
                },
                "max_tokens": 32,
                "temperature": 0.0,
            },
        }
        response = self._invoke(payload)
        return {
            "selection": response["text"][0],
            "metadata": response.get("perf_metrics", {}),
        }

    def judge(self, prompt: str, reference: Optional[str] = None, max_tokens: int = 512) -> Mapping[str, Any]:
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
        response = self._invoke(payload)
        return {
            "text": response["text"][0],
            "metadata": response.get("perf_metrics", {}),
        }

    def _invoke(self, payload: Mapping[str, Any]) -> Mapping[str, Any]:
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
        response = self._client.post(f"{self._config.endpoint}/v2/models/{self._config.model_name}/infer", json=request, headers=headers)
        response.raise_for_status()
        return response.json()

    def _build_enum_grammar(self, candidates: list[str]) -> str:
        escaped = [candidate.replace('"', '\"') for candidate in candidates]
        grammar_body = " | ".join(f'"{value}"' for value in escaped)
        return f"start ::= {grammar_body}"
