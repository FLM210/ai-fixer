from typing import Any, ClassVar

from app.plugins.base import PluginContext, PluginResult, PluginSpec
from app.plugins.builtin.postgres._base import PostgresPluginBase
from app.plugins.registry import global_registry, register

_QUERY = """
SELECT
    pid,
    now() - pg_stat_activity.query_start AS duration,
    query,
    state,
    wait_event_type,
    wait_event
FROM pg_stat_activity
WHERE state != 'idle'
    AND query NOT ILIKE '%pg_stat_activity%'
    AND now() - pg_stat_activity.query_start > interval '5 seconds'
ORDER BY duration DESC
LIMIT 20;
"""


@register(global_registry)
class PgSlowQueries(PostgresPluginBase):
    _SCHEMA: ClassVar[dict[str, Any]] = {
        "type": "object",
        "properties": {
            "dsn": {"type": "string", "description": "PostgreSQL DSN（可选）"},
            "min_duration_seconds": {"type": "integer", "minimum": 1, "default": 5},
        },
        "additionalProperties": False,
    }

    @property
    def spec(self) -> PluginSpec:
        return PluginSpec(
            name="pg.slow_queries",
            category="diagnostic",
            resource_type="database",
            description="查询当前正在执行的慢查询（超过 5 秒），包含 PID、持续时间、SQL 文本、等待事件",
            risk_level="low",
            timeout_seconds=10,
            input_schema=self._SCHEMA,
        )

    async def execute(self, ctx: PluginContext, args: dict[str, Any]) -> PluginResult:
        min_sec = args.get("min_duration_seconds", 5)
        query = _QUERY.replace("interval '5 seconds'", f"interval '{min_sec} seconds'")
        return await self._execute_query(ctx, args, query)
