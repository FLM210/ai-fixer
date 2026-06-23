import httpx
import pytest
import respx

from app.plugins.base import PluginContext
from app.plugins.builtin.prom_query_range import PromQueryRange


@pytest.mark.asyncio
@respx.mock
async def test_prom_query_range_success() -> None:
    respx.get("http://prometheus:9090/api/v1/query_range").mock(
        return_value=httpx.Response(
            200, json={"status": "success", "data": {"resultType": "matrix", "result": []}}
        )
    )
    plugin = PromQueryRange(base_url="http://prometheus:9090")
    ctx = PluginContext(incident_id="i-1", actor="agent", trace_id="t-1")

    result = await plugin.execute(
        ctx, {"query": "up", "start": "2024-01-01T00:00:00Z", "end": "2024-01-01T01:00:00Z"}
    )

    assert result.ok is True
    assert result.output["status"] == "success"


@pytest.mark.asyncio
@respx.mock
async def test_prom_query_range_http_error() -> None:
    respx.get("http://prometheus:9090/api/v1/query_range").mock(return_value=httpx.Response(400))
    plugin = PromQueryRange(base_url="http://prometheus:9090")
    ctx = PluginContext(incident_id="i-1", actor="agent", trace_id="t-1")

    result = await plugin.execute(
        ctx, {"query": "up", "start": "2024-01-01T00:00:00Z", "end": "2024-01-01T01:00:00Z"}
    )

    assert result.ok is False
    assert "prom.query_range failed" in result.error


@pytest.mark.asyncio
async def test_prom_query_range_dry_run() -> None:
    plugin = PromQueryRange(base_url="http://prometheus:9090")
    ctx = PluginContext(incident_id="i-1", actor="agent", trace_id="t-1", dry_run=True)

    result = await plugin.execute(
        ctx, {"query": "up", "start": "2024-01-01T00:00:00Z", "end": "2024-01-01T01:00:00Z"}
    )

    assert result.ok is True
    assert result.output == {"dry_run": True}
