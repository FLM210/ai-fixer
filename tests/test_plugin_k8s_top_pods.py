from unittest.mock import AsyncMock

import pytest

from app.plugins.base import PluginContext
from app.plugins.builtin.k8s_top_pods import K8sTopPods


@pytest.mark.asyncio
async def test_top_pods_success() -> None:
    mock_client = AsyncMock()
    mock_client.top_pods.return_value = [{"pod": "web-1", "cpu": "100m"}]
    plugin = K8sTopPods(k8s_client=mock_client)
    ctx = PluginContext(incident_id="i-1", actor="agent", trace_id="t-1")

    result = await plugin.execute(ctx, {"namespace": "prod"})

    assert result.ok is True
    assert len(result.output["pods"]) == 1
    mock_client.top_pods.assert_awaited_once_with("prod", sort_by="cpu")


@pytest.mark.asyncio
async def test_top_pods_sort_by_memory() -> None:
    mock_client = AsyncMock()
    mock_client.top_pods.return_value = []
    plugin = K8sTopPods(k8s_client=mock_client)
    ctx = PluginContext(incident_id="i-1", actor="agent", trace_id="t-1")

    await plugin.execute(ctx, {"namespace": "prod", "sort_by": "memory"})

    mock_client.top_pods.assert_awaited_once_with("prod", sort_by="memory")


@pytest.mark.asyncio
async def test_top_pods_failure() -> None:
    mock_client = AsyncMock()
    mock_client.top_pods.side_effect = RuntimeError("metrics not available")
    plugin = K8sTopPods(k8s_client=mock_client)
    ctx = PluginContext(incident_id="i-1", actor="agent", trace_id="t-1")

    result = await plugin.execute(ctx, {"namespace": "prod"})

    assert result.ok is False
    assert "metrics not available" in result.error


@pytest.mark.asyncio
async def test_top_pods_dry_run() -> None:
    mock_client = AsyncMock()
    plugin = K8sTopPods(k8s_client=mock_client)
    ctx = PluginContext(incident_id="i-1", actor="agent", trace_id="t-1", dry_run=True)

    result = await plugin.execute(ctx, {"namespace": "prod"})

    assert result.ok is True
    assert result.output == {"dry_run": True}
    mock_client.top_pods.assert_not_awaited()
