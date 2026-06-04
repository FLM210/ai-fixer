from typing import Any, ClassVar

from app.plugins.base import PluginContext, PluginResult, PluginSpec
from app.plugins.builtin.postgres._base import PostgresPluginBase
from app.plugins.registry import global_registry, register


@register(global_registry)
class PgVacuumTable(PostgresPluginBase):
    _SCHEMA: ClassVar[dict[str, Any]] = {
        "type": "object",
        "properties": {
            "dsn": {"type": "string", "description": "PostgreSQL DSN（可选）"},
            "table_name": {"type": "string", "minLength": 1, "description": "要 vacuum 的表名（schema.table 格式）"},
            "full": {"type": "boolean", "default": False, "description": "是否执行 VACUUM FULL（会锁表）"},
        },
        "required": ["table_name"],
        "additionalProperties": False,
    }

    @property
    def spec(self) -> PluginSpec:
        return PluginSpec(
            name="pg.vacuum_table",
            category="remediation",
            resource_type="database",
            description="对指定表执行 VACUMM 回收死行空间。默认 VACUUM（不锁表），可选 VACUUM FULL（锁表但回收更多空间）",
            risk_level="medium",
            requires_approval=False,
            blast_radius="单张表，VACUUM FULL 期间该表不可写",
            timeout_seconds=300,
            input_schema=self._SCHEMA,
        )

    async def execute(self, ctx: PluginContext, args: dict[str, Any]) -> PluginResult:
        if ctx.dry_run:
            return PluginResult(ok=True, output={"dry_run": True, "table": args["table_name"]})

        dsn = args.get("dsn")
        table = args["table_name"]
        full = args.get("full", False)

        # 安全检查：防止 SQL 注入
        if not all(c.isalnum() or c in "._" for c in table):
            return PluginResult(ok=False, output={}, error=f"无效的表名: {table}")

        vacuum_sql = f"VACUUM {'FULL ' if full else ''}{table}"

        try:
            conn = await self._get_connection(dsn)
            try:
                await conn.execute(vacuum_sql)
                return PluginResult(ok=True, output={"table": table, "full": full, "executed": True})
            finally:
                await conn.close()
        except Exception as e:
            return PluginResult(ok=False, output={}, error=f"pg.vacuum_table failed: {e}")
