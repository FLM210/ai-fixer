from unittest.mock import AsyncMock

import pytest

from app.plugins.base import PluginContext
from app.plugins.builtin.k8s_rollback_deployment import K8sRollbackDeployment


@pytest.fixture
def ctx() -> PluginContext:
    return PluginContext(incident_id="inc-1", actor="user1", trace_id="trace-1")


@pytest.mark.asyncio
async def test_rollback_deployment_success(ctx: PluginContext) -> None:
    mock_k8s = AsyncMock()
    mock_k8s.rollback_deployment.return_value = {"revision": 3}
    plugin = K8sRollbackDeployment(k8s_client=mock_k8s)
    result = await plugin.execute(ctx, {"namespace": "prod", "deployment": "order-api"})
    assert result.ok is True
    assert result.output["revision"] == 3


@pytest.mark.asyncio
async def test_rollback_deployment_failure(ctx: PluginContext) -> None:
    mock_k8s = AsyncMock()
    mock_k8s.rollback_deployment.side_effect = Exception("no revision")
    plugin = K8sRollbackDeployment(k8s_client=mock_k8s)
    result = await plugin.execute(ctx, {"namespace": "prod", "deployment": "order-api"})
    assert result.ok is False


@pytest.mark.asyncio
async def test_rollback_deployment_dry_run(ctx: PluginContext) -> None:
    ctx_dry = PluginContext(incident_id="inc-1", actor="user1", trace_id="trace-1", dry_run=True)
    plugin = K8sRollbackDeployment()
    result = await plugin.execute(ctx_dry, {"namespace": "prod", "deployment": "order-api"})
    assert result.output == {"dry_run": True}
