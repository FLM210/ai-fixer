import httpx
import pytest
import respx

from app.plugins.base import PluginContext
from app.plugins.builtin.prom_query import PromQuery


@pytest.mark.asyncio
@respx.mock
async def test_prom_query_success() -> None:
    respx.get("http://prometheus:9090/api/v1/query").mock(
        return_value=httpx.Response(200, json={"status": "success", "data": {"resultType": "vector", "result": []}})
    )
    plugin = PromQuery(base_url="http://prometheus:9090")
    ctx = PluginContext(incident_id="i-1", actor="agent", trace_id="t-1")

    result = await plugin.execute(ctx, {"query": "up"})

    assert result.ok is True
    assert result.output["status"] == "success"


@pytest.mark.asyncio
@respx.mock
async def test_prom_query_http_error() -> None:
    respx.get("http://prometheus:9090/api/v1/query").mock(return_value=httpx.Response(500))
    plugin = PromQuery(base_url="http://prometheus:9090")
    ctx = PluginContext(incident_id="i-1", actor="agent", trace_id="t-1")

    result = await plugin.execute(ctx, {"query": "up"})

    assert result.ok is False
    assert "prom.query failed" in result.error


@pytest.mark.asyncio
async def test_prom_query_dry_run() -> None:
    plugin = PromQuery(base_url="http://prometheus:9090")
    ctx = PluginContext(incident_id="i-1", actor="agent", trace_id="t-1", dry_run=True)

    result = await plugin.execute(ctx, {"query": "up"})

    assert result.ok is True
    assert result.output == {"dry_run": True}
