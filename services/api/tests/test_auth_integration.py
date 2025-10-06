"""
Integration tests for authentication endpoints.

These tests validate the entire auth flow against the actual API.
"""

import pytest
from httpx import AsyncClient, ASGITransport
from fastapi import status

# Import the FastAPI app
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from main import app


@pytest.fixture
async def client():
    """Create test client."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
def test_user_data():
    """Sample user data for testing."""
    import uuid

    unique_id = str(uuid.uuid4())[:8]
    return {
        "username": f"testuser_{unique_id}",
        "email": f"test_{unique_id}@example.com",
        "password": "SecurePassword123!",
        "region": "us-west",
    }


@pytest.mark.asyncio
async def test_register_new_user(client, test_user_data):
    """Test user registration with valid data."""
    response = await client.post("/v1/auth/register", json=test_user_data)

    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()

    # Verify response structure
    assert "player_id" in data
    assert "username" in data
    assert "email" in data
    assert "access_token" in data
    assert "refresh_token" in data
    assert "token_type" in data
    assert "expires_in" in data

    # Verify data matches request
    assert data["username"] == test_user_data["username"]
    assert data["email"] == test_user_data["email"]
    assert data["token_type"] == "bearer"
    assert len(data["access_token"]) > 0
    assert len(data["refresh_token"]) > 0


@pytest.mark.asyncio
async def test_register_duplicate_username(client, test_user_data):
    """Test that registering duplicate username fails."""
    # Register first time
    response1 = await client.post("/v1/auth/register", json=test_user_data)
    assert response1.status_code == status.HTTP_201_CREATED

    # Try to register again with same username but different email
    duplicate_data = test_user_data.copy()
    duplicate_data["email"] = "different@example.com"

    response2 = await client.post("/v1/auth/register", json=duplicate_data)
    assert response2.status_code == status.HTTP_400_BAD_REQUEST
    assert "username" in response2.json()["detail"].lower()


@pytest.mark.asyncio
async def test_register_duplicate_email(client, test_user_data):
    """Test that registering duplicate email fails."""
    # Register first time
    response1 = await client.post("/v1/auth/register", json=test_user_data)
    assert response1.status_code == status.HTTP_201_CREATED

    # Try to register again with same email but different username
    duplicate_data = test_user_data.copy()
    duplicate_data["username"] = "different_username"

    response2 = await client.post("/v1/auth/register", json=duplicate_data)
    assert response2.status_code == status.HTTP_400_BAD_REQUEST
    assert "email" in response2.json()["detail"].lower()


@pytest.mark.asyncio
async def test_login_valid_credentials(client, test_user_data):
    """Test login with valid credentials."""
    # First register a user
    await client.post("/v1/auth/register", json=test_user_data)

    # Now try to login
    login_data = {
        "username": test_user_data["username"],
        "password": test_user_data["password"],
    }

    response = await client.post("/v1/auth/login", json=login_data)
    assert response.status_code == status.HTTP_200_OK

    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["username"] == test_user_data["username"]


@pytest.mark.asyncio
async def test_login_invalid_password(client, test_user_data):
    """Test login with invalid password."""
    # First register a user
    await client.post("/v1/auth/register", json=test_user_data)

    # Try to login with wrong password
    login_data = {
        "username": test_user_data["username"],
        "password": "WrongPassword123!",
    }

    response = await client.post("/v1/auth/login", json=login_data)
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.asyncio
async def test_login_nonexistent_user(client):
    """Test login with non-existent username."""
    login_data = {"username": "nonexistent_user", "password": "SomePassword123!"}

    response = await client.post("/v1/auth/login", json=login_data)
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.asyncio
async def test_refresh_token_flow(client, test_user_data):
    """Test refresh token functionality."""
    # Register and get tokens
    register_response = await client.post("/v1/auth/register", json=test_user_data)
    assert register_response.status_code == status.HTTP_201_CREATED

    tokens = register_response.json()
    refresh_token = tokens["refresh_token"]

    # Use refresh token to get new access token
    refresh_data = {"refresh_token": refresh_token}

    response = await client.post("/v1/auth/refresh", json=refresh_data)
    assert response.status_code == status.HTTP_200_OK

    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"

    # New tokens should be different from original
    assert data["access_token"] != tokens["access_token"]
    assert data["refresh_token"] != tokens["refresh_token"]


@pytest.mark.asyncio
async def test_refresh_invalid_token(client):
    """Test refresh with invalid token."""
    refresh_data = {"refresh_token": "invalid_token"}

    response = await client.post("/v1/auth/refresh", json=refresh_data)
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.asyncio
async def test_refresh_with_access_token(client, test_user_data):
    """Test that using access token for refresh fails."""
    # Register and get tokens
    register_response = await client.post("/v1/auth/register", json=test_user_data)
    tokens = register_response.json()

    # Try to use access token instead of refresh token
    refresh_data = {"refresh_token": tokens["access_token"]}

    response = await client.post("/v1/auth/refresh", json=refresh_data)
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
