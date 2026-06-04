from typing import Any, ClassVar

import httpx

from app.plugins.base import Plugin, PluginContext, PluginResult, PluginSpec
from app.plugins.registry import global_registry, register


@register(global_registry)
class LokiQuery(Plugin):
    _SCHEMA: ClassVar[dict[str, Any]] = {
        "type": "object",
        "properties": {
            "query": {"type": "string", "minLength": 1},
            "limit": {"type": "integer", "default": 100},
            "start": {"type": "string"},
            "end": {"type": "string"},
        },
        "required": ["query"],
        "additionalProperties": False,
    }

    def __init__(self, base_url: str = "http://loki:3100") -> None:
        self._base_url = base_url

    @property
    def spec(self) -> PluginSpec:
        return PluginSpec(
            name="loki.query",
            category="diagnostic",
            description="Loki 日志查询",
            risk_level="low",
            timeout_seconds=15,
            input_schema=self._SCHEMA,
        )

    async def execute(self, ctx: PluginContext, args: dict[str, Any]) -> PluginResult:
        if ctx.dry_run:
            return PluginResult(ok=True, output={"dry_run": True})

        params: dict[str, Any] = {
            "query": args["query"],
            "limit": args.get("limit", 100),
        }
        if "start" in args:
            params["start"] = args["start"]
        if "end" in args:
            params["end"] = args["end"]

        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(f"{self._base_url}/loki/api/v1/query_range", params=params, timeout=10)
                resp.raise_for_status()
                data = resp.json()
        except Exception as e:
            return PluginResult(ok=False, output={}, error=f"loki.query failed: {e}")

        return PluginResult(ok=True, output=data)
