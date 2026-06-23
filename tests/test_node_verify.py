from unittest.mock import AsyncMock, patch

import pytest

from app.graph.nodes.verify import verify_node
from app.graph.state import GraphState


@pytest.mark.asyncio
async def test_verify_confirms_recovery() -> None:
    state: GraphState = {
        "incident_id": "inc-1",
        "trace_id": "trace-1",
        "raw_alert": "[告警] P1 order-api pod crashloop",
        "source_meta": {"chat_id": "oc_test", "msg_id": "om_test", "sender": "user1", "ts": 123},
        "category": "k8s_pod_crash",
        "severity": "p1",
        "service": "order-api",
        "is_duplicate": False,
        "diagnosis_messages": [],
        "evidence": {},
        "diagnosis_summary": "Pod OOMKilled",
        "confidence": 0.85,
        "proposals": [],
        "approval_decisions": {},
        "awaiting_since": None,
        "execution_results": [
            {
                "proposal_id": "prop-0",
                "plugin_name": "k8s.restart_pod",
                "status": "success",
                "output": {"deleted": True},
                "error": None,
                "duration_ms": 3200,
            }
        ],
        "final_status": None,
    }
    with patch("app.graph.nodes.verify.check_recovery", new_callable=AsyncMock) as mock_check:
        mock_check.return_value = True
        result = await verify_node(state)
        assert result["final_status"] == "resolved"


@pytest.mark.asyncio
async def test_verify_detects_failure() -> None:
    """当执行结果中有失败时,final_status 应为 'failed'。"""
    state: GraphState = {
        "incident_id": "inc-2",
        "trace_id": "trace-2",
        "raw_alert": "[告警] P1 order-api pod crashloop",
        "source_meta": {"chat_id": "oc_test", "msg_id": "om_test", "sender": "user1", "ts": 123},
        "category": "k8s_pod_crash",
        "severity": "p1",
        "service": "order-api",
        "is_duplicate": False,
        "diagnosis_messages": [],
        "evidence": {},
        "diagnosis_summary": "Pod OOMKilled",
        "confidence": 0.85,
        "proposals": [],
        "approval_decisions": {},
        "awaiting_since": None,
        "execution_results": [
            {
                "proposal_id": "prop-0",
                "plugin_name": "k8s.restart_pod",
                "status": "failure",
                "output": {},
                "error": "connection refused",
                "duration_ms": 500,
            }
        ],
        "final_status": None,
    }
    with patch("app.graph.nodes.verify.check_recovery", new_callable=AsyncMock) as mock_check:
        mock_check.return_value = False
        result = await verify_node(state)
        assert result["final_status"] == "failed"


@pytest.mark.asyncio
async def test_verify_empty_execution_results() -> None:
    """当没有执行结果时,应视为恢复(resolved)。"""
    state: GraphState = {
        "incident_id": "inc-3",
        "trace_id": "trace-3",
        "raw_alert": "[告警] P2 service degraded",
        "source_meta": {"chat_id": "oc_test", "msg_id": "om_test", "sender": "user1", "ts": 123},
        "category": "service_degraded",
        "severity": "p2",
        "service": "order-api",
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
    result = await verify_node(state)
    assert result["final_status"] == "resolved"
