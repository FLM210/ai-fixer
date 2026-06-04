from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from app.graph.nodes.execute import execute_node
from app.graph.state import GraphState


@pytest.mark.asyncio
async def test_execute_calls_approved_plugins() -> None:
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
        'proposals': [
            {
                'plugin_name': 'k8s.restart_pod',
                'args': {'namespace': 'prod', 'pod_name': 'app-xyz'},
                'risk_level': 'medium',
                'description': 'restart pod',
                'expected_outcome': 'pod restarts',
                'rollback_hint': None,
                'source': 'plugin',
            }
        ],
        'approval_decisions': {'prop-0': 'approved'},
        'awaiting_since': None,
        'execution_results': [],
        'final_status': None,
    }
    with patch('app.graph.nodes.execute.execute_plugin', new_callable=AsyncMock) as mock_exec:
        mock_exec.return_value = {
            'proposal_id': 'prop-0',
            'plugin_name': 'k8s.restart_pod',
            'status': 'success',
            'output': {'deleted': True},
            'error': None,
            'duration_ms': 3200,
        }
        result = await execute_node(state)
        assert len(result['execution_results']) == 1
        assert result['execution_results'][0]['status'] == 'success'
