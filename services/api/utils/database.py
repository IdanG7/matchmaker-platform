"""
Database connection and query utilities.
"""

import asyncpg
import json
from typing import Optional
from contextlib import asynccontextmanager

from config import get_settings

settings = get_settings()


def _json_encoder(value):
    """
    Serialise a json/jsonb parameter.

    Callers pass either a dict or a string they serialised themselves, so
    already-encoded values are passed through rather than double-encoded.
    """
    return value if isinstance(value, str) else json.dumps(value)


async def _init_connection(conn):
    """
    Decode json and jsonb columns into Python objects.

    Without this asyncpg hands back the raw string, so reading a metadata or
    result column and calling .get() on it raises
    "'str' object has no attribute 'get'" at runtime.
    """
    for type_name in ("json", "jsonb"):
        await conn.set_type_codec(
            type_name,
            encoder=_json_encoder,
            decoder=json.loads,
            schema="pg_catalog",
        )


class Database:
    """Database connection manager."""

    def __init__(self):
        self.pool: Optional[asyncpg.Pool] = None

    async def connect(self):
        """Create database connection pool."""
        self.pool = await asyncpg.create_pool(
            settings.database_url,
            min_size=5,
            max_size=20,
            command_timeout=60,
            init=_init_connection,
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
