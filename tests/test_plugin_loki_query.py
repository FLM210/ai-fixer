import httpx
import pytest
import respx

from app.plugins.base import PluginContext
from app.plugins.builtin.loki_query import LokiQuery


@pytest.mark.asyncio
@respx.mock
async def test_loki_query_success() -> None:
    respx.get("http://loki:3100/loki/api/v1/query_range").mock(
        return_value=httpx.Response(200, json={"status": "success", "data": {"result": []}})
    )
    plugin = LokiQuery(base_url="http://loki:3100")
    ctx = PluginContext(incident_id="i-1", actor="agent", trace_id="t-1")

    result = await plugin.execute(ctx, {"query": '{app="web"}'})

    assert result.ok is True
    assert result.output["status"] == "success"


@pytest.mark.asyncio
@respx.mock
async def test_loki_query_http_error() -> None:
    respx.get("http://loki:3100/loki/api/v1/query_range").mock(return_value=httpx.Response(500))
    plugin = LokiQuery(base_url="http://loki:3100")
    ctx = PluginContext(incident_id="i-1", actor="agent", trace_id="t-1")

    result = await plugin.execute(ctx, {"query": '{app="web"}'})

    assert result.ok is False
    assert "loki.query failed" in result.error


@pytest.mark.asyncio
async def test_loki_query_dry_run() -> None:
    plugin = LokiQuery(base_url="http://loki:3100")
    ctx = PluginContext(incident_id="i-1", actor="agent", trace_id="t-1", dry_run=True)

    result = await plugin.execute(ctx, {"query": '{app="web"}'})

    assert result.ok is True
    assert result.output == {"dry_run": True}
