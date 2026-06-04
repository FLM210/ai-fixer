from unittest.mock import AsyncMock

import pytest

from app.plugins.base import PluginContext
from app.plugins.builtin.k8s_get_pod_logs import K8sGetPodLogs


@pytest.mark.asyncio
async def test_get_pod_logs_success() -> None:
    mock_client = AsyncMock()
    mock_client.get_pod_logs.return_value = "line1\nline2\n"
    plugin = K8sGetPodLogs(k8s_client=mock_client)
    ctx = PluginContext(incident_id="i-1", actor="agent", trace_id="t-1")

    result = await plugin.execute(ctx, {"namespace": "prod", "pod": "web-abc"})

    assert result.ok is True
    assert result.output["logs"] == "line1\nline2\n"
    mock_client.get_pod_logs.assert_awaited_once_with("prod", "web-abc", container=None, tail_lines=200)


@pytest.mark.asyncio
async def test_get_pod_logs_with_container() -> None:
    mock_client = AsyncMock()
    mock_client.get_pod_logs.return_value = "sidecar logs"
    plugin = K8sGetPodLogs(k8s_client=mock_client)
    ctx = PluginContext(incident_id="i-1", actor="agent", trace_id="t-1")

    result = await plugin.execute(ctx, {"namespace": "prod", "pod": "web-abc", "container": "sidecar", "tail_lines": 50})

    assert result.ok is True
    mock_client.get_pod_logs.assert_awaited_once_with("prod", "web-abc", container="sidecar", tail_lines=50)


@pytest.mark.asyncio
async def test_get_pod_logs_failure() -> None:
    mock_client = AsyncMock()
    mock_client.get_pod_logs.side_effect = RuntimeError("not found")
    plugin = K8sGetPodLogs(k8s_client=mock_client)
    ctx = PluginContext(incident_id="i-1", actor="agent", trace_id="t-1")

    result = await plugin.execute(ctx, {"namespace": "prod", "pod": "web-abc"})

    assert result.ok is False
    assert "not found" in result.error


@pytest.mark.asyncio
async def test_get_pod_logs_dry_run() -> None:
    mock_client = AsyncMock()
    plugin = K8sGetPodLogs(k8s_client=mock_client)
    ctx = PluginContext(incident_id="i-1", actor="agent", trace_id="t-1", dry_run=True)

    result = await plugin.execute(ctx, {"namespace": "prod", "pod": "web-abc"})

    assert result.ok is True
    assert result.output == {"dry_run": True}
    mock_client.get_pod_logs.assert_not_awaited()
