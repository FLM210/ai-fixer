"""Postgres 插件基类：管理外部 PostgreSQL 实例连接。"""

from __future__ import annotations

from typing import Any

import asyncpg

from app.config import get_settings
from app.plugins.base import Plugin, PluginContext, PluginResult


class PostgresPluginBase(Plugin):
    """Postgres 插件基类，提供连接管理。"""

    async def _get_connection(self, dsn: str | None = None) -> asyncpg.Connection:
        """获取 PostgreSQL 连接。优先使用传入的 DSN，否则使用配置中的 DSN。"""
        target_dsn = dsn or get_settings().pg_monitor.dsn
        if not target_dsn:
            raise ValueError("未配置 PostgreSQL DSN，请设置 PG_MONITOR_DSN 环境变量或传入 dsn 参数")
        return await asyncpg.connect(target_dsn)

    async def _execute_query(
        self, ctx: PluginContext, args: dict[str, Any], query: str
    ) -> PluginResult:
        """执行查询的通用方法。"""
        if ctx.dry_run:
            return PluginResult(ok=True, output={"dry_run": True, "query": query})

        dsn = args.get("dsn")
        try:
            conn = await self._get_connection(dsn)
            try:
                rows = await conn.fetch(query)
                output = [dict(row) for row in rows]
                return PluginResult(ok=True, output={"rows": output, "count": len(output)})
            finally:
                await conn.close()
        except Exception as e:
            return PluginResult(ok=False, output={}, error=f"{self.spec.name} failed: {e}")
