from unittest.mock import AsyncMock, patch

import pytest

from app.graph.nodes.escalate import escalate_node
from app.graph.state import GraphState


@pytest.mark.asyncio
async def test_escalate_sends_card() -> None:
    state: GraphState = {
        'incident_id': 'inc-1',
        'trace_id': 'trace-1',
        'raw_alert': '[告警] P1 order-api pod crashloop',
        'source_meta': {'chat_id': 'oc_test', 'msg_id': 'om_test', 'sender': 'user1', 'ts': 123},
        'category': 'k8s_pod_crash',
        'severity': 'p1',
        'service': 'order-api',
        'is_duplicate': False,
        'diagnosis_messages': [],
        'evidence': {},
        'diagnosis_summary': 'Pod OOMKilled',
        'confidence': 0.85,
        'proposals': [],
        'approval_decisions': {},
        'awaiting_since': None,
        'execution_results': [],
        'final_status': None,
    }
    with patch('app.graph.nodes.escalate.send_escalate_card', new_callable=AsyncMock) as mock_send:
        mock_send.return_value = None
        result = await escalate_node(state)
        assert result['final_status'] == 'escalated'
        mock_send.assert_called_once()
