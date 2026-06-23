"""数据库兼容层：支持 PostgreSQL 和 MySQL。

根据 DATABASE_URL 自动选择合适的列类型和引擎配置。
"""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import JSON, TypeDecorator, types
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.types import TypeDecorator


def get_database_type(url: str) -> str:
    """根据 URL 判断数据库类型。"""
    if url.startswith("postgresql") or url.startswith("postgres"):
        return "postgresql"
    if url.startswith("mysql"):
        return "mysql"
    if url.startswith("sqlite"):
        return "sqlite"
    raise ValueError(f"Unsupported database URL: {url}")


class UUID(TypeDecorator):
    """跨数据库的 UUID 类型。

    PostgreSQL: 使用原生 UUID
    MySQL: 使用 CHAR(36) 存储
    """

    impl = types.String(36)
    cache_ok = True

    def __init__(self, as_uuid: bool = False):
        super().__init__()
        self.as_uuid = as_uuid

    def process_bind_param(self, value: Any, dialect: Any) -> str | None:
        if value is None:
            return None
        if isinstance(value, uuid.UUID):
            return str(value)
        return str(value)

    def process_result_value(self, value: Any, dialect: Any) -> uuid.UUID | str | None:
        if value is None:
            return None
        if self.as_uuid:
            if isinstance(value, uuid.UUID):
                return value
            return uuid.UUID(value)
        return str(value)

    def load_dialect_impl(self, dialect: Any) -> Any:
        if dialect.name == "postgresql":
            return dialect.type_descriptor(PgUUID(as_uuid=self.as_uuid))
        return dialect.type_descriptor(types.String(36))


class JSONCompat(TypeDecorator):
    """跨数据库的 JSON 类型。

    PostgreSQL: 使用 JSONB
    MySQL: 使用 JSON
    SQLite: 使用 TEXT
    """

    impl = JSON
    cache_ok = True

    def load_dialect_impl(self, dialect: Any) -> Any:
        if dialect.name == "postgresql":
            from sqlalchemy.dialects.postgresql import JSONB

            return dialect.type_descriptor(JSONB())
        elif dialect.name == "mysql":
            return dialect.type_descriptor(JSON())
        else:
            return dialect.type_descriptor(types.Text())

    def process_bind_param(self, value: Any, dialect: Any) -> Any:
        if value is None:
            return None
        if dialect.name == "sqlite":
            import json

            return json.dumps(value)
        return value

    def process_result_value(self, value: Any, dialect: Any) -> Any:
        if value is None:
            return None
        if dialect.name == "sqlite" and isinstance(value, str):
            import json

            return json.loads(value)
        return value


def get_engine_kwargs(url: str) -> dict[str, Any]:
    """根据数据库类型返回引擎配置。"""
    db_type = get_database_type(url)

    kwargs: dict[str, Any] = {
        "pool_size": 10,
        "max_overflow": 10,
        "pool_pre_ping": True,
        "echo": False,
    }

    if db_type == "mysql":
        kwargs.update(
            {
                "pool_recycle": 3600,  # MySQL 连接回收时间
                "pool_timeout": 30,
            }
        )

    return kwargs


def get_server_default(url: str) -> Any:
    """返回数据库兼容的 server_default。"""
    from sqlalchemy import text

    db_type = get_database_type(url)
    if db_type == "mysql":
        return text("CURRENT_TIMESTAMP")
    return text("now()")
