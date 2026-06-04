from __future__ import annotations

import time
from typing import Any

from app.graph.state import ExecutionRecord, GraphState
from app.plugins import PluginContext, global_registry


async def execute_plugin(proposal: dict[str, Any], state: GraphState) -> ExecutionRecord:
    plugin_name = proposal['plugin_name']
    plugin = global_registry.get(plugin_name)
    ctx = PluginContext(
        incident_id=state['incident_id'],
        actor='system',
        trace_id=state['trace_id'],
    )

    start = time.monotonic()
    try:
        result = await plugin.execute(ctx, proposal['args'])
        duration_ms = int((time.monotonic() - start) * 1000)
        return ExecutionRecord(
            proposal_id=proposal.get('id', ''),
            plugin_name=plugin_name,
            status='success' if result.ok else 'failure',
            output=result.output,
            error=result.error,
            duration_ms=duration_ms,
        )
    except Exception as e:
        duration_ms = int((time.monotonic() - start) * 1000)
        return ExecutionRecord(
            proposal_id=proposal.get('id', ''),
            plugin_name=plugin_name,
            status='failure',
            output={},
            error=str(e),
            duration_ms=duration_ms,
        )


async def execute_node(state: GraphState) -> GraphState:
    results: list[ExecutionRecord] = []
    decisions = state.get('approval_decisions', {})

    for i, proposal in enumerate(state.get('proposals', [])):
        proposal_id = f'prop-{i}'
        if decisions.get(proposal_id) != 'approved':
            continue

        result = await execute_plugin({**proposal, 'id': proposal_id}, state)
        results.append(result)

    state['execution_results'] = results
    return state
