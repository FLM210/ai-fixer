from typing import Any, ClassVar

from app.plugins.base import PluginContext, PluginResult, PluginSpec
from app.plugins.builtin.postgres._base import PostgresPluginBase
from app.plugins.registry import global_registry, register

_QUERY = """
SELECT
    client_addr,
    state,
    sent_lsn,
    write_lsn,
    flush_lsn,
    replay_lsn,
    pg_wal_lsn_diff(sent_lsn, replay_lsn) AS replay_lag_bytes,
    pg_wal_lsn_diff(sent_lsn, flush_lsn) AS flush_lag_bytes
FROM pg_stat_replication;
"""

_IS_REPLICA_QUERY = "SELECT pg_is_in_recovery() AS is_replica;"

_REPLICA_LAG_QUERY = """
SELECT
    CASE WHEN pg_is_in_recovery()
        THEN EXTRACT(EPOCH FROM now() - pg_last_xact_replay_timestamp())
        ELSE NULL
    END AS replica_lag_seconds;
"""


@register(global_registry)
class PgReplicationLag(PostgresPluginBase):
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
            name="pg.replication_lag",
            category="diagnostic",
            resource_type="database",
            description="查询复制延迟：主库查各 standby 的 replay/flush 延迟字节数，备库查 replay 延迟秒数",
            risk_level="low",
            timeout_seconds=10,
            input_schema=self._SCHEMA,
        )

    async def execute(self, ctx: PluginContext, args: dict[str, Any]) -> PluginResult:
        if ctx.dry_run:
            return PluginResult(ok=True, output={"dry_run": True})

        dsn = args.get("dsn")
        try:
            conn = await self._get_connection(dsn)
            try:
                is_replica = await conn.fetchval("SELECT pg_is_in_recovery()")
                if is_replica:
                    lag = await conn.fetchval(_REPLICA_LAG_QUERY)
                    return PluginResult(ok=True, output={"role": "replica", "lag_seconds": lag})
                else:
                    rows = await conn.fetch(_QUERY)
                    return PluginResult(ok=True, output={
                        "role": "primary",
                        "replicas": [dict(r) for r in rows],
                    })
            finally:
                await conn.close()
        except Exception as e:
            return PluginResult(ok=False, output={}, error=f"pg.replication_lag failed: {e}")
