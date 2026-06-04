from unittest.mock import AsyncMock, patch

import pytest

from app.graph.nodes.resolve import resolve_node
from app.graph.state import GraphState


@pytest.mark.asyncio
async def test_resolve_sends_card() -> None:
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
        'final_status': 'resolved',
    }
    with patch('app.graph.nodes.resolve.send_resolve_card', new_callable=AsyncMock) as mock_send:
        mock_send.return_value = None
        result = await resolve_node(state)
        assert result['final_status'] == 'resolved'
        mock_send.assert_called_once()
