"""Request builder enforcing prompt pack retrieval and token policies."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Iterable, Mapping

from .calibration import get_calibration_set
from .runtime import PromptRuntimeManager, TemplateRuntime


@dataclass
class BuiltRequest:
    """Represents a request payload ready for the LLM provider."""

    prompt: str
    schema_id: str
    max_tokens: int
    context: Mapping[str, object]


class RequestBuilder:
    """Builds provider requests while enforcing prompt policies."""

    def __init__(self, runtime_manager: PromptRuntimeManager) -> None:
        self._runtime_manager = runtime_manager

    def build(
        self,
        template_id: str,
        version: str,
        context: Mapping[str, object],
    ) -> BuiltRequest:
        runtime = self._runtime_manager.get(template_id, version)
        filtered_context = self._filter_context(runtime, context)
        serialized = json.dumps(filtered_context, ensure_ascii=False)
        prompt = self._runtime_manager.render_prompt(runtime, filtered_context)
        self._enforce_prompt_budget(runtime, serialized)
        return BuiltRequest(
            prompt=prompt,
            schema_id=runtime.schema_id,
            max_tokens=runtime.max_tokens,
            context=filtered_context,
        )

    def validate_citations(
        self,
        runtime: TemplateRuntime,
        response: Mapping[str, object],
        request: BuiltRequest,
    ) -> None:
        evidence = response.get("evidence", []) if isinstance(response, Mapping) else []
        if not evidence:
            return
        corpus = "\n".join(
            value if isinstance(value, str) else json.dumps(value, ensure_ascii=False)
            for value in request.context.values()
        )
        missing = [citation for citation in evidence if citation not in corpus]
        if missing:
            raise ValueError(
                f"Evidence citations not found in provided context for {runtime.qualified_id}: {missing}"
            )

    def warmup(self, template_id: str, version: str) -> Iterable[BuiltRequest]:
        """Generate warm-up requests for the specified template."""

        calibration_set = get_calibration_set(template_id, version)
        for example in calibration_set:
            context = {
                key: value
                for key, value in example.input_payload.items()
                if key not in {"item", "candidates"}
            }
            yield self.build(template_id, version, context)

    def _enforce_prompt_budget(self, runtime: TemplateRuntime, serialized_context: str) -> None:
        # Simple proxy for token counts: character length divided by 4 (approximate English tokens)
        estimated_tokens = max(1, len(serialized_context) // 4)
        if estimated_tokens > runtime.token_budget:
            raise ValueError(
                f"Context budget exceeded for {runtime.qualified_id}: "
                f"estimated {estimated_tokens} tokens > budget {runtime.token_budget}"
            )

    def _filter_context(
        self,
        runtime: TemplateRuntime,
        context: Mapping[str, object],
    ) -> Mapping[str, object]:
        filtered = {
            key: context[key]
            for key in runtime.policy.allowed_sources
            if key in context
        }
        return {
            key: value
            for key, value in filtered.items()
            if not isinstance(value, str) or not runtime.policy.filter_terms or not any(
                term.casefold() in value.casefold() for term in runtime.policy.filter_terms
            )
        }
