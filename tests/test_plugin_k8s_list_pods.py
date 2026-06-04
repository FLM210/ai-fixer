from unittest.mock import AsyncMock

import pytest

from app.plugins.base import PluginContext
from app.plugins.builtin.k8s_list_pods import K8sListPods


@pytest.mark.asyncio
async def test_list_pods_success() -> None:
    mock_client = AsyncMock()
    mock_client.list_pods.return_value = [{"name": "web-1"}, {"name": "web-2"}]
    plugin = K8sListPods(k8s_client=mock_client)
    ctx = PluginContext(incident_id="i-1", actor="agent", trace_id="t-1")

    result = await plugin.execute(ctx, {"namespace": "prod"})

    assert result.ok is True
    assert len(result.output["pods"]) == 2
    mock_client.list_pods.assert_awaited_once_with("prod", label_selector=None)


@pytest.mark.asyncio
async def test_list_pods_with_label_selector() -> None:
    mock_client = AsyncMock()
    mock_client.list_pods.return_value = [{"name": "web-1"}]
    plugin = K8sListPods(k8s_client=mock_client)
    ctx = PluginContext(incident_id="i-1", actor="agent", trace_id="t-1")

    await plugin.execute(ctx, {"namespace": "prod", "label_selector": "app=web"})

    mock_client.list_pods.assert_awaited_once_with("prod", label_selector="app=web")


@pytest.mark.asyncio
async def test_list_pods_failure() -> None:
    mock_client = AsyncMock()
    mock_client.list_pods.side_effect = RuntimeError("forbidden")
    plugin = K8sListPods(k8s_client=mock_client)
    ctx = PluginContext(incident_id="i-1", actor="agent", trace_id="t-1")

    result = await plugin.execute(ctx, {"namespace": "prod"})

    assert result.ok is False
    assert "forbidden" in result.error


@pytest.mark.asyncio
async def test_list_pods_dry_run() -> None:
    mock_client = AsyncMock()
    plugin = K8sListPods(k8s_client=mock_client)
    ctx = PluginContext(incident_id="i-1", actor="agent", trace_id="t-1", dry_run=True)

    result = await plugin.execute(ctx, {"namespace": "prod"})

    assert result.ok is True
    assert result.output == {"dry_run": True}
    mock_client.list_pods.assert_not_awaited()
