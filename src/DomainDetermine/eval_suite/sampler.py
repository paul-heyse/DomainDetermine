"""Sampling utilities for semi-dynamic suites."""

from __future__ import annotations

from dataclasses import dataclass
from random import Random
from typing import Sequence

from .models import SliceDefinition


@dataclass
class SliceSampler:
    """Deterministic sampler for slice items."""

    random_generator: Random

    def sample(self, slice_def: SliceDefinition, population: Sequence[str]) -> Sequence[str]:
        if slice_def.sampling.mode == "static":
            return list(slice_def.sampling.inclusion_list)
        if slice_def.sampling.seed is None:
            raise ValueError(f"Slice '{slice_def.slice_id}' requires a seed for semi-dynamic sampling")
        rng = Random(slice_def.sampling.seed)
        candidates = [item for item in population if item not in slice_def.sampling.exclusion_list]
        rng.shuffle(candidates)
        return tuple(candidates[: slice_def.quota])


def default_sampler() -> SliceSampler:
    return SliceSampler(random_generator=Random())


