"""FastAPI 依赖注入。"""

from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_dynamic_config, get_settings
from app.config.dynamic import DynamicConfig
from app.config.settings import Settings
from app.db import session_scope


async def get_db_session() -> AsyncIterator[AsyncSession]:
    """提供数据库 session 的依赖。"""
    async with session_scope() as session:
        yield session


def get_config() -> Settings:
    """获取 Settings 配置。"""
    return get_settings()


def get_dynamic() -> DynamicConfig:
    """获取 DynamicConfig 实例。"""
    return get_dynamic_config()
