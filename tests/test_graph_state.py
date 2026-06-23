from app.graph.state import ExecutionRecord, GraphState, ProposalDraft


def test_graph_state_creation() -> None:
    state: GraphState = {
        "incident_id": "inc-1",
        "trace_id": "trace-1",
        "raw_alert": "test alert",
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
    assert state["incident_id"] == "inc-1"
    assert state["is_duplicate"] is False
    assert state["proposals"] == []


def test_proposal_draft_creation() -> None:
    proposal: ProposalDraft = {
        "plugin_name": "k8s.restart_pod",
        "args": {"namespace": "prod", "pod_name": "app-xyz"},
        "risk_level": "medium",
        "description": "restart pod",
        "expected_outcome": "pod restarts",
        "rollback_hint": None,
        "source": "plugin",
    }
    assert proposal["plugin_name"] == "k8s.restart_pod"
    assert proposal["risk_level"] == "medium"


def test_execution_record_creation() -> None:
    record: ExecutionRecord = {
        "proposal_id": "prop-1",
        "plugin_name": "k8s.restart_pod",
        "status": "success",
        "output": {"deleted": True},
        "error": None,
        "duration_ms": 3200,
    }
    assert record["status"] == "success"
    assert record["duration_ms"] == 3200
