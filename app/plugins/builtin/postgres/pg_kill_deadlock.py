from typing import Any, ClassVar

from app.plugins.base import PluginContext, PluginResult, PluginSpec
from app.plugins.builtin.postgres._base import PostgresPluginBase
from app.plugins.registry import global_registry, register

_FIND_DEADLOCKS = """
SELECT
    blocked_locks.pid AS blocked_pid,
    blocking_locks.pid AS blocking_pid
FROM pg_catalog.pg_locks blocked_locks
JOIN pg_catalog.pg_locks blocking_locks
    ON blocking_locks.locktype = blocked_locks.locktype
    AND blocking_locks.database IS NOT DISTINCT FROM blocked_locks.database
    AND blocking_locks.relation IS NOT DISTINCT FROM blocked_locks.relation
    AND blocking_locks.page IS NOT DISTINCT FROM blocked_locks.page
    AND blocking_locks.tuple IS NOT DISTINCT FROM blocked_locks.tuple
    AND blocking_locks.virtualxid IS NOT DISTINCT FROM blocked_locks.virtualxid
    AND blocking_locks.transactionid IS NOT DISTINCT FROM blocked_locks.transactionid
    AND blocking_locks.classid IS NOT DISTINCT FROM blocked_locks.classid
    AND blocking_locks.objid IS NOT DISTINCT FROM blocked_locks.objid
    AND blocking_locks.objsubid IS NOT DISTINCT FROM blocked_locks.objsubid
    AND blocking_locks.pid != blocked_locks.pid
WHERE NOT blocked_locks.granted;
"""


@register(global_registry)
class PgKillDeadlock(PostgresPluginBase):
    _SCHEMA: ClassVar[dict[str, Any]] = {
        "type": "object",
        "properties": {
            "dsn": {"type": "string", "description": "PostgreSQL DSN（可选）"},
            "pid": {
                "type": "integer",
                "description": "要终止的阻塞者 PID。不传则自动查找并终止所有阻塞者",
            },
        },
        "additionalProperties": False,
    }

    @property
    def spec(self) -> PluginSpec:
        return PluginSpec(
            name="pg.kill_deadlock",
            category="remediation",
            resource_type="database",
            description="终止死锁阻塞者：指定 PID 或自动查找所有阻塞源头并终止",
            risk_level="high",
            requires_approval=True,
            blast_radius="阻塞链上的所有会话",
            timeout_seconds=15,
            input_schema=self._SCHEMA,
        )

    async def execute(self, ctx: PluginContext, args: dict[str, Any]) -> PluginResult:
        if ctx.dry_run:
            return PluginResult(ok=True, output={"dry_run": True})

        dsn = args.get("dsn")
        target_pid = args.get("pid")

        try:
            conn = await self._get_connection(dsn)
            try:
                if target_pid:
                    pids_to_kill = [target_pid]
                else:
                    rows = await conn.fetch(_FIND_DEADLOCKS)
                    pids_to_kill = list({r["blocking_pid"] for r in rows})

                if not pids_to_kill:
                    return PluginResult(ok=True, output={"message": "未发现死锁阻塞者", "killed": []})

                killed = []
                for pid in pids_to_kill:
                    result = await conn.fetchval("SELECT pg_terminate_backend($1)", pid)
                    if result:
                        killed.append(pid)

                return PluginResult(ok=True, output={"killed": killed, "total": len(pids_to_kill)})
            finally:
                await conn.close()
        except Exception as e:
            return PluginResult(ok=False, output={}, error=f"pg.kill_deadlock failed: {e}")
