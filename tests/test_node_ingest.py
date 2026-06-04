from unittest.mock import AsyncMock, patch

import pytest

from app.graph.nodes.ingest import ingest_node
from app.graph.state import GraphState


def _make_state(**overrides: object) -> GraphState:
    base: GraphState = {
        "incident_id": "",
        "trace_id": "trace-1",
        "raw_alert": "[告警] P1 order-api pod crashloop",
        "source_meta": {"chat_id": "oc_test", "msg_id": "om_test", "sender": "user1", "ts": 123},
        "category": None,
        "severity": None,
        "service": None,
        "is_duplicate": False,
        "diagnosis_messages": [],
        "evidence": {},
        "diagnosis_summary": None,
        "confidence": None,
        "proposals": [],
        "approval_decisions": {},
        "awaiting_since": None,
        "execution_results": [],
        "final_status": None,
    }
    base.update(overrides)  # type: ignore[arg-type]
    return base


@pytest.mark.asyncio
async def test_ingest_creates_incident() -> None:
    state = _make_state()
    with patch("app.graph.nodes.ingest.create_incident", new_callable=AsyncMock) as mock_create:
        mock_create.return_value = {"id": "inc-1", "fingerprint": "fp1"}
        result = await ingest_node(state)
        assert result["incident_id"] == "inc-1"
        assert result["is_duplicate"] is False
        mock_create.assert_called_once()


@pytest.mark.asyncio
async def test_ingest_detects_duplicate() -> None:
    state = _make_state()
    with patch("app.graph.nodes.ingest.create_incident", new_callable=AsyncMock) as mock_create:
        mock_create.return_value = {"id": "inc-1", "fingerprint": "fp1", "is_duplicate": True}
        result = await ingest_node(state)
        assert result["is_duplicate"] is True


@pytest.mark.asyncio
async def test_generate_fingerprint_deterministic() -> None:
    from app.graph.nodes.ingest import generate_fingerprint

    fp1 = generate_fingerprint("hello world", None, None)
    fp2 = generate_fingerprint("hello world", None, None)
    assert fp1 == fp2
    assert len(fp1) == 16


@pytest.mark.asyncio
async def test_generate_fingerprint_differs_for_different_alerts() -> None:
    from app.graph.nodes.ingest import generate_fingerprint

    fp1 = generate_fingerprint("alert A", None, None)
    fp2 = generate_fingerprint("alert B", None, None)
    assert fp1 != fp2
