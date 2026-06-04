from __future__ import annotations

import json
from unittest.mock import AsyncMock, patch

import pytest

from app.graph.nodes.await_approval import (
    await_approval_node,
    build_diagnosis_card,
    send_card,
)
from app.graph.state import GraphState


def _make_state(**overrides: object) -> GraphState:
    base: GraphState = {
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
        'approval_decisions': {},
        'awaiting_since': None,
        'execution_results': [],
        'final_status': None,
    }
    base.update(overrides)  # type: ignore[arg-type]
    return base


@pytest.mark.asyncio
async def test_await_approval_renders_card() -> None:
    state = _make_state()
    with patch('app.graph.nodes.await_approval.send_card', new_callable=AsyncMock) as mock_send:
        mock_send.return_value = {'message_id': 'om_card_1'}
        result = await await_approval_node(state)
        assert result['awaiting_since'] is not None
        mock_send.assert_called_once()


@pytest.mark.asyncio
async def test_await_approval_sends_to_correct_chat() -> None:
    state = _make_state()
    with patch('app.graph.nodes.await_approval.send_card', new_callable=AsyncMock) as mock_send:
        mock_send.return_value = {'message_id': 'om_card_1'}
        await await_approval_node(state)
        call_args = mock_send.call_args
        assert call_args[0][0] == 'oc_test'


@pytest.mark.asyncio
async def test_await_approval_passes_card_json() -> None:
    state = _make_state()
    with patch('app.graph.nodes.await_approval.send_card', new_callable=AsyncMock) as mock_send:
        mock_send.return_value = {'message_id': 'om_card_1'}
        await await_approval_node(state)
        card_json = mock_send.call_args[0][1]
        card = json.loads(card_json)
        assert card['type'] == 'template'
        assert card['data']['template_id'] == 'diagnosis_approval'
        assert card['data']['template_variable']['incident_id'] == 'inc-1'
        assert card['data']['template_variable']['severity'] == 'p1'
        assert card['data']['template_variable']['service'] == 'order-api'
        assert card['data']['template_variable']['diagnosis_summary'] == 'Pod OOMKilled'
        assert card['data']['template_variable']['confidence'] == 0.85


@pytest.mark.asyncio
async def test_send_card_returns_message_id() -> None:
    result = await send_card('oc_test', '{}')
    assert 'message_id' in result


def test_build_diagnosis_card_structure() -> None:
    state = _make_state()
    card_json = build_diagnosis_card(state)
    card = json.loads(card_json)
    assert card['type'] == 'template'
    assert 'template_variable' in card['data']
    proposals = card['data']['template_variable']['proposals']
    assert len(proposals) == 1
    assert proposals[0]['plugin_name'] == 'k8s.restart_pod'
