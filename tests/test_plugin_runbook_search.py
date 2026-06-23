import httpx
import pytest
import respx

from app.plugins.base import PluginContext
from app.plugins.builtin.runbook_search import RunbookSearch


@pytest.mark.asyncio
@respx.mock
async def test_runbook_search_success() -> None:
    respx.get("https://runbook.example.com/search").mock(
        return_value=httpx.Response(
            200, json={"results": [{"title": "Restart nginx", "url": "https://rb.io/1"}]}
        )
    )
    plugin = RunbookSearch(base_url="https://runbook.example.com")
    ctx = PluginContext(incident_id="i-1", actor="agent", trace_id="t-1")

    result = await plugin.execute(ctx, {"query": "nginx restart"})

    assert result.ok is True
    assert len(result.output["results"]) == 1


@pytest.mark.asyncio
@respx.mock
async def test_runbook_search_http_error() -> None:
    respx.get("https://runbook.example.com/search").mock(return_value=httpx.Response(500))
    plugin = RunbookSearch(base_url="https://runbook.example.com")
    ctx = PluginContext(incident_id="i-1", actor="agent", trace_id="t-1")

    result = await plugin.execute(ctx, {"query": "nginx"})

    assert result.ok is False
    assert "runbook.search failed" in result.error


@pytest.mark.asyncio
async def test_runbook_search_no_base_url() -> None:
    plugin = RunbookSearch(base_url="")
    ctx = PluginContext(incident_id="i-1", actor="agent", trace_id="t-1")

    result = await plugin.execute(ctx, {"query": "nginx"})

    assert result.ok is True
    assert result.output["results"] == []
    assert result.output["note"] == "no base_url configured"


@pytest.mark.asyncio
async def test_runbook_search_dry_run() -> None:
    plugin = RunbookSearch(base_url="https://runbook.example.com")
    ctx = PluginContext(incident_id="i-1", actor="agent", trace_id="t-1", dry_run=True)

    result = await plugin.execute(ctx, {"query": "nginx"})

    assert result.ok is True
    assert result.output == {"dry_run": True}
