from datetime import UTC, datetime
from uuid import uuid4

import pytest

from app.db import dispose_engine, session_scope
from app.db.models import (
    Diagnosis,
    FixExecution,
    FixExecutionStatus,
    FixProposal,
    Incident,
    IncidentEvent,
    IncidentStatus,
    LarkCardBinding,
)


@pytest.mark.asyncio
async def test_create_full_incident_chain() -> None:
    async with session_scope() as session:
        incident = Incident(
            fingerprint="test-fp-001",
            status=IncidentStatus.NEW,
            category="k8s.pod_crashloop",
            service="svc-a",
            namespace="prod",
            severity="P2",
            summary="pod crashlooping",
            raw_alert={"alert": "test"},
            chat_id="oc_test",
            source_message_id="om_test",
        )
        session.add(incident)
        await session.flush()
        incident_id = incident.id

        session.add(
            IncidentEvent(
                incident_id=incident_id,
                event_type="created",
                payload={"source": "test"},
            )
        )

        diagnosis = Diagnosis(
            incident_id=incident_id,
            root_cause="OOMKilled",
            confidence=0.85,
            evidence=[{"type": "log", "snippet": "OOM"}],
        )
        session.add(diagnosis)
        await session.flush()

        proposal = FixProposal(
            incident_id=incident_id,
            plugin_name="k8s.restart_pod",
            args={"pod": "p", "namespace": "prod"},
            risk_level="medium",
            description="restart pod",
            source="plugin",
        )
        session.add(proposal)
        await session.flush()

        session.add(
            FixExecution(
                incident_id=incident_id,
                proposal_id=proposal.id,
                approved_by="user_a",
                approved_at=datetime.now(UTC),
                status=FixExecutionStatus.PENDING,
                output={},
            )
        )

        session.add(
            LarkCardBinding(
                incident_id=incident_id,
                chat_id="oc_test",
                message_id=f"om_card_{uuid4()}",
                card_kind="diagnosis",
            )
        )

    # 重开 session 验证
    async with session_scope() as session:
        from sqlalchemy import select

        result = await session.execute(select(Incident).where(Incident.id == incident_id))
        loaded = result.scalar_one()
        assert loaded.fingerprint == "test-fp-001"
        assert loaded.raw_alert == {"alert": "test"}

    await dispose_engine()
