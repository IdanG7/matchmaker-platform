"""
Integration tests for profile endpoints.

These tests validate profile management against the actual API.
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
async def authenticated_user(client):
    """Create and authenticate a test user, return tokens and user data."""
    import uuid

    unique_id = str(uuid.uuid4())[:8]
    user_data = {
        "username": f"testuser_{unique_id}",
        "email": f"test_{unique_id}@example.com",
        "password": "SecurePassword123!",
        "region": "us-west",
    }

    response = await client.post("/v1/auth/register", json=user_data)
    assert response.status_code == status.HTTP_201_CREATED

    auth_data = response.json()
    return {
        "user_data": user_data,
        "auth_data": auth_data,
        "access_token": auth_data["access_token"],
        "refresh_token": auth_data["refresh_token"],
    }


@pytest.mark.asyncio
async def test_get_profile_authenticated(client, authenticated_user):
    """Test getting profile with valid authentication."""
    headers = {"Authorization": f"Bearer {authenticated_user['access_token']}"}

    response = await client.get("/v1/profile/me", headers=headers)
    assert response.status_code == status.HTTP_200_OK

    data = response.json()
    assert "player_id" in data
    assert "username" in data
    assert "email" in data
    assert "region" in data
    assert "mmr" in data
    assert "created_at" in data

    # Verify data matches registered user
    assert data["username"] == authenticated_user["user_data"]["username"]
    assert data["email"] == authenticated_user["user_data"]["email"]
    assert data["region"] == authenticated_user["user_data"]["region"]


@pytest.mark.asyncio
async def test_get_profile_unauthenticated(client):
    """Test getting profile without authentication fails."""
    response = await client.get("/v1/profile/me")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.asyncio
async def test_get_profile_invalid_token(client):
    """Test getting profile with invalid token fails."""
    headers = {"Authorization": "Bearer invalid_token"}

    response = await client.get("/v1/profile/me", headers=headers)
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.asyncio
async def test_update_profile_region(client, authenticated_user):
    """Test updating profile region."""
    headers = {"Authorization": f"Bearer {authenticated_user['access_token']}"}

    # Update region
    update_data = {"region": "eu-west"}

    response = await client.patch("/v1/profile/me", json=update_data, headers=headers)
    assert response.status_code == status.HTTP_200_OK

    data = response.json()
    assert data["region"] == "eu-west"

    # Verify username and email remain unchanged
    assert data["username"] == authenticated_user["user_data"]["username"]
    assert data["email"] == authenticated_user["user_data"]["email"]


@pytest.mark.asyncio
async def test_update_profile_no_changes(client, authenticated_user):
    """Test updating profile with no fields returns current profile."""
    headers = {"Authorization": f"Bearer {authenticated_user['access_token']}"}

    # Send empty update
    update_data = {}

    response = await client.patch("/v1/profile/me", json=update_data, headers=headers)
    assert response.status_code == status.HTTP_200_OK

    data = response.json()
    # Should return current profile unchanged
    assert data["username"] == authenticated_user["user_data"]["username"]
    assert data["region"] == authenticated_user["user_data"]["region"]


@pytest.mark.asyncio
async def test_update_profile_unauthenticated(client):
    """Test updating profile without authentication fails."""
    update_data = {"region": "eu-west"}

    response = await client.patch("/v1/profile/me", json=update_data)
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.asyncio
async def test_update_profile_invalid_token(client):
    """Test updating profile with invalid token fails."""
    headers = {"Authorization": "Bearer invalid_token"}
    update_data = {"region": "eu-west"}

    response = await client.patch("/v1/profile/me", json=update_data, headers=headers)
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.asyncio
async def test_full_auth_profile_flow(client):
    """Test complete flow: register -> login -> get profile -> update profile."""
    import uuid

    unique_id = str(uuid.uuid4())[:8]

    # 1. Register
    register_data = {
        "username": f"flowtest_{unique_id}",
        "email": f"flowtest_{unique_id}@example.com",
        "password": "TestPassword123!",
        "region": "us-east",
    }

    register_response = await client.post("/v1/auth/register", json=register_data)
    assert register_response.status_code == status.HTTP_201_CREATED
    register_result = register_response.json()

    # 2. Login
    login_data = {
        "username": register_data["username"],
        "password": register_data["password"],
    }

    login_response = await client.post("/v1/auth/login", json=login_data)
    assert login_response.status_code == status.HTTP_200_OK
    login_result = login_response.json()

    # Tokens should be different from registration
    assert login_result["access_token"] != register_result["access_token"]

    # 3. Get profile
    headers = {"Authorization": f"Bearer {login_result['access_token']}"}
    profile_response = await client.get("/v1/profile/me", headers=headers)
    assert profile_response.status_code == status.HTTP_200_OK
    profile = profile_response.json()

    assert profile["username"] == register_data["username"]
    assert profile["region"] == "us-east"

    # 4. Update profile
    update_response = await client.patch(
        "/v1/profile/me", json={"region": "ap-southeast"}, headers=headers
    )
    assert update_response.status_code == status.HTTP_200_OK
    updated_profile = update_response.json()

    assert updated_profile["region"] == "ap-southeast"
    assert updated_profile["username"] == register_data["username"]

    # 5. Verify profile was updated
    verify_response = await client.get("/v1/profile/me", headers=headers)
    assert verify_response.status_code == status.HTTP_200_OK
    final_profile = verify_response.json()

    assert final_profile["region"] == "ap-southeast"
