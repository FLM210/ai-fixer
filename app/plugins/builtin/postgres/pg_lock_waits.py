from typing import Any, ClassVar

from app.plugins.base import PluginContext, PluginResult, PluginSpec
from app.plugins.builtin.postgres._base import PostgresPluginBase
from app.plugins.registry import global_registry, register

_QUERY = """
SELECT
    blocked_locks.pid AS blocked_pid,
    blocked_activity.usename AS blocked_user,
    blocking_locks.pid AS blocking_pid,
    blocking_activity.usename AS blocking_user,
    blocked_activity.query AS blocked_query,
    blocking_activity.query AS blocking_query,
    now() - blocked_activity.query_start AS blocked_duration
FROM pg_catalog.pg_locks blocked_locks
JOIN pg_catalog.pg_stat_activity blocked_activity ON blocked_activity.pid = blocked_locks.pid
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
JOIN pg_catalog.pg_stat_activity blocking_activity ON blocking_activity.pid = blocking_locks.pid
WHERE NOT blocked_locks.granted
LIMIT 20;
"""


@register(global_registry)
class PgLockWaits(PostgresPluginBase):
    _SCHEMA: ClassVar[dict[str, Any]] = {
        "type": "object",
        "properties": {
            "dsn": {"type": "string", "description": "PostgreSQL DSN（可选）"},
        },
        "additionalProperties": False,
    }

    @property
    def spec(self) -> PluginSpec:
        return PluginSpec(
            name="pg.lock_waits",
            category="diagnostic",
            resource_type="database",
            description="查询锁等待链：哪些会话被阻塞、被谁阻塞、阻塞了多久、执行的 SQL 是什么",
            risk_level="low",
            timeout_seconds=10,
            input_schema=self._SCHEMA,
        )

    async def execute(self, ctx: PluginContext, args: dict[str, Any]) -> PluginResult:
        return await self._execute_query(ctx, args, _QUERY)
