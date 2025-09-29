"""Candidate scoring and calibration."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

import numpy as np

from .models import Candidate


@dataclass(slots=True)
class CandidateScorer:
    """Combines multiple scores and calibrates confidence estimates."""

    temperature: float = 1.0

    def score(self, candidates: Sequence[Candidate]) -> tuple[Candidate, ...]:
        if not candidates:
            return tuple()
        scores = np.array([candidate.score for candidate in candidates], dtype=float)
        calibrated = self._softmax(scores / max(self.temperature, 1e-6))
        ranked = []
        for candidate, confidence in zip(candidates, calibrated, strict=True):
            ranked.append(
                Candidate(
                    concept_id=candidate.concept_id,
                    label=candidate.label,
                    source=candidate.source,
                    score=float(confidence),
                    evidence=candidate.evidence,
                    language=candidate.language,
                )
            )
        ranked.sort(key=lambda candidate: candidate.score, reverse=True)
        return tuple(ranked)

    @staticmethod
    def _softmax(values: np.ndarray) -> np.ndarray:
        stable_values = values - np.max(values)
        exp = np.exp(stable_values)
        total = np.sum(exp)
        if total == 0:
            return np.full_like(exp, 1.0 / len(values))
        return exp / total

