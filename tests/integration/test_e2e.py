"""E2E 集成测试: 模拟完整的告警处理流程。"""

from unittest.mock import AsyncMock, patch

from app.graph.state import ExecutionRecord, GraphState


def _make_initial_state(trace_id: str) -> GraphState:
    """构造初始 GraphState。"""
    return GraphState(
        incident_id='',
        trace_id=trace_id,
        raw_alert='[告警] P1 order-api pod crashloop',
        source_meta={'chat_id': 'oc_test', 'msg_id': 'om_test', 'sender': 'bot_alert', 'ts': 123},
        category=None,
        severity=None,
        service=None,
        is_duplicate=False,
        diagnosis_messages=[],
        evidence={},
        diagnosis_summary=None,
        confidence=None,
        proposals=[],
        approval_decisions={},
        awaiting_since=None,
        execution_results=[],
        final_status=None,
    )


async def test_e2e_alert_to_resolve() -> None:
    """端到端: 告警 → 诊断 → 修复建议 → 审批 → 执行 → 验证 → 结案。"""
    state = _make_initial_state('trace-e2e-1')

    with (
        patch('app.graph.nodes.ingest.create_incident', new_callable=AsyncMock) as mock_ingest,
        patch('app.graph.nodes.triage.classify_alert', new_callable=AsyncMock) as mock_triage,
        patch('app.graph.nodes.diagnose.run_diagnose_loop', new_callable=AsyncMock) as mock_diagnose,
        patch('app.graph.nodes.propose.generate_proposals', new_callable=AsyncMock) as mock_propose,
        patch('app.graph.nodes.await_approval.send_card', new_callable=AsyncMock) as mock_card,
        patch('app.graph.nodes.execute.execute_plugin', new_callable=AsyncMock) as mock_exec,
        patch('app.graph.nodes.verify.check_recovery', new_callable=AsyncMock) as mock_verify,
        patch('app.graph.nodes.resolve.send_resolve_card', new_callable=AsyncMock) as mock_resolve,
    ):
        mock_ingest.return_value = {'id': 'inc-e2e', 'fingerprint': 'fp-e2e', 'is_duplicate': False}
        mock_triage.return_value = {'category': 'k8s_pod_crash', 'severity': 'p1', 'service': 'order-api'}
        mock_diagnose.return_value = {
            'diagnosis_summary': 'Pod OOMKilled',
            'confidence': 0.9,
            'evidence': {'k8s.describe_pod': [{'phase': 'CrashLoopBackOff'}]},
            'diagnosis_messages': [],
        }
        mock_propose.return_value = [
            {
                'plugin_name': 'k8s.restart_pod',
                'args': {'namespace': 'prod', 'pod_name': 'app-xyz', 'reason': 'OOMKilled'},
                'risk_level': 'medium',
                'description': 'restart pod',
                'expected_outcome': 'pod restarts',
                'rollback_hint': None,
                'source': 'plugin',
            },
        ]
        mock_card.return_value = {'message_id': 'om_card_e2e'}
        mock_exec.return_value = ExecutionRecord(
            proposal_id='prop-0',
            plugin_name='k8s.restart_pod',
            status='success',
            output={'deleted': True},
            error=None,
            duration_ms=1500,
        )
        mock_verify.return_value = True
        mock_resolve.return_value = None

        # ---- ingest ----
        from app.graph.nodes.ingest import ingest_node
        state = await ingest_node(state)
        assert state['incident_id'] == 'inc-e2e'
        assert state['is_duplicate'] is False

        # ---- triage ----
        from app.graph.nodes.triage import triage_node
        state = await triage_node(state)
        assert state['category'] == 'k8s_pod_crash'
        assert state['severity'] == 'p1'
        assert state['service'] == 'order-api'

        # ---- diagnose ----
        from app.graph.nodes.diagnose import diagnose_node
        state = await diagnose_node(state)
        assert state['diagnosis_summary'] == 'Pod OOMKilled'
        assert state['confidence'] == 0.9

        # ---- propose ----
        from app.graph.nodes.propose import propose_node
        state = await propose_node(state)
        assert len(state['proposals']) == 1

        # ---- 模拟审批 ----
        state['approval_decisions'] = {'prop-0': 'approved'}

        # ---- await_approval ----
        from app.graph.nodes.await_approval import await_approval_node
        state = await await_approval_node(state)
        assert state['awaiting_since'] is not None

        # ---- execute ----
        from app.graph.nodes.execute import execute_node
        state = await execute_node(state)
        assert len(state['execution_results']) == 1
        assert state['execution_results'][0]['status'] == 'success'

        # ---- verify ----
        from app.graph.nodes.verify import verify_node
        state = await verify_node(state)
        assert state['final_status'] == 'resolved'

        # ---- resolve ----
        from app.graph.nodes.resolve import resolve_node
        state = await resolve_node(state)
        assert state['final_status'] == 'resolved'

        # ---- 验证所有 mock 被调用 ----
        mock_ingest.assert_called_once()
        mock_triage.assert_called_once()
        mock_diagnose.assert_called_once()
        mock_propose.assert_called_once()
        mock_card.assert_called_once()
        mock_exec.assert_called_once()
        mock_verify.assert_called_once()
        mock_resolve.assert_called_once()


async def test_e2e_duplicate_alert_skipped() -> None:
    """端到端: 重复告警被跳过。"""
    state = _make_initial_state('trace-e2e-2')

    with patch('app.graph.nodes.ingest.create_incident', new_callable=AsyncMock) as mock_ingest:
        mock_ingest.return_value = {'id': 'inc-dup', 'fingerprint': 'fp-dup', 'is_duplicate': True}

        from app.graph.nodes.ingest import ingest_node
        state = await ingest_node(state)
        assert state['is_duplicate'] is True
