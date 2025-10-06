"""
Pytest configuration for API tests.

This file sets up the test environment, including database initialization.
"""

import asyncio
import os
import pytest
import pytest_asyncio


# Set test environment variables before importing the app
os.environ.setdefault(
    "DATABASE_URL", "postgresql://postgres:password@localhost:5432/game"
)
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-for-testing-only")
os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("RATE_LIMIT_ENABLED", "false")


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session", autouse=True)
async def initialize_database():
    """
    Initialize database connection pool for all tests.

    This fixture runs once per test session and sets up the database pool.
    """
    # Import here to ensure environment variables are set first
    from utils.database import db

    # Initialize database connection pool
    try:
        await db.connect()
        yield
    except Exception as e:
        print(f"Warning: Could not connect to database: {e}")
        yield
    finally:
        # Clean up database connection pool
        try:
            await db.disconnect()
        except Exception:
            pass
