from typing import Optional
import redis.asyncio as aioredis
from backend.core.config import settings
from backend.core.logger import logger

_redis_client: Optional[aioredis.Redis] = None
_is_mock: bool = False


async def connect_to_redis() -> aioredis.Redis:
    global _redis_client, _is_mock
    if settings.USE_MOCK_DB or settings.ENVIRONMENT == "test":
        import fakeredis.aioredis as fakeredis_aioredis
        _redis_client = fakeredis_aioredis.FakeRedis(decode_responses=True)
        _is_mock = True
        logger.info("Using in-memory FakeRedis for test environment")
        return _redis_client

    try:
        client = aioredis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True,
            socket_connect_timeout=2.0
        )
        await client.ping()
        _redis_client = client
        _is_mock = False
        logger.info(f"Connected to live Redis at {settings.REDIS_URL}")
    except Exception as e:
        logger.warning(f"Could not connect to live Redis ({e}). Initializing in-memory FakeRedis...")
        try:
            import fakeredis.aioredis as fakeredis_aioredis
            _redis_client = fakeredis_aioredis.FakeRedis(decode_responses=True)
            _is_mock = True
            logger.info("In-memory FakeRedis initialized successfully")
        except Exception as mock_err:
            logger.error(f"Failed to initialize FakeRedis: {mock_err}")
            raise e
    return _redis_client


async def close_redis_connection():
    global _redis_client
    if _redis_client:
        await _redis_client.close()
        logger.info("Redis connection closed")


def get_redis() -> aioredis.Redis:
    global _redis_client
    if _redis_client is None:
        raise RuntimeError("Redis is not initialized. Call connect_to_redis() first.")
    return _redis_client


def is_redis_mock() -> bool:
    return _is_mock


async def acquire_distributed_lock(key: str, timeout_seconds: int = 10) -> bool:
    """Acquire atomic distributed lock using SET NX PX."""
    r = get_redis()
    acquired = await r.set(f"lock:{key}", "locked", nx=True, ex=timeout_seconds)
    return bool(acquired)


async def release_distributed_lock(key: str):
    """Release distributed lock."""
    r = get_redis()
    await r.delete(f"lock:{key}")
