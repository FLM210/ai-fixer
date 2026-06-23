import httpx
import pytest
import respx

from app.plugins.base import PluginContext
from app.plugins.builtin.sentry_get_issue import SentryGetIssue


@pytest.mark.asyncio
@respx.mock
async def test_sentry_get_issue_success() -> None:
    respx.get("https://sentry.example.com/api/0/issues/12345/").mock(
        return_value=httpx.Response(
            200, json={"id": "12345", "title": "TypeError: ...", "status": "unresolved"}
        )
    )
    plugin = SentryGetIssue(base_url="https://sentry.example.com", token="tok_abc")
    ctx = PluginContext(incident_id="i-1", actor="agent", trace_id="t-1")

    result = await plugin.execute(ctx, {"issue_id": "12345"})

    assert result.ok is True
    assert result.output["id"] == "12345"


@pytest.mark.asyncio
@respx.mock
async def test_sentry_get_issue_http_error() -> None:
    respx.get("https://sentry.example.com/api/0/issues/999/").mock(return_value=httpx.Response(404))
    plugin = SentryGetIssue(base_url="https://sentry.example.com", token="tok_abc")
    ctx = PluginContext(incident_id="i-1", actor="agent", trace_id="t-1")

    result = await plugin.execute(ctx, {"issue_id": "999"})

    assert result.ok is False
    assert "sentry.get_issue failed" in result.error


@pytest.mark.asyncio
async def test_sentry_get_issue_dry_run() -> None:
    plugin = SentryGetIssue(base_url="https://sentry.example.com", token="tok_abc")
    ctx = PluginContext(incident_id="i-1", actor="agent", trace_id="t-1", dry_run=True)

    result = await plugin.execute(ctx, {"issue_id": "12345"})

    assert result.ok is True
    assert result.output == {"dry_run": True}
