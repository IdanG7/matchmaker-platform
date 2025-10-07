"""
Pytest configuration for API tests.

This file sets up the test environment, including database initialization.
"""

import asyncio
import os
import uuid
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport


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


@pytest_asyncio.fixture
async def async_client():
    """Create test HTTP client."""
    from main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture(scope="function")
def test_user_data():
    """Generate unique test user data (fresh for each test)."""
    unique_id = str(uuid.uuid4())[:8]
    return {
        "username": f"testuser_{unique_id}",
        "email": f"test_{unique_id}@example.com",
        "password": "SecurePassword123!",
        "region": "us-west",
    }


@pytest.fixture(scope="function")
def second_test_user_data():
    """Generate second unique test user data (fresh for each test)."""
    unique_id = str(uuid.uuid4())[:8]
    return {
        "username": f"testuser2_{unique_id}",
        "email": f"test2_{unique_id}@example.com",
        "password": "SecurePassword456!",
        "region": "us-east",
    }


@pytest_asyncio.fixture(scope="function")
async def tokens(async_client, test_user_data):
    """Register a user and return their auth tokens (fresh for each test)."""
    response = await async_client.post("/v1/auth/register", json=test_user_data)
    assert response.status_code == 201
    return response.json()


@pytest_asyncio.fixture(scope="function")
async def second_user_tokens(async_client, second_test_user_data):
    """Register a second user and return their auth tokens (fresh for each test)."""
    response = await async_client.post("/v1/auth/register", json=second_test_user_data)
    assert response.status_code == 201
    return response.json()
