from unittest.mock import AsyncMock

import pytest

from app.utils.lock import DistributedLock


@pytest.mark.asyncio
async def test_lock_acquires_and_releases() -> None:
    mock_redis = AsyncMock()
    mock_redis.set.return_value = True
    lock = DistributedLock(mock_redis)
    result = await lock.acquire('lock:test', ttl_seconds=30)
    assert result is True
    await lock.release('lock:test')
    mock_redis.delete.assert_called_once()


@pytest.mark.asyncio
async def test_lock_acquire_fails_when_exists() -> None:
    mock_redis = AsyncMock()
    mock_redis.set.return_value = None  # key already exists
    lock = DistributedLock(mock_redis)
    result = await lock.acquire('lock:test')
    assert result is None
