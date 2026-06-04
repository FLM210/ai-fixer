from typing import Any, ClassVar

import httpx

from app.plugins.base import Plugin, PluginContext, PluginResult, PluginSpec
from app.plugins.registry import global_registry, register


@register(global_registry)
class SentryGetIssue(Plugin):
    _SCHEMA: ClassVar[dict[str, Any]] = {
        "type": "object",
        "properties": {
            "issue_id": {"type": "string", "minLength": 1},
        },
        "required": ["issue_id"],
        "additionalProperties": False,
    }

    def __init__(self, base_url: str = "", token: str = "") -> None:
        self._base_url = base_url
        self._token = token

    @property
    def spec(self) -> PluginSpec:
        return PluginSpec(
            name="sentry.get_issue",
            category="diagnostic",
            description="获取 Sentry issue 详情",
            risk_level="low",
            timeout_seconds=15,
            input_schema=self._SCHEMA,
        )

    async def execute(self, ctx: PluginContext, args: dict[str, Any]) -> PluginResult:
        if ctx.dry_run:
            return PluginResult(ok=True, output={"dry_run": True})

        issue_id = args["issue_id"]
        url = f"{self._base_url}/api/0/issues/{issue_id}/"
        headers = {"Authorization": f"Bearer {self._token}"} if self._token else {}

        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(url, headers=headers, timeout=10)
                resp.raise_for_status()
                data = resp.json()
        except Exception as e:
            return PluginResult(ok=False, output={}, error=f"sentry.get_issue failed: {e}")

        return PluginResult(ok=True, output=data)
