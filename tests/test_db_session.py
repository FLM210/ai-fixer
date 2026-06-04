import pytest
from sqlalchemy import text

from app.db import dispose_engine, session_scope


@pytest.mark.asyncio
async def test_session_scope_executes_query() -> None:
    async with session_scope() as session:
        result = await session.execute(text("SELECT 1"))
        assert result.scalar_one() == 1
    await dispose_engine()


@pytest.mark.asyncio
async def test_session_scope_rollback_on_error() -> None:
    with pytest.raises(RuntimeError):
        async with session_scope() as session:
            await session.execute(text("SELECT 1"))
            raise RuntimeError("boom")
    await dispose_engine()
