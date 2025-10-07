"""
Database connection and query utilities.
"""

import asyncpg
from typing import Optional
from contextlib import asynccontextmanager

from config import get_settings

settings = get_settings()


class Database:
    """Database connection manager."""

    def __init__(self):
        self.pool: Optional[asyncpg.Pool] = None

    async def connect(self):
        """Create database connection pool."""
        self.pool = await asyncpg.create_pool(
            settings.database_url, min_size=5, max_size=20, command_timeout=60
        )

    async def disconnect(self):
        """Close database connection pool."""
        if self.pool:
            await self.pool.close()

    @asynccontextmanager
    async def acquire(self):
        """Acquire a connection from the pool."""
        async with self.pool.acquire() as connection:
            yield connection


# Global database instance
db = Database()


async def get_db_connection():
    """Dependency for getting database connection."""
    async with db.acquire() as conn:
        yield conn


async def get_db_pool():
    """Get the database connection pool."""
    return db.pool
