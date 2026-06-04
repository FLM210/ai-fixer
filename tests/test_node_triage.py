from unittest.mock import AsyncMock, patch

import pytest

from app.graph.nodes.triage import triage_node
from app.graph.state import GraphState


@pytest.mark.asyncio
async def test_triage_classifies_alert() -> None:
    state: GraphState = {
        'incident_id': 'inc-1',
        'trace_id': 'trace-1',
        'raw_alert': '[告警] P1 order-api pod crashloop',
        'source_meta': {'chat_id': 'oc_test', 'msg_id': 'om_test', 'sender': 'user1', 'ts': 123},
        'category': None,
        'severity': None,
        'service': None,
        'is_duplicate': False,
        'diagnosis_messages': [],
        'evidence': {},
        'diagnosis_summary': None,
        'confidence': None,
        'proposals': [],
        'approval_decisions': {},
        'awaiting_since': None,
        'execution_results': [],
        'final_status': None,
    }
    with patch('app.graph.nodes.triage.classify_alert', new_callable=AsyncMock) as mock_classify:
        mock_classify.return_value = {
            'category': 'k8s_pod_crash',
            'severity': 'p1',
            'service': 'order-api',
        }
        result = await triage_node(state)
        assert result['category'] == 'k8s_pod_crash'
        assert result['severity'] == 'p1'
        assert result['service'] == 'order-api'
