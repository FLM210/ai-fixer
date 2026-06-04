from unittest.mock import AsyncMock

import pytest

from app.utils.dedup import EventDedup


@pytest.mark.asyncio
async def test_dedup_detects_duplicate() -> None:
    mock_redis = AsyncMock()
    mock_redis.set.return_value = None  # key already exists
    dedup = EventDedup(mock_redis)
    result = await dedup.is_duplicate('event_123')
    assert result is True


@pytest.mark.asyncio
async def test_dedup_allows_new_event() -> None:
    mock_redis = AsyncMock()
    mock_redis.set.return_value = True  # key set successfully
    dedup = EventDedup(mock_redis)
    result = await dedup.is_duplicate('event_456')
    assert result is False
