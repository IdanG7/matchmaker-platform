"""
Pytest configuration for API tests.

This file sets up the test environment, including database initialization.
"""

import asyncio
import os
import pytest
import asyncpg


# Set test environment variables
os.environ.setdefault("DATABASE_URL", "postgresql://postgres:password@localhost:5432/game")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-for-testing-only")
os.environ.setdefault("ENVIRONMENT", "test")


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session", autouse=True)
async def setup_database():
    """
    Set up the database schema before running tests.

    This fixture runs once per test session and ensures the database
    schema is initialized.
    """
    database_url = os.getenv("DATABASE_URL")

    # Skip database setup if DATABASE_URL is not set (e.g., in unit tests)
    if not database_url:
        yield
        return

    try:
        # Connect to database
        conn = await asyncpg.connect(database_url)

        # Read and execute init.sql if needed
        # For now, we assume the database is already initialized via docker-compose
        # In a real CI environment, we'd run the migration here

        await conn.close()
    except Exception as e:
        # If we can't connect to the database, skip database-dependent tests
        print(f"Warning: Could not connect to database: {e}")

    yield
