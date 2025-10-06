"""Redis connection pool and helper utilities."""

import os
import logging
from typing import Optional
from redis import Redis, ConnectionPool
from redis.exceptions import RedisError

logger = logging.getLogger(__name__)


class RedisClient:
    """Redis client wrapper with connection pooling."""

    def __init__(self, url: Optional[str] = None):
        """
        Initialize Redis client.

        Args:
            url: Redis connection URL (default: from REDIS_URL env var)
        """
        self.url = url or os.getenv("REDIS_URL", "redis://localhost:6379/0")
        self._pool: Optional[ConnectionPool] = None
        self._client: Optional[Redis] = None

    def connect(self) -> Redis:
        """
        Create connection pool and return Redis client.

        Returns:
            Redis client instance
        """
        if self._client is None:
            try:
                self._pool = ConnectionPool.from_url(
                    self.url,
                    max_connections=50,
                    decode_responses=True,
                    socket_timeout=5,
                    socket_connect_timeout=5,
                )
                self._client = Redis(connection_pool=self._pool)

                # Test connection
                self._client.ping()
                logger.info(f"Connected to Redis at {self.url}")
            except RedisError as e:
                logger.error(f"Failed to connect to Redis: {e}")
                raise

        return self._client

    def disconnect(self):
        """Close Redis connection pool."""
        if self._client:
            self._client.close()
            self._client = None
        if self._pool:
            self._pool.disconnect()
            self._pool = None
        logger.info("Disconnected from Redis")

    def health_check(self) -> bool:
        """
        Check if Redis is healthy.

        Returns:
            True if Redis responds to PING, False otherwise
        """
        try:
            if self._client:
                self._client.ping()
                return True
        except RedisError as e:
            logger.error(f"Redis health check failed: {e}")
        return False

    @property
    def client(self) -> Redis:
        """Get Redis client, creating connection if needed."""
        if self._client is None:
            self.connect()
        return self._client


# Global Redis client instance
_redis_client: Optional[RedisClient] = None


def get_redis() -> Redis:
    """
    Get global Redis client instance.

    Returns:
        Redis client
    """
    global _redis_client
    if _redis_client is None:
        _redis_client = RedisClient()
        _redis_client.connect()
    return _redis_client.client


def close_redis():
    """Close global Redis connection."""
    global _redis_client
    if _redis_client:
        _redis_client.disconnect()
        _redis_client = None
