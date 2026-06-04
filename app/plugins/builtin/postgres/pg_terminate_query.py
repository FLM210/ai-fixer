from typing import Any, ClassVar

from app.plugins.base import PluginContext, PluginResult, PluginSpec
from app.plugins.builtin.postgres._base import PostgresPluginBase
from app.plugins.registry import global_registry, register


@register(global_registry)
class PgTerminateQuery(PostgresPluginBase):
    _SCHEMA: ClassVar[dict[str, Any]] = {
        "type": "object",
        "properties": {
            "dsn": {"type": "string", "description": "PostgreSQL DSN（可选）"},
            "pid": {"type": "integer", "description": "要终止的会话 PID"},
        },
        "required": ["pid"],
        "additionalProperties": False,
    }

    @property
    def spec(self) -> PluginSpec:
        return PluginSpec(
            name="pg.terminate_query",
            category="remediation",
            resource_type="database",
            description="终止指定 PID 的查询（pg_terminate_backend），不杀连接本身",
            risk_level="medium",
            requires_approval=True,
            blast_radius="单个查询会话",
            timeout_seconds=10,
            input_schema=self._SCHEMA,
        )

    async def execute(self, ctx: PluginContext, args: dict[str, Any]) -> PluginResult:
        if ctx.dry_run:
            return PluginResult(ok=True, output={"dry_run": True, "pid": args["pid"]})

        dsn = args.get("dsn")
        pid = args["pid"]
        try:
            conn = await self._get_connection(dsn)
            try:
                result = await conn.fetchval("SELECT pg_terminate_backend($1)", pid)
                return PluginResult(
                    ok=result is True,
                    output={"pid": pid, "terminated": result is True},
                    error=None if result else f"pg_terminate_backend({pid}) returned False",
                )
            finally:
                await conn.close()
        except Exception as e:
            return PluginResult(ok=False, output={}, error=f"pg.terminate_query failed: {e}")
