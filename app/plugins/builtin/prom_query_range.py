from typing import Any, ClassVar

import httpx

from app.plugins.base import Plugin, PluginContext, PluginResult, PluginSpec
from app.plugins.registry import global_registry, register


@register(global_registry)
class PromQueryRange(Plugin):
    _SCHEMA: ClassVar[dict[str, Any]] = {
        "type": "object",
        "properties": {
            "query": {"type": "string", "minLength": 1},
            "start": {"type": "string", "minLength": 1},
            "end": {"type": "string", "minLength": 1},
            "step": {"type": "string", "default": "60s"},
        },
        "required": ["query", "start", "end"],
        "additionalProperties": False,
    }

    def __init__(self, base_url: str = "http://prometheus:9090") -> None:
        self._base_url = base_url

    @property
    def spec(self) -> PluginSpec:
        return PluginSpec(
            name="prom.query_range",
            category="diagnostic",
            description="Prometheus 范围查询",
            risk_level="low",
            timeout_seconds=15,
            input_schema=self._SCHEMA,
        )

    async def execute(self, ctx: PluginContext, args: dict[str, Any]) -> PluginResult:
        if ctx.dry_run:
            return PluginResult(ok=True, output={"dry_run": True})

        params: dict[str, Any] = {
            "query": args["query"],
            "start": args["start"],
            "end": args["end"],
            "step": args.get("step", "60s"),
        }

        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    f"{self._base_url}/api/v1/query_range", params=params, timeout=10
                )
                resp.raise_for_status()
                data = resp.json()
        except Exception as e:
            return PluginResult(ok=False, output={}, error=f"prom.query_range failed: {e}")

        return PluginResult(ok=True, output=data)
