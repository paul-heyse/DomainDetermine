"""Tests for mapping policy guardrails."""

from __future__ import annotations

from DomainDetermine.mapping.policy import MappingGuardrailConfig, MappingPolicyGuardrails


def test_lexical_overlap_guardrail() -> None:
    guardrails = MappingPolicyGuardrails(MappingGuardrailConfig(min_lexical_overlap=0.3))
    assert guardrails.check_lexical_overlap(0.35)
    assert not guardrails.check_lexical_overlap(0.2)


def test_edit_distance_guardrail() -> None:
    guardrails = MappingPolicyGuardrails(MappingGuardrailConfig(max_edit_distance=2))
    assert guardrails.check_edit_distance(1)
    assert not guardrails.check_edit_distance(3)


def test_language_guardrail() -> None:
    guardrails = MappingPolicyGuardrails(MappingGuardrailConfig(allow_language_mismatch=False))
    assert guardrails.check_language("en", ["en", "fr"])
    assert guardrails.check_language("und", [])
    assert not guardrails.check_language("de", ["en"])

    permissive = MappingPolicyGuardrails(MappingGuardrailConfig(allow_language_mismatch=True))
    assert permissive.check_language("de", [])
