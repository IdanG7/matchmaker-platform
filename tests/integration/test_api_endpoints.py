"""
Integration tests for API endpoints.

Tests the complete flow of user registration, authentication, and party creation.
"""

import pytest
import httpx
import asyncio


BASE_URL = "http://localhost:8080"


@pytest.mark.asyncio
async def test_user_registration_and_login():
    """Test user registration and login flow."""
    async with httpx.AsyncClient(base_url=BASE_URL) as client:
        # Register a new user
        register_data = {
            "email": "integration-test@example.com",
            "username": "integrationtester",
            "password": "testpassword123",
            "region": "us-west",
        }

        response = await client.post("/v1/auth/register", json=register_data)

        # Should succeed (201) or fail if already exists (400)
        assert response.status_code in [200, 201, 400]

        if response.status_code in [200, 201]:
            data = response.json()
            assert "access_token" in data
            assert "refresh_token" in data
            access_token = data["access_token"]
        else:
            # User already exists, try to login
            login_data = {
                "username": register_data["username"],
                "password": register_data["password"],
            }
            response = await client.post("/v1/auth/login", json=login_data)
            assert response.status_code == 200
            data = response.json()
            access_token = data["access_token"]

        # Test authenticated endpoint
        headers = {"Authorization": f"Bearer {access_token}"}
        response = await client.get("/v1/profile/me", headers=headers)
        assert response.status_code == 200

        profile = response.json()
        assert profile["username"] == "integrationtester"
        assert profile["region"] == "us-west"


@pytest.mark.asyncio
async def test_party_creation():
    """Test party creation and management."""
    async with httpx.AsyncClient(base_url=BASE_URL) as client:
        # First, authenticate
        login_data = {
            "username": "integrationtester",
            "password": "testpassword123",
        }

        # Try to login (user should exist from previous test)
        response = await client.post("/v1/auth/login", json=login_data)

        if response.status_code != 200:
            # User doesn't exist, register first
            register_data = {
                "email": "integration-test@example.com",
                "username": "integrationtester",
                "password": "testpassword123",
                "region": "us-west",
            }
            response = await client.post("/v1/auth/register", json=register_data)
            assert response.status_code in [200, 201]

        data = response.json()
        access_token = data["access_token"]
        headers = {"Authorization": f"Bearer {access_token}"}

        # Note: This will fail if user is already in a party
        # For now, we just test that the endpoint responds correctly
        response = await client.post("/v1/party", headers=headers, json={})

        # Either success or "already in party" error
        assert response.status_code in [200, 201, 400]

        if response.status_code in [200, 201]:
            party = response.json()
            assert "id" in party
            assert "leader_id" in party
            assert "status" in party


@pytest.mark.asyncio
async def test_health_check():
    """Test that the API is responsive."""
    async with httpx.AsyncClient(base_url=BASE_URL) as client:
        response = await client.get("/docs")
        assert response.status_code == 200


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])
