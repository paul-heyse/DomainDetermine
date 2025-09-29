"""Grader contract definitions and registry."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Mapping, Optional

from .models import GraderReference, GraderType


@dataclass(frozen=True)
class GraderContract:
    """Defines expectations for a grader entry."""

    grader_id: str
    grader_type: GraderType
    normalization_rules: Mapping[str, str]
    schema: Mapping[str, str]
    tolerance: Mapping[str, float]
    synonym_dictionaries: Mapping[str, Mapping[str, str]]
    calibration_targets: Mapping[str, float]


@dataclass
class GraderRegistry:
    """Manages graders and ensures consistent IDs across suites."""

    contracts: Dict[str, GraderContract] = field(default_factory=dict)
    references: Dict[str, GraderReference] = field(default_factory=dict)

    def register(self, contract: GraderContract, reference: GraderReference) -> None:
        if contract.grader_id != reference.grader_id:
            raise ValueError("Contract and reference IDs must match")
        existing = self.contracts.get(contract.grader_id)
        if existing and existing != contract:
            msg = f"Grader contract '{contract.grader_id}' conflicts with existing definition"
            raise ValueError(msg)
        self.contracts[contract.grader_id] = contract
        self.references[reference.grader_id] = reference

    def get_contract(self, grader_id: str) -> Optional[GraderContract]:
        return self.contracts.get(grader_id)

    def get_reference(self, grader_id: str) -> Optional[GraderReference]:
        return self.references.get(grader_id)


