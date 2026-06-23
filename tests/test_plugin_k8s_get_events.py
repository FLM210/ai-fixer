from unittest.mock import AsyncMock

import pytest

from app.plugins.base import PluginContext
from app.plugins.builtin.k8s_get_events import K8sGetEvents


@pytest.mark.asyncio
async def test_get_events_success() -> None:
    mock_client = AsyncMock()
    mock_client.get_events.return_value = [{"reason": "Pulled", "message": "image pulled"}]
    plugin = K8sGetEvents(k8s_client=mock_client)
    ctx = PluginContext(incident_id="i-1", actor="agent", trace_id="t-1")

    result = await plugin.execute(ctx, {"namespace": "prod"})

    assert result.ok is True
    assert len(result.output["events"]) == 1
    mock_client.get_events.assert_awaited_once_with("prod", field_selector=None, limit=50)


@pytest.mark.asyncio
async def test_get_events_with_field_selector() -> None:
    mock_client = AsyncMock()
    mock_client.get_events.return_value = []
    plugin = K8sGetEvents(k8s_client=mock_client)
    ctx = PluginContext(incident_id="i-1", actor="agent", trace_id="t-1")

    await plugin.execute(
        ctx, {"namespace": "prod", "field_selector": "involvedObject.name=web-1", "limit": 10}
    )

    mock_client.get_events.assert_awaited_once_with(
        "prod", field_selector="involvedObject.name=web-1", limit=10
    )


@pytest.mark.asyncio
async def test_get_events_failure() -> None:
    mock_client = AsyncMock()
    mock_client.get_events.side_effect = RuntimeError("timeout")
    plugin = K8sGetEvents(k8s_client=mock_client)
    ctx = PluginContext(incident_id="i-1", actor="agent", trace_id="t-1")

    result = await plugin.execute(ctx, {"namespace": "prod"})

    assert result.ok is False
    assert "timeout" in result.error


@pytest.mark.asyncio
async def test_get_events_dry_run() -> None:
    mock_client = AsyncMock()
    plugin = K8sGetEvents(k8s_client=mock_client)
    ctx = PluginContext(incident_id="i-1", actor="agent", trace_id="t-1", dry_run=True)

    result = await plugin.execute(ctx, {"namespace": "prod"})

    assert result.ok is True
    assert result.output == {"dry_run": True}
    mock_client.get_events.assert_not_awaited()
