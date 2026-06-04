import redis.asyncio as redis


class EventDedup:
    def __init__(self, redis_client: redis.Redis) -> None:
        self.redis = redis_client

    async def is_duplicate(self, event_id: str, ttl_seconds: int = 300) -> bool:
        key = f'dedup:event:{event_id}'
        result = await self.redis.set(key, '1', nx=True, ex=ttl_seconds)
        return result is None
