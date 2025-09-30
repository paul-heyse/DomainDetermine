import logging
from pathlib import Path

import pytest

from DomainDetermine.governance import (
    ArtifactRef,
    GovernanceEventLog,
    GovernanceEventType,
    log_mapping_batch_published,
)
from DomainDetermine.mapping.telemetry import MappingTelemetry


@pytest.fixture
def governance_log(tmp_path: Path) -> GovernanceEventLog:
    secret = "secret"
    path = tmp_path / "governance.log"
    return GovernanceEventLog(path, secret=secret)


def test_mapping_telemetry_emits_governance_event(governance_log: GovernanceEventLog) -> None:
    artifact = ArtifactRef(artifact_id="MAP-000001", version="1.0.0", hash="abc123")
    logger = logging.getLogger("test.mapping.telemetry")
    telemetry = MappingTelemetry(logger=logger, governance_log=governance_log, governance_artifact=artifact)
    metrics = {"items_total": 2.0, "items_resolved": 1.0}
    telemetry.emit_metrics(metrics)
    events = list(governance_log.query(artifact_id="MAP-000001", event_types=[GovernanceEventType.MAPPING_BATCH_PUBLISHED]))
    assert events
    event = events[0]
    assert event.payload["metrics"]["resolution_rate"] == 0.5
