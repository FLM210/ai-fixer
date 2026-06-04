from sqlalchemy import MetaData
from sqlalchemy.orm import DeclarativeBase

NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


def get_schema_name() -> str | None:
    """返回 schema 名称，MySQL/SQLite 返回 None。"""
    from app.config import get_settings
    from app.db.compat import get_database_type

    try:
        settings = get_settings()
        db_type = get_database_type(settings.database_url)
        if db_type == "postgresql":
            return "fixer"
        return None
    except Exception:
        return None


def get_table_args(*extra_args: dict) -> tuple[dict, ...]:
    """返回表参数，自动包含 schema（如果需要）。"""
    schema = get_schema_name()
    args = {}
    if schema:
        args["schema"] = schema
    args.update(extra_args[0] if extra_args else {})
    return (args,) if args else ()


def _get_metadata() -> MetaData:
    """根据数据库类型返回合适的 MetaData。"""
    schema = get_schema_name()
    if schema:
        return MetaData(naming_convention=NAMING_CONVENTION, schema=schema)
    return MetaData(naming_convention=NAMING_CONVENTION)


class Base(DeclarativeBase):
    metadata = _get_metadata()
