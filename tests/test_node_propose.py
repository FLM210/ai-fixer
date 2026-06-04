from unittest.mock import AsyncMock, patch

import pytest

from app.graph.nodes.propose import generate_proposals, propose_node
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
        'proposals': [],
        'approval_decisions': {},
        'awaiting_since': None,
        'execution_results': [],
        'final_status': None,
    }
    base.update(overrides)  # type: ignore[arg-type]
    return base


@pytest.mark.asyncio
async def test_propose_generates_fixes() -> None:
    state = _make_state()
    with patch('app.graph.nodes.propose.generate_proposals', new_callable=AsyncMock) as mock_propose:
        mock_propose.return_value = [
            {
                'plugin_name': 'k8s.restart_pod',
                'args': {'namespace': 'prod', 'pod_name': 'app-xyz'},
                'risk_level': 'medium',
                'description': 'restart pod',
                'expected_outcome': 'pod restarts',
                'rollback_hint': None,
                'source': 'plugin',
            }
        ]
        result = await propose_node(state)
        assert len(result['proposals']) == 1
        assert result['proposals'][0]['plugin_name'] == 'k8s.restart_pod'


@pytest.mark.asyncio
async def test_propose_empty_on_llm_empty_array() -> None:
    """LLM returns empty JSON array -> proposals is empty."""
    from app.llm import LLMResponse

    state = _make_state()

    mock_client = AsyncMock()
    mock_client.complete = AsyncMock(return_value=LLMResponse(
        text='[]',
        tool_uses=[],
        stop_reason='end_turn',
    ))

    with (
        patch('app.graph.nodes.propose.build_llm_client', return_value=mock_client),
        patch('app.graph.nodes.propose.get_settings'),
        patch('app.graph.nodes.propose.global_registry') as mock_registry,
    ):
        mock_registry.list_specs.return_value = []
        result = await generate_proposals(state)

    assert result == []


@pytest.mark.asyncio
async def test_propose_empty_on_invalid_json() -> None:
    """LLM returns non-JSON -> proposals is empty."""
    from app.llm import LLMResponse

    state = _make_state()

    mock_client = AsyncMock()
    mock_client.complete = AsyncMock(return_value=LLMResponse(
        text='I am not JSON',
        tool_uses=[],
        stop_reason='end_turn',
    ))

    with (
        patch('app.graph.nodes.propose.build_llm_client', return_value=mock_client),
        patch('app.graph.nodes.propose.get_settings'),
        patch('app.graph.nodes.propose.global_registry') as mock_registry,
    ):
        mock_registry.list_specs.return_value = []
        result = await generate_proposals(state)

    assert result == []


@pytest.mark.asyncio
async def test_propose_empty_on_non_list_json() -> None:
    """LLM returns a JSON object instead of array -> proposals is empty."""
    from app.llm import LLMResponse

    state = _make_state()

    mock_client = AsyncMock()
    mock_client.complete = AsyncMock(return_value=LLMResponse(
        text='{"message": "no fix needed"}',
        tool_uses=[],
        stop_reason='end_turn',
    ))

    with (
        patch('app.graph.nodes.propose.build_llm_client', return_value=mock_client),
        patch('app.graph.nodes.propose.get_settings'),
        patch('app.graph.nodes.propose.global_registry') as mock_registry,
    ):
        mock_registry.list_specs.return_value = []
        result = await generate_proposals(state)

    assert result == []


@pytest.mark.asyncio
async def test_propose_parses_multiple_proposals() -> None:
    """LLM returns multiple proposals, all parsed correctly."""
    from app.llm import LLMResponse
    from app.plugins.base import PluginSpec

    state = _make_state()

    proposals_json = '''[
        {
            "plugin_name": "k8s.restart_pod",
            "args": {"namespace": "prod", "pod_name": "app-xyz"},
            "risk_level": "medium",
            "description": "restart pod",
            "expected_outcome": "pod restarts",
            "rollback_hint": null
        },
        {
            "plugin_name": "k8s.scale_deployment",
            "args": {"namespace": "prod", "deployment": "order-api", "replicas": 3},
            "risk_level": "low",
            "description": "scale deployment",
            "expected_outcome": "more replicas available",
            "rollback_hint": "scale back to 1"
        }
    ]'''

    mock_client = AsyncMock()
    mock_client.complete = AsyncMock(return_value=LLMResponse(
        text=proposals_json,
        tool_uses=[],
        stop_reason='end_turn',
    ))

    plugin_specs = [
        PluginSpec(
            name='k8s.restart_pod',
            category='remediation',
            description='Restart a pod',
            risk_level='medium',
            timeout_seconds=30,
            input_schema={},
        ),
        PluginSpec(
            name='k8s.scale_deployment',
            category='remediation',
            description='Scale a deployment',
            risk_level='low',
            timeout_seconds=30,
            input_schema={},
        ),
    ]

    with (
        patch('app.graph.nodes.propose.build_llm_client', return_value=mock_client),
        patch('app.graph.nodes.propose.get_settings'),
        patch('app.graph.nodes.propose.global_registry') as mock_registry,
    ):
        mock_registry.list_specs.return_value = plugin_specs
        result = await generate_proposals(state)

    assert len(result) == 2
    assert result[0]['plugin_name'] == 'k8s.restart_pod'
    assert result[0]['source'] == 'plugin'
    assert result[1]['plugin_name'] == 'k8s.scale_deployment'
    assert result[1]['rollback_hint'] == 'scale back to 1'


@pytest.mark.asyncio
async def test_propose_node_sets_proposals_on_state() -> None:
    """propose_node writes proposals back to state."""
    from app.llm import LLMResponse
    from app.plugins.base import PluginSpec

    state = _make_state()

    proposals_json = '''[
        {
            "plugin_name": "k8s.restart_pod",
            "args": {"namespace": "prod", "pod_name": "app-xyz"},
            "risk_level": "medium",
            "description": "restart pod",
            "expected_outcome": "pod restarts",
            "rollback_hint": null
        }
    ]'''

    mock_client = AsyncMock()
    mock_client.complete = AsyncMock(return_value=LLMResponse(
        text=proposals_json,
        tool_uses=[],
        stop_reason='end_turn',
    ))

    plugin_specs = [
        PluginSpec(
            name='k8s.restart_pod',
            category='remediation',
            description='Restart a pod',
            risk_level='medium',
            timeout_seconds=30,
            input_schema={},
        ),
    ]

    with (
        patch('app.graph.nodes.propose.build_llm_client', return_value=mock_client),
        patch('app.graph.nodes.propose.get_settings'),
        patch('app.graph.nodes.propose.global_registry') as mock_registry,
    ):
        mock_registry.list_specs.return_value = plugin_specs
        result = await propose_node(state)

    assert len(result['proposals']) == 1
    assert result['proposals'][0]['plugin_name'] == 'k8s.restart_pod'
    assert result['proposals'][0]['risk_level'] == 'medium'
