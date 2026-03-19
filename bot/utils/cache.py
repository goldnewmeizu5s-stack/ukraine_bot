import hashlib
import logging
from collections import OrderedDict
from typing import Optional

logger = logging.getLogger(__name__)

CACHE_TTL = 7 * 24 * 60 * 60


class InMemoryCache:
    def __init__(self, maxsize: int = 500):
        self._cache: OrderedDict[str, bytes] = OrderedDict()
        self._maxsize = maxsize

    def _make_key(self, text: str) -> str:
        return hashlib.sha256(text.encode()).hexdigest()

    async def get(self, text: str) -> Optional[bytes]:
        key = self._make_key(text)
        if key in self._cache:
            self._cache.move_to_end(key)
            return self._cache[key]
        return None

    async def set(self, text: str, data: bytes) -> None:
        key = self._make_key(text)
        if key in self._cache:
            self._cache.move_to_end(key)
        else:
            if len(self._cache) >= self._maxsize:
                self._cache.popitem(last=False)
        self._cache[key] = data


class RedisCache:
    def __init__(self, redis_client):
        self._redis = redis_client

    def _make_key(self, text: str) -> str:
        return f"tts:{hashlib.sha256(text.encode()).hexdigest()}"

    async def get(self, text: str) -> Optional[bytes]:
        try:
            return await self._redis.get(self._make_key(text))
        except Exception as e:
            logger.warning("Redis get failed: %s", e)
            return None

    async def set(self, text: str, data: bytes) -> None:
        try:
            await self._redis.set(self._make_key(text), data, ex=CACHE_TTL)
        except Exception as e:
            logger.warning("Redis set failed: %s", e)


async def create_cache() -> InMemoryCache | RedisCache:
    from bot.config import settings
    if settings.REDIS_URL:
        try:
            import redis.asyncio as aioredis
            redis_client = aioredis.from_url(settings.REDIS_URL)
            await redis_client.ping()
            logger.info("Using Redis cache")
            return RedisCache(redis_client)
        except Exception as e:
            logger.warning("Redis unavailable, falling back to in-memory cache: %s", e)
    logger.info("Using in-memory cache")
    return InMemoryCache()


audio_cache = InMemoryCache()


async def init_cache() -> None:
    global audio_cache
    audio_cache = await create_cache()
