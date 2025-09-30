"""Runtime configuration for prompt templates."""

from __future__ import annotations

import json
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Dict, Mapping, Sequence

import jsonschema

from .loader import PromptTemplateLoader, TemplateRecord
from .metrics import MetricsRepository
from .validators import PromptQualityValidator, ValidationResult


@dataclass(frozen=True)
class RetrievalPolicy:
    """Defines retrieval and citation rules for a template."""

    allowed_sources: Sequence[str]
    prompt_budget: int
    completion_budget: int
    require_citations: bool
    filter_terms: Sequence[str] = ()


@dataclass(frozen=True)
class TemplateRuntime:
    """Runtime data needed to execute a prompt template."""

    template_id: str
    version: str
    schema: Mapping[str, object]
    schema_id: str
    policy: RetrievalPolicy
    max_tokens: int
    token_budget: int
    template_record: TemplateRecord

    @property
    def qualified_id(self) -> str:
        return f"{self.template_id}:{self.version}"


class PromptRuntimeManager:
    """Loads runtime manifests and renders prompts with policy enforcement."""

    def __init__(
        self,
        root: Path,
        metrics: MetricsRepository | None = None,
        quality_validator: PromptQualityValidator | None = None,
    ) -> None:
        self._root = root
        self._loader = PromptTemplateLoader(root)
        self._templates: Dict[str, TemplateRuntime] = {}
        self._metrics = metrics or MetricsRepository()
        self._warmup_status: Dict[str, bool] = {}
        self._manifest_metadata: Dict[str, object] = {}
        self._validator = quality_validator or PromptQualityValidator()
        manifest_path = root / "runtime_manifest.json"
        if manifest_path.exists():
            self._load_manifest(manifest_path)

    @property
    def manifest_metadata(self) -> Mapping[str, object]:
        return dict(self._manifest_metadata)

    def register_template(self, runtime: TemplateRuntime) -> None:
        self._templates[runtime.qualified_id] = runtime
        self._warmup_status.setdefault(runtime.qualified_id, False)
        metrics = self._metrics.get(runtime.template_id, runtime.version)
        metrics.record("warmup_status", float(self._warmup_status[runtime.qualified_id]))
        self._metrics.upsert(metrics)

    def set_warmup_status(self, template_id: str, version: str, healthy: bool) -> None:
        self._warmup_status[f"{template_id}:{version}"] = healthy
        metrics = self._metrics.get(template_id, version)
        metrics.record("warmup_status", float(healthy))
        self._metrics.upsert(metrics)

    def get_warmup_status(self, template_id: str, version: str) -> bool:
        return self._warmup_status.get(f"{template_id}:{version}", False)

    def _load_manifest(self, path: Path) -> None:
        data = json.loads(path.read_text(encoding="utf-8"))
        self._manifest_metadata = {
            "version": data.get("version"),
            "generated_at": data.get("generated_at"),
            "provenance": data.get("provenance"),
        }
        records = list(self._loader.discover())
        record_cache: Dict[tuple[str, str], TemplateRecord] = {}
        for record in records:
            metadata = record.load_metadata()
            key = (metadata.get("template_id"), metadata.get("version"))
            record_cache[key] = record
        templates = data.get("templates", [])
        for entry in templates:
            template_id = entry["id"]
            version = entry["version"]
            schema_ref = entry.get("schema", {})
            schema_name = schema_ref.get("name")
            schema_version = schema_ref.get("version")
            schema_path = self._root / "schemas" / f"{schema_name}_{schema_version}.schema.json"
            if not schema_path.exists():
                raise FileNotFoundError(f"Schema file not found for {template_id}:{version}: {schema_path}")
            schema = json.loads(schema_path.read_text(encoding="utf-8"))
            policy_id = entry.get("policy_id")
            policy_path = self._root / "policies" / f"{policy_id}.policy.json"
            if not policy_path.exists():
                raise FileNotFoundError(f"Policy file not found for {template_id}:{version}: {policy_path}")
            policy_data = json.loads(policy_path.read_text(encoding="utf-8"))
            runtime_policy = RetrievalPolicy(
                allowed_sources=tuple(policy_data.get("allowed_sources", [])),
                prompt_budget=int(policy_data.get("token_budget", {}).get("prompt", entry.get("token_budget", 4096))),
                completion_budget=int(policy_data.get("token_budget", {}).get("completion", entry.get("max_tokens", 256))),
                require_citations=bool(policy_data.get("citation_policy", {}).get("require_citations", False)),
                filter_terms=tuple(policy_data.get("filter_terms", [])),
            )
            record = record_cache.get((template_id, version))
            if record is None:
                raise FileNotFoundError(f"Template files not found for {template_id}:{version}")
            schema_id = f"{schema_name}:{schema_version}"
            runtime = TemplateRuntime(
                template_id=template_id,
                version=version,
                schema=schema,
                schema_id=schema_id,
                policy=runtime_policy,
                max_tokens=int(entry.get("max_tokens", runtime_policy.completion_budget)),
                token_budget=int(entry.get("token_budget", runtime_policy.prompt_budget)),
                template_record=record,
            )
            self.register_template(runtime)

    def list_templates(self) -> Sequence[TemplateRuntime]:
        return tuple(self._templates.values())

    def summary(self) -> Mapping[str, object]:
        templates = [
            {
                "id": runtime.template_id,
                "version": runtime.version,
                "schema_id": runtime.schema_id,
                "max_tokens": runtime.max_tokens,
                "token_budget": runtime.token_budget,
                "warmup": self.get_warmup_status(runtime.template_id, runtime.version),
            }
            for runtime in self._templates.values()
        ]
        return {
            "metadata": self._manifest_metadata,
            "templates": templates,
        }

    def get(self, template_id: str, version: str) -> TemplateRuntime:
        key = f"{template_id}:{version}"
        if key not in self._templates:
            raise KeyError(f"Template runtime not found: {key}")
        return self._templates[key]

    def default(self, template_id: str) -> TemplateRuntime:
        candidates = [runtime for runtime in self._templates.values() if runtime.template_id == template_id]
        if not candidates:
            raise KeyError(f"No runtime definitions available for template {template_id}")
        return sorted(candidates, key=lambda r: r.version)[-1]

    def render_prompt(self, runtime: TemplateRuntime, context: Mapping[str, object]) -> str:
        template_text = runtime.template_record.load_template()
        filtered_context = {
            key: context[key]
            for key in runtime.policy.allowed_sources
            if key in context
        }
        context_json = json.dumps(filtered_context, ensure_ascii=False, indent=2)
        prompt = template_text.replace("{{ context_json }}", context_json)
        payload_hash = sha256(context_json.encode("utf-8")).hexdigest()
        prompt += "\n\nPrompt-Context-Hash: " + payload_hash
        return prompt

    def validate_response(
        self,
        runtime: TemplateRuntime,
        response: Mapping[str, object],
        *,
        context: Mapping[str, object] | None = None,
        locale: str = "default",
        latency_ms: float | None = None,
        cost_usd: float | None = None,
    ) -> ValidationResult:
        jsonschema.validate(instance=response, schema=runtime.schema)
        if runtime.policy.require_citations:
            evidence = response.get("evidence", [])
            if not evidence:
                raise ValueError("Response missing required evidence citations")
        result = self._validator.evaluate(
            template_id=runtime.template_id,
            version=runtime.version,
            locale=locale,
            response=response,
            context=context or {},
        )
        record = self._metrics.record_metrics(
            template_id=runtime.template_id,
            version=runtime.version,
            metrics=result.metrics,
            locale=locale,
            observation=True,
        )
        record.increment("responses_validated", locale=locale)
        extras: dict[str, float] = {}
        if latency_ms is not None:
            extras["latency_ms"] = float(latency_ms)
            record.record("latency_ms", float(latency_ms), locale=locale)
        if cost_usd is not None:
            extras["cost_usd"] = float(cost_usd)
            record.record("cost_usd", float(cost_usd), locale=locale)
        if extras:
            record.track_observation(extras, locale=locale)
        return result
