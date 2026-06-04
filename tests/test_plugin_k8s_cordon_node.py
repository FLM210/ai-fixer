from unittest.mock import AsyncMock

import pytest

from app.plugins.base import PluginContext
from app.plugins.builtin.k8s_cordon_node import K8sCordonNode


@pytest.fixture
def ctx() -> PluginContext:
    return PluginContext(incident_id="inc-1", actor="user1", trace_id="trace-1")


@pytest.mark.asyncio
async def test_cordon_node_success(ctx: PluginContext) -> None:
    mock_k8s = AsyncMock()
    mock_k8s.cordon_node.return_value = {"cordoned": True}
    plugin = K8sCordonNode(k8s_client=mock_k8s)
    result = await plugin.execute(ctx, {"node_name": "node-1", "reason": "disk pressure"})
    assert result.ok is True
    assert result.output["cordoned"] is True


@pytest.mark.asyncio
async def test_cordon_node_failure(ctx: PluginContext) -> None:
    mock_k8s = AsyncMock()
    mock_k8s.cordon_node.side_effect = Exception("not found")
    plugin = K8sCordonNode(k8s_client=mock_k8s)
    result = await plugin.execute(ctx, {"node_name": "missing", "reason": "test"})
    assert result.ok is False


@pytest.mark.asyncio
async def test_cordon_node_dry_run(ctx: PluginContext) -> None:
    ctx_dry = PluginContext(incident_id="inc-1", actor="user1", trace_id="trace-1", dry_run=True)
    plugin = K8sCordonNode()
    result = await plugin.execute(ctx_dry, {"node_name": "node-1", "reason": "test"})
    assert result.output == {"dry_run": True}
