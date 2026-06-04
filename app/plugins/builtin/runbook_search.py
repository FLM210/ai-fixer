from typing import Any, ClassVar

import httpx

from app.plugins.base import Plugin, PluginContext, PluginResult, PluginSpec
from app.plugins.registry import global_registry, register


@register(global_registry)
class RunbookSearch(Plugin):
    _SCHEMA: ClassVar[dict[str, Any]] = {
        "type": "object",
        "properties": {
            "query": {"type": "string", "minLength": 1},
            "limit": {"type": "integer", "default": 5},
        },
        "required": ["query"],
        "additionalProperties": False,
    }

    def __init__(self, base_url: str = "") -> None:
        self._base_url = base_url

    @property
    def spec(self) -> PluginSpec:
        return PluginSpec(
            name="runbook.search",
            category="diagnostic",
            description="搜索 Runbook",
            risk_level="low",
            timeout_seconds=15,
            input_schema=self._SCHEMA,
        )

    async def execute(self, ctx: PluginContext, args: dict[str, Any]) -> PluginResult:
        if ctx.dry_run:
            return PluginResult(ok=True, output={"dry_run": True})

        if not self._base_url:
            return PluginResult(ok=True, output={"results": [], "note": "no base_url configured"})

        params: dict[str, Any] = {
            "query": args["query"],
            "limit": args.get("limit", 5),
        }

        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(f"{self._base_url}/search", params=params, timeout=10)
                resp.raise_for_status()
                data = resp.json()
        except Exception as e:
            return PluginResult(ok=False, output={}, error=f"runbook.search failed: {e}")

        return PluginResult(ok=True, output=data)
