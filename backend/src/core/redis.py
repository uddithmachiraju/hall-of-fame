from redis.asyncio import ConnectionPool, Redis

from src.config.logging import get_logger
from src.config.settings import settings

logger = get_logger(__name__)

pool = ConnectionPool.from_url(
    settings.REDIS_URL,
    encoding="utf-8",
    max_connections=settings.REDIS_MAX_CONNECTIONS,
    decode_responses=True,
    socket_connect_timeout=settings.REDIS_SOCKET_CONNECT_TIMEOUT,
    socket_timeout=settings.REDIS_SOCKET_TIMEOUT,
    health_check_interval=settings.REDIS_HEALTH_CHECK_INTERVAL,
    retry_on_timeout=settings.REDIS_RETRY_ON_TIMEOUT,
)

redis_client = Redis(connection_pool=pool)


async def get_redis_client() -> Redis:
    """Get Redis client instance."""

    return redis_client


async def close_redis_client() -> None:
    """Close Redis client connection."""

    await redis_client.close()
    await pool.disconnect()
    logger.info("redis_connection_closed.", redis_url=settings.REDIS_URL)


async def check_redis_health() -> bool:
    """Check the health of the Redis connection."""

    try:
        pong = await redis_client.ping()
        if pong:
            logger.info("Redis_connection_healthy.", redis_url=settings.REDIS_URL)
            return True
        else:
            logger.error("Redis_connection_unhealthy.", redis_url=settings.REDIS_URL)
            return False
    except Exception:
        logger.error("Redis_connection_unhealthy.", redis_url=settings.REDIS_URL)
        return False
