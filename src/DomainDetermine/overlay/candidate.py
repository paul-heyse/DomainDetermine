"""Candidate mining and LLM-assisted proposal generation for overlay nodes."""

from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass
from hashlib import sha256
from typing import Iterable, Mapping, Optional, Sequence

from DomainDetermine.llm import SchemaRegistry, TritonLLMProvider
from DomainDetermine.overlay.exceptions import PolicyViolationError, QualityGateError
from DomainDetermine.overlay.models import EvidenceDocument, EvidencePack
from DomainDetermine.overlay.quality import OverlayQualityGateConfig, run_quality_gates


@dataclass(frozen=True)
class CoverageGap:
    """Represents an under-covered branch coming from Module 2 diagnostics."""

    parent_concept_id: str
    parent_label: str
    desired_facets: Mapping[str, str]
    corpus_snippets: Sequence[str]
    editorial_rules: Sequence[str]
    policy_guardrails: Sequence[str]


@dataclass(frozen=True)
class CandidateSeed:
    """Lightweight candidate mined before LLM prompting."""

    label: str
    score: float
    source: str
    citations: Sequence[str]


@dataclass(frozen=True)
class PromptBundle:
    """Payload supplied to the LLM for candidate generation."""

    parent_definition: str
    sibling_labels: Sequence[str]
    editorial_rules: Sequence[str]
    policy_guardrails: Sequence[str]
    corpus_snippets: Sequence[str]
    prompt_hash: str


@dataclass(frozen=True)
class StructuredCandidate:
    """Structured response from the LLM constrained by schema."""

    label: str
    justification: str
    citations: Sequence[str]
    annotation_prompts: Sequence[str]
    difficulty: str
    nearest_existing: Optional[str]
    split_children: Sequence[str]
    merge_targets: Sequence[str]
    synonyms: Mapping[str, Sequence[str]]
    jurisdiction_tags: Sequence[str]

    @classmethod
    def from_payload(cls, payload: Mapping[str, object]) -> "StructuredCandidate":
        required = {
            "label": str,
            "justification": str,
            "citations": list,
            "annotation_prompts": list,
            "difficulty": str,
            "nearest_existing": (str, type(None)),
            "split_children": list,
            "merge_targets": list,
            "synonyms": dict,
            "jurisdiction_tags": list,
        }
        for field, expected in required.items():
            if field not in payload:
                raise QualityGateError(f"LLM payload missing field '{field}'")
            value = payload[field]
            if isinstance(expected, tuple):
                if not isinstance(value, expected):
                    raise QualityGateError(f"Field '{field}' has incorrect type {type(value)}")
            elif not isinstance(value, expected):
                raise QualityGateError(f"Field '{field}' has incorrect type {type(value)}")
        citations = tuple(str(item) for item in payload["citations"])
        annotation_prompts = tuple(str(item) for item in payload["annotation_prompts"])
        split_children = tuple(str(item) for item in payload["split_children"])
        merge_targets = tuple(str(item) for item in payload["merge_targets"])
        jurisdiction_tags = tuple(str(item) for item in payload["jurisdiction_tags"])
        synonyms_payload = payload["synonyms"]
        synonyms: dict[str, tuple[str, ...]] = {}
        for language, labels in synonyms_payload.items():
            synonyms[str(language)] = tuple(str(value) for value in labels)
        return cls(
            label=str(payload["label"]),
            justification=str(payload["justification"]),
            citations=citations,
            annotation_prompts=annotation_prompts,
            difficulty=str(payload["difficulty"]),
            nearest_existing=str(payload["nearest_existing"]) if payload["nearest_existing"] else None,
            split_children=split_children,
            merge_targets=merge_targets,
            synonyms=synonyms,
            jurisdiction_tags=jurisdiction_tags,
        )


@dataclass(frozen=True)
class CritiqueResult:
    """Outcome of the self-critique stage."""

    is_duplicate: bool
    policy_violation: Optional[str]
    annotatability_ok: bool


@dataclass(frozen=True)
class CandidateProposal:
    """Final vetted candidate ready for registry insertion."""

    structured: StructuredCandidate
    evidence_pack: EvidencePack
    coverage_gap: CoverageGap
    prompt_hash: str


class CorpusCandidateMiner:
    """Discover promising candidate labels from corpus snippets."""

    def __init__(self, *, stopwords: Optional[set[str]] = None) -> None:
        self._stopwords = stopwords or {
            "the",
            "and",
            "for",
            "with",
            "from",
            "that",
            "into",
            "such",
        }

    def extract(self, gap: CoverageGap, *, max_candidates: int = 5) -> Sequence[CandidateSeed]:
        frequencies: Counter[str] = Counter()
        for snippet in gap.corpus_snippets:
            tokens = [token.strip(".,:;()[]{}\"'") for token in snippet.split()]
            filtered = [token for token in tokens if token and token.lower() not in self._stopwords]
            for i in range(len(filtered)):
                unigram = filtered[i]
                if unigram[0].isupper():
                    frequencies[unigram] += 1
                if i + 1 < len(filtered):
                    bigram = f"{filtered[i]} {filtered[i + 1]}"
                    if all(word[0].isupper() for word in bigram.split()):
                        frequencies[bigram] += 1
        most_common = frequencies.most_common(max_candidates)
        seeds = []
        for label, score in most_common:
            seed = CandidateSeed(label=label, score=float(score), source="corpus", citations=(gap.parent_concept_id,))
            seeds.append(seed)
        return tuple(seeds)


class OntologyHoleDetector:
    """Suggest candidates based on sibling definitions and external mappings."""

    def detect(
        self,
        *,
        sibling_definitions: Mapping[str, str],
        external_concepts: Mapping[str, Sequence[str]],
        max_candidates: int = 3,
    ) -> Sequence[CandidateSeed]:
        suggestions: list[CandidateSeed] = []
        for sibling, definition in sibling_definitions.items():
            for concept in external_concepts.get(sibling, ()):  # consider cross references
                suggestions.append(
                    CandidateSeed(
                        label=concept,
                        score=float(len(definition)),
                        source="ontology-hole",
                        citations=(sibling,),
                    )
                )
        suggestions.sort(key=lambda candidate: candidate.score, reverse=True)
        return tuple(suggestions[:max_candidates])


class PromptAssembler:
    """Constructs prompt bundles for LLM invocation."""

    def build(
        self,
        *,
        parent_definition: str,
        sibling_labels: Sequence[str],
        editorial_rules: Sequence[str],
        policy_guardrails: Sequence[str],
        corpus_snippets: Sequence[str],
    ) -> PromptBundle:
        payload = {
            "parent_definition": parent_definition,
            "sibling_labels": tuple(sibling_labels),
            "editorial_rules": tuple(editorial_rules),
            "policy_guardrails": tuple(policy_guardrails),
            "corpus_snippets": tuple(corpus_snippets),
        }
        prompt_hash = sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
        return PromptBundle(
            parent_definition=parent_definition,
            sibling_labels=tuple(sibling_labels),
            editorial_rules=tuple(editorial_rules),
            policy_guardrails=tuple(policy_guardrails),
            corpus_snippets=tuple(corpus_snippets),
            prompt_hash=prompt_hash,
        )


class StructuredOutputValidator:
    """Validates and normalizes LLM structured outputs."""

    def parse(self, payload: str | Mapping[str, object]) -> StructuredCandidate:
        if isinstance(payload, str):
            data = json.loads(payload)
        else:
            data = payload
        if not isinstance(data, Mapping):
            raise QualityGateError("LLM payload must be a mapping")
        return StructuredCandidate.from_payload(data)


class SelfCritiqueEngine:
    """Runs a second-pass critique to ensure policy and overlap compliance."""

    def critique(
        self,
        candidate: StructuredCandidate,
        *,
        existing_labels: Iterable[str],
        policy_guardrails: Sequence[str],
    ) -> CritiqueResult:
        normalized = candidate.label.lower()
        duplicates = {label.lower() for label in existing_labels}
        is_duplicate = normalized in duplicates or candidate.nearest_existing in duplicates
        policy_violation = next((rule for rule in policy_guardrails if rule in candidate.label), None)
        annotatability_ok = bool(candidate.annotation_prompts)
        return CritiqueResult(
            is_duplicate=is_duplicate,
            policy_violation=policy_violation,
            annotatability_ok=annotatability_ok,
        )


class CandidatePipeline:
    """Full pipeline that mines, prompts, critiques, and vets overlay candidates."""

    def __init__(
        self,
        *,
        llm_provider: TritonLLMProvider,
        schema_registry: SchemaRegistry,
        quality_config: Optional[OverlayQualityGateConfig] = None,
        schema_name: str = "overlay_candidate",
        schema_version: str = "v1",
    ) -> None:
        self._llm_provider = llm_provider
        self._schema_registry = schema_registry
        self._quality_config = quality_config or OverlayQualityGateConfig()
        self._prompt_assembler = PromptAssembler()
        self._output_validator = StructuredOutputValidator()
        self._critique_engine = SelfCritiqueEngine()
        self._schema_name = schema_name
        self._schema_version = schema_version

    def generate_proposal(
        self,
        *,
        gap: CoverageGap,
        parent_definition: str,
        sibling_labels: Sequence[str],
        mining_candidates: Sequence[CandidateSeed],
        existing_labels: Sequence[str],
        evidence_documents: Sequence[EvidenceDocument],
    ) -> CandidateProposal:
        evidence_pack = EvidencePack(documents=tuple(evidence_documents), policy_notes=gap.policy_guardrails)
        prompt_bundle = self._prompt_assembler.build(
            parent_definition=parent_definition,
            sibling_labels=sibling_labels,
            editorial_rules=gap.editorial_rules,
            policy_guardrails=gap.policy_guardrails,
            corpus_snippets=gap.corpus_snippets,
        )
        schema_record = self._schema_registry.load_record(self._schema_name, self._schema_version)
        payload = {
            "parent_definition": prompt_bundle.parent_definition,
            "sibling_labels": list(prompt_bundle.sibling_labels),
            "editorial_rules": list(prompt_bundle.editorial_rules),
            "policy_guardrails": list(prompt_bundle.policy_guardrails),
            "corpus_snippets": list(prompt_bundle.corpus_snippets),
            "candidate_seeds": [seed.label for seed in mining_candidates],
        }
        raw_payload = self._llm_provider.generate_json(
            schema_record.schema,
            json.dumps(payload),
            schema_id=schema_record.id,
            max_tokens=512,
        )
        structured = self._output_validator.parse(raw_payload)
        critique = self._critique_engine.critique(
            structured,
            existing_labels=existing_labels,
            policy_guardrails=gap.policy_guardrails,
        )
        if critique.is_duplicate:
            raise QualityGateError("Critique flagged duplicate candidate")
        if critique.policy_violation:
            raise PolicyViolationError(f"Candidate violates policy: {critique.policy_violation}")
        if not critique.annotatability_ok:
            raise QualityGateError("Critique indicates insufficient annotatability prompts")
        run_quality_gates(
            preferred_labels={"default": structured.label},
            new_label=structured.label,
            existing_labels=existing_labels,
            evidence_pack=evidence_pack,
            cited_identifiers=structured.citations,
            config=self._quality_config,
        )
        return CandidateProposal(
            structured=structured,
            evidence_pack=evidence_pack,
            coverage_gap=gap,
            prompt_hash=prompt_bundle.prompt_hash,
        )


__all__ = [
    "CandidatePipeline",
    "CandidateSeed",
    "CorpusCandidateMiner",
    "CoverageGap",
    "CritiqueResult",
    "OntologyHoleDetector",
    "PromptAssembler",
    "StructuredCandidate",
    "StructuredOutputValidator",
]
