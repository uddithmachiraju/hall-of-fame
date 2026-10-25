import time
from functools import lru_cache

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from src.config.logging import get_logger
from src.config.settings import get_settings

settings = get_settings()
logger = get_logger(__name__)


@lru_cache
def get_mongo_client() -> AsyncIOMotorClient:
    """Get a cached instance of the MongoDb client."""

    return AsyncIOMotorClient(
        settings.MONGO_URI,
        appname=settings.APP_NAME,
        tz_aware=True,
        minPoolSize=10,
        maxPoolSize=100,
        connectTimeoutMS=5000,
        serverSelectionTimeoutMS=5000,
        waitQueueTimeoutMS=5000,
    )


async def get_db() -> AsyncIOMotorDatabase:
    """Get the MongoDB database instance."""

    return get_mongo_client().get_default_database()


async def close_db() -> None:
    """Close the MongoDB client connection."""
    get_mongo_client().close()
    logger.info("MongoDB client connection closed.", database=get_mongo_client().get_default_database().name)


async def check_db_health() -> bool:
    """Check the health of the MongoDB connection."""

    for attempt in range(1, 3):
        start = time.monotonic()
        try:
            await get_mongo_client().admin.command("ping")
            latency_ms = (round(time.monotonic() - start) * 1000, 2)
            logger.info(
                "db_health_check_passed",
                latency=latency_ms,
                attempt=attempt,
                database=get_mongo_client().get_default_database().name,
            )
            return True
        except Exception as e:
            latency_ms = (round(time.monotonic() - start) * 1000, 2)
            logger.warning(
                "db_health_check_attempt_failed",
                error=str(e),
                latency=latency_ms,
                attempt=attempt,
                database=get_mongo_client().get_default_database().name,
            )

    logger.error("db_health_check_failed", database=get_mongo_client().get_default_database().name)
    return False
