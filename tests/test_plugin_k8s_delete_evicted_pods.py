from unittest.mock import AsyncMock

import pytest

from app.plugins.base import PluginContext
from app.plugins.builtin.k8s_delete_evicted_pods import K8sDeleteEvictedPods


@pytest.fixture
def ctx() -> PluginContext:
    return PluginContext(incident_id="inc-1", actor="user1", trace_id="trace-1")


@pytest.mark.asyncio
async def test_delete_evicted_pods_success(ctx: PluginContext) -> None:
    mock_k8s = AsyncMock()
    mock_k8s.delete_evicted_pods.return_value = {"deleted_count": 3}
    plugin = K8sDeleteEvictedPods(k8s_client=mock_k8s)
    result = await plugin.execute(ctx, {"namespace": "prod"})
    assert result.ok is True
    assert result.output["deleted_count"] == 3


@pytest.mark.asyncio
async def test_delete_evicted_pods_failure(ctx: PluginContext) -> None:
    mock_k8s = AsyncMock()
    mock_k8s.delete_evicted_pods.side_effect = Exception("forbidden")
    plugin = K8sDeleteEvictedPods(k8s_client=mock_k8s)
    result = await plugin.execute(ctx, {"namespace": "prod"})
    assert result.ok is False


@pytest.mark.asyncio
async def test_delete_evicted_pods_dry_run(ctx: PluginContext) -> None:
    ctx_dry = PluginContext(incident_id="inc-1", actor="user1", trace_id="trace-1", dry_run=True)
    plugin = K8sDeleteEvictedPods()
    result = await plugin.execute(ctx_dry, {"namespace": "prod"})
    assert result.output == {"dry_run": True}
