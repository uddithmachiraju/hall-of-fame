from dataclasses import dataclass, field

from redis.asyncio import Redis

from src.core.redis import get_redis_client


@dataclass
class AppComponents:
    """A single container for all the components of the application."""

    redis_service: Redis | None = field(default=None)

    async def initialize(self):
        """Initialize all components of the application."""
        # Initialize Redis service
        self.redis_service = await get_redis_client()

    @property
    def redis(self) -> Redis:
        """Get the Redis service instance."""
        if self.redis_service is None:
            raise RuntimeError("Redis service is not initialized.")
        return self.redis_service


container = AppComponents()


def get_redis_service() -> Redis:
    """Get the Redis service instance."""
    if container.redis_service is None:
        raise RuntimeError("Redis service is not initialized.")
    return container.redis
