from unittest.mock import AsyncMock

import pytest

from app.plugins.base import PluginContext
from app.plugins.builtin.k8s_describe_node import K8sDescribeNode


@pytest.mark.asyncio
async def test_describe_node_success() -> None:
    mock_client = AsyncMock()
    mock_client.describe_node.return_value = {"node": "node-1", "status": "Ready"}
    plugin = K8sDescribeNode(k8s_client=mock_client)
    ctx = PluginContext(incident_id="i-1", actor="agent", trace_id="t-1")

    result = await plugin.execute(ctx, {"node_name": "node-1"})

    assert result.ok is True
    assert result.output["node"] == "node-1"
    mock_client.describe_node.assert_awaited_once_with("node-1")


@pytest.mark.asyncio
async def test_describe_node_failure() -> None:
    mock_client = AsyncMock()
    mock_client.describe_node.side_effect = RuntimeError("not found")
    plugin = K8sDescribeNode(k8s_client=mock_client)
    ctx = PluginContext(incident_id="i-1", actor="agent", trace_id="t-1")

    result = await plugin.execute(ctx, {"node_name": "node-1"})

    assert result.ok is False
    assert "not found" in result.error


@pytest.mark.asyncio
async def test_describe_node_dry_run() -> None:
    mock_client = AsyncMock()
    plugin = K8sDescribeNode(k8s_client=mock_client)
    ctx = PluginContext(incident_id="i-1", actor="agent", trace_id="t-1", dry_run=True)

    result = await plugin.execute(ctx, {"node_name": "node-1"})

    assert result.ok is True
    assert result.output == {"dry_run": True}
    mock_client.describe_node.assert_not_awaited()
