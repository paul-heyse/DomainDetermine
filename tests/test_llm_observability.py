from __future__ import annotations

from pathlib import Path

from DomainDetermine.governance import (
    ArtifactRef,
    GovernanceEventLog,
    GovernanceEventType,
)
from DomainDetermine.llm import LLMObservability, ProviderConfig, TritonLLMProvider


def test_llm_observability_records_metrics() -> None:
    observability = LLMObservability()
    payload = {
        "model": "test",
        "operation": "generate_json",
        "schema_id": "schema",
        "duration_ms": 120.0,
        "queue_delay_us": 500.0,
        "tokens_in": 10.0,
        "tokens_out": 5.0,
        "kv_cache_reuse": {"hits": 8, "misses": 2},
        "speculative": {"attempts": 4, "accepts": 2},
    }

    observability.record_request(payload)

    snapshot = observability.metrics_snapshot()
    assert snapshot["requests"] == 1
    assert snapshot["latency_avg_ms"] == 120.0
    assert snapshot["queue_delay_avg_us"] == 500.0
    assert snapshot["tokens_in_avg"] == 10.0
    assert snapshot["tokens_out_avg"] == 5.0
    assert snapshot["kv_reuse_ratio"] == 0.8
    assert snapshot["speculative_accept_ratio"] == 0.5

    events = list(observability.recent_events())
    assert len(events) == 1
    assert events[0]["operation"] == "generate_json"


def test_llm_provider_emits_governance_alerts(tmp_path: Path) -> None:
    event_log_path = tmp_path / "gov.log"
    event_log = GovernanceEventLog(event_log_path, secret="secret")
    artifact = ArtifactRef(artifact_id="llm-engine", version="v1", hash="abc123")

    config = ProviderConfig(
        endpoint="http://example.com",
        model_name="llm",
        tokenizer_dir=tmp_path,
        engine_hash="hash",
        quantisation="w4a8",
        readiness_thresholds={
            "max_queue_delay_us": 10.0,
            "max_tokens": 5.0,
            "max_cost_usd": 0.01,
        },
        price_per_token=0.002,
        governance_log=event_log,
        governance_artifact=artifact,
        governance_actor="test-actor",
    )

    provider = TritonLLMProvider(config)

    response = {
        "text": ["{}"],
        "perf_metrics": {
            "queue_delay_us": 25.0,
            "tokens_in": 4.0,
            "tokens_out": 2.0,
        },
    }

    provider._log_request("generate_json", response, duration_ms=15.0, schema_id="schema")

    events = list(event_log.query())
    assert len(events) == 3
    assert all(event.event_type is GovernanceEventType.LLM_OBSERVABILITY_ALERT for event in events)
    reasons = {event.payload["reason"] for event in events}
    assert {"queue_delay", "token_budget", "cost_budget"} <= reasons
