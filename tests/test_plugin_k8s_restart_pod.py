from unittest.mock import AsyncMock

import pytest

from app.plugins.base import PluginContext
from app.plugins.builtin.k8s_restart_pod import K8sRestartPod


@pytest.fixture
def ctx() -> PluginContext:
    return PluginContext(incident_id="inc-1", actor="user1", trace_id="trace-1")


@pytest.mark.asyncio
async def test_restart_pod_success(ctx: PluginContext) -> None:
    mock_k8s = AsyncMock()
    mock_k8s.delete_pod.return_value = {"status": "deleted"}
    plugin = K8sRestartPod(k8s_client=mock_k8s)
    result = await plugin.execute(
        ctx, {"namespace": "prod", "pod_name": "app-xyz", "reason": "OOMKilled"}
    )
    assert result.ok is True
    mock_k8s.delete_pod.assert_called_once_with("prod", "app-xyz")


@pytest.mark.asyncio
async def test_restart_pod_failure(ctx: PluginContext) -> None:
    mock_k8s = AsyncMock()
    mock_k8s.delete_pod.side_effect = Exception("forbidden")
    plugin = K8sRestartPod(k8s_client=mock_k8s)
    result = await plugin.execute(
        ctx, {"namespace": "prod", "pod_name": "app-xyz", "reason": "test"}
    )
    assert result.ok is False
    assert "forbidden" in result.error


@pytest.mark.asyncio
async def test_restart_pod_dry_run(ctx: PluginContext) -> None:
    ctx_dry = PluginContext(incident_id="inc-1", actor="user1", trace_id="trace-1", dry_run=True)
    plugin = K8sRestartPod()
    result = await plugin.execute(
        ctx_dry, {"namespace": "prod", "pod_name": "app-xyz", "reason": "test"}
    )
    assert result.ok is True
    assert result.output == {"dry_run": True}
