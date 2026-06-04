import redis.asyncio as redis


class DistributedLock:
    def __init__(self, redis_client: redis.Redis) -> None:
        self.redis = redis_client

    async def acquire(self, key: str, ttl_seconds: int = 30) -> bool:
        result: bool = await self.redis.set(key, '1', nx=True, ex=ttl_seconds)
        return result

    async def release(self, key: str) -> None:
        await self.redis.delete(key)
