from unittest.mock import AsyncMock

import pytest

from app.plugins.base import PluginContext
from app.plugins.builtin.k8s_scale_deployment import K8sScaleDeployment


@pytest.fixture
def ctx() -> PluginContext:
    return PluginContext(incident_id="inc-1", actor="user1", trace_id="trace-1")


@pytest.mark.asyncio
async def test_scale_deployment_success(ctx: PluginContext) -> None:
    mock_k8s = AsyncMock()
    mock_k8s.scale_deployment.return_value = {"replicas": 5}
    plugin = K8sScaleDeployment(k8s_client=mock_k8s)
    result = await plugin.execute(ctx, {"namespace": "prod", "deployment": "order-api", "replicas": 5})
    assert result.ok is True
    assert result.output["replicas"] == 5


@pytest.mark.asyncio
async def test_scale_deployment_failure(ctx: PluginContext) -> None:
    mock_k8s = AsyncMock()
    mock_k8s.scale_deployment.side_effect = Exception("not found")
    plugin = K8sScaleDeployment(k8s_client=mock_k8s)
    result = await plugin.execute(ctx, {"namespace": "prod", "deployment": "missing", "replicas": 3})
    assert result.ok is False


@pytest.mark.asyncio
async def test_scale_deployment_dry_run(ctx: PluginContext) -> None:
    ctx_dry = PluginContext(incident_id="inc-1", actor="user1", trace_id="trace-1", dry_run=True)
    plugin = K8sScaleDeployment()
    result = await plugin.execute(ctx_dry, {"namespace": "prod", "deployment": "order-api", "replicas": 5})
    assert result.output == {"dry_run": True}
