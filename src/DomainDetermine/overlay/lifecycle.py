"""Lifecycle management for overlay nodes."""

from __future__ import annotations

import json
import re
import unicodedata
from collections import defaultdict
from dataclasses import dataclass
from typing import Iterable, Mapping, MutableMapping, Optional, Sequence

from DomainDetermine.coverage_planner.models import RiskTier
from DomainDetermine.overlay.exceptions import (
    IdentifierCollisionError,
    InvalidStateTransitionError,
    PolicyViolationError,
)
from DomainDetermine.overlay.models import (
    EvidencePack,
    OverlayCoverageDelta,
    OverlayLifecycleEvent,
    OverlayManifest,
    OverlayManifestEntry,
    OverlayNode,
    OverlayNodeState,
    OverlayProvenance,
    PolicyGuardrail,
    serialize_labels,
)


def _slugify(value: str) -> str:
    """Return an ASCII slug suitable for overlay identifiers."""

    normalized = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode()
    normalized = normalized.lower()
    normalized = re.sub(r"[^a-z0-9]+", "-", normalized).strip("-")
    return re.sub(r"-+", "-", normalized) or "concept"


@dataclass
class OverlayIdGenerator:
    """Generates collision-free overlay identifiers."""

    namespace: str = "overlay"

    def __post_init__(self) -> None:
        self._issued: set[str] = set()

    def generate(self, label_hint: str, counter: int = 0) -> str:
        slug = _slugify(label_hint)
        candidate = f"{self.namespace}:{slug}" if not counter else f"{self.namespace}:{slug}-{counter}"
        if candidate in self._issued:
            return self.generate(label_hint, counter + 1)
        self._issued.add(candidate)
        return candidate

    def reserve(self, overlay_id: str) -> None:
        if overlay_id in self._issued:
            msg = f"Overlay identifier '{overlay_id}' already reserved"
            raise IdentifierCollisionError(msg)
        self._issued.add(overlay_id)


class OverlayRegistry:
    """In-memory registry supporting overlay lifecycle operations."""

    def __init__(self, *, namespace: str = "overlay", policy_guardrail: Optional[PolicyGuardrail] = None) -> None:
        self._namespace = namespace
        self._id_generator = OverlayIdGenerator(namespace=namespace)
        self._nodes: MutableMapping[str, OverlayNode] = {}
        self._events: MutableMapping[str, list[OverlayLifecycleEvent]] = defaultdict(list)
        self._policy_guardrail = policy_guardrail or PolicyGuardrail()

    @property
    def namespace(self) -> str:
        return self._namespace

    def register_candidate(
        self,
        *,
        base_concept_id: str,
        preferred_labels: Mapping[str, str],
        alt_labels: Optional[Mapping[str, Sequence[str]]],
        short_definition: str,
        long_definition: Optional[str],
        examples: Sequence[str],
        difficulty: str,
        jurisdiction_tags: Sequence[str],
        evidence_pack: EvidencePack,
        provenance: OverlayProvenance,
        nearest_concept_id: Optional[str] = None,
        explicit_overlay_id: Optional[str] = None,
        prompt_hash: Optional[str] = None,
    ) -> OverlayNode:
        """Mint a candidate node in the overlay namespace."""

        if explicit_overlay_id:
            self._id_generator.reserve(explicit_overlay_id)
            overlay_id = explicit_overlay_id
        else:
            label_hint = next(iter(preferred_labels.values())) if preferred_labels else base_concept_id
            overlay_id = self._id_generator.generate(label_hint)
        if overlay_id in self._nodes:
            msg = f"Overlay node '{overlay_id}' already exists"
            raise IdentifierCollisionError(msg)

        for jurisdiction in jurisdiction_tags:
            if not self._policy_guardrail.allows(base_concept_id, jurisdiction):
                msg = f"Jurisdiction '{jurisdiction}' is blocked for concept '{base_concept_id}'"
                raise PolicyViolationError(msg)

        node = OverlayNode(
            overlay_id=overlay_id,
            base_concept_id=base_concept_id,
            state=OverlayNodeState.CANDIDATE,
            preferred_labels=dict(preferred_labels),
            alt_labels=serialize_labels(alt_labels or {}),
            short_definition=short_definition,
            long_definition=long_definition,
            examples=tuple(examples),
            difficulty=difficulty,
            jurisdiction_tags=tuple(jurisdiction_tags),
            evidence_pack=evidence_pack,
            provenance=provenance,
            coverage_plan_links=tuple(),
            prompt_hash=prompt_hash,
            nearest_concept_id=nearest_concept_id,
        )
        self._nodes[overlay_id] = node
        self._events[overlay_id].append(
            OverlayLifecycleEvent(
                overlay_id=overlay_id,
                from_state=OverlayNodeState.CANDIDATE,
                to_state=OverlayNodeState.CANDIDATE,
                reviewer_id=None,
                rationale="candidate_registered",
            )
        )
        return node

    def get(self, overlay_id: str) -> OverlayNode:
        return self._nodes[overlay_id]

    def iter_nodes(self, *, states: Optional[Iterable[OverlayNodeState]] = None) -> Sequence[OverlayNode]:
        if states is None:
            return tuple(self._nodes.values())
        allowed = {state for state in states}
        return tuple(node for node in self._nodes.values() if node.state in allowed)

    def attach_coverage_plan(self, overlay_id: str, coverage_plan_id: str) -> None:
        node = self._nodes[overlay_id]
        links = set(node.coverage_plan_links)
        links.add(coverage_plan_id)
        self._nodes[overlay_id] = OverlayNode(
            overlay_id=node.overlay_id,
            base_concept_id=node.base_concept_id,
            state=node.state,
            preferred_labels=node.preferred_labels,
            alt_labels=node.alt_labels,
            short_definition=node.short_definition,
            long_definition=node.long_definition,
            examples=node.examples,
            difficulty=node.difficulty,
            jurisdiction_tags=node.jurisdiction_tags,
            evidence_pack=node.evidence_pack,
            provenance=node.provenance,
            coverage_plan_links=tuple(sorted(links)),
            prompt_hash=node.prompt_hash,
            nearest_concept_id=node.nearest_concept_id,
        )

    def transition(
        self,
        overlay_id: str,
        *,
        to_state: OverlayNodeState,
        reviewer_id: Optional[str],
        rationale: Optional[str],
    ) -> OverlayNode:
        node = self._nodes[overlay_id]
        self._assert_transition(node.state, to_state)
        if to_state in {OverlayNodeState.APPROVED, OverlayNodeState.PUBLISHED, OverlayNodeState.DEPRECATED} and not reviewer_id:
            msg = f"Reviewer id required for transition to {to_state.value}"
            raise InvalidStateTransitionError(msg)
        updated = node.with_state(to_state)
        self._nodes[overlay_id] = updated
        event = OverlayLifecycleEvent(
            overlay_id=overlay_id,
            from_state=node.state,
            to_state=to_state,
            reviewer_id=reviewer_id,
            rationale=rationale,
        )
        self._events[overlay_id].append(event)
        return updated

    def _assert_transition(self, from_state: OverlayNodeState, to_state: OverlayNodeState) -> None:
        if from_state == to_state:
            return
        allowed = {
            OverlayNodeState.CANDIDATE: {OverlayNodeState.APPROVED, OverlayNodeState.DEPRECATED},
            OverlayNodeState.APPROVED: {OverlayNodeState.PUBLISHED, OverlayNodeState.DEPRECATED},
            OverlayNodeState.PUBLISHED: {OverlayNodeState.DEPRECATED},
            OverlayNodeState.DEPRECATED: set(),
        }
        if to_state not in allowed.get(from_state, set()):
            msg = f"Cannot transition overlay node from {from_state.value} to {to_state.value}"
            raise InvalidStateTransitionError(msg)

    def export_for_module1(self) -> Sequence[Mapping[str, object]]:
        return tuple(node.to_module1_record() for node in self._nodes.values())

    def build_manifest(
        self,
        *,
        version: str,
        governance_registry: Optional[Mapping[str, Mapping[str, object]]] = None,
    ) -> OverlayManifest:
        entries = []
        governance_registry = governance_registry or {}
        for node in self._nodes.values():
            lifecycle_events = [event.as_dict() for event in self._events[node.overlay_id]]
            content_hash = _manifest_entry_hash(node)
            entries.append(
                OverlayManifestEntry(
                    overlay_id=node.overlay_id,
                    base_concept_id=node.base_concept_id,
                    kos_snapshot_id=node.provenance.kos_snapshot_id,
                    coverage_plan_ids=node.coverage_plan_links,
                    provenance=node.provenance.as_dict(),
                    lifecycle_events=lifecycle_events,
                    content_hash=content_hash,
                    governance=governance_registry.get(node.overlay_id, {}),
                )
            )
        return OverlayManifest(version=version, nodes=tuple(entries))

    def build_coverage_delta(
        self,
        overlay_id: str,
        *,
        coverage_plan_id: str,
        planned_quota: int,
        risk_tier: str,
    ) -> OverlayCoverageDelta:
        node = self._nodes[overlay_id]
        if node.state is not OverlayNodeState.PUBLISHED:
            msg = f"Coverage delta requested for non-published node '{overlay_id}'"
            raise InvalidStateTransitionError(msg)
        self.attach_coverage_plan(overlay_id, coverage_plan_id)
        return OverlayCoverageDelta(
            overlay_id=overlay_id,
            coverage_plan_id=coverage_plan_id,
            concept_id=node.base_concept_id,
            preferred_label=next(iter(node.preferred_labels.values())),
            difficulty=node.difficulty,
            planned_quota=planned_quota,
            provenance=node.provenance.as_dict(),
            risk_tier=_parse_risk_tier(risk_tier),
        )

    def lifecycle_events(self, overlay_id: str) -> Sequence[OverlayLifecycleEvent]:
        return tuple(self._events[overlay_id])


def _manifest_entry_hash(node: OverlayNode) -> str:
    payload = node.to_module1_record()
    # Lifecycle state is excluded to avoid churn between approved/published snapshots
    payload.pop("state", None)
    payload["overlay_id"] = node.overlay_id
    serialized = json.dumps(payload, sort_keys=True)
    import hashlib

    return hashlib.sha256(serialized.encode()).hexdigest()


def _parse_risk_tier(value: str) -> RiskTier:
    try:
        return RiskTier(value)
    except ValueError as exc:  # pragma: no cover - defensive guard
        msg = f"Unknown risk tier '{value}'"
        raise InvalidStateTransitionError(msg) from exc


__all__ = [
    "OverlayIdGenerator",
    "OverlayRegistry",
]
