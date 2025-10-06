"""
Tests for party/lobby management endpoints.
"""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
class TestPartyEndpoints:
    """Test party management endpoints."""

    async def test_create_party(self, async_client: AsyncClient, tokens: dict):
        """Test creating a new party."""
        response = await async_client.post(
            "/v1/party",
            json={"max_size": 5, "region": "us-west"},
            headers={"Authorization": f"Bearer {tokens['access_token']}"},
        )

        assert response.status_code == 201
        data = response.json()
        assert "id" in data
        assert data["leader_id"] is not None
        assert data["size"] == 1
        assert data["max_size"] == 5
        assert data["status"] == "idle"
        assert data["region"] == "us-west"
        assert len(data["members"]) == 1
        assert data["members"][0]["ready"] is True  # Leader is auto-ready

    async def test_create_party_defaults(self, async_client: AsyncClient, tokens: dict):
        """Test creating a party with default values."""
        response = await async_client.post(
            "/v1/party",
            json={},
            headers={"Authorization": f"Bearer {tokens['access_token']}"},
        )

        assert response.status_code == 201
        data = response.json()
        assert data["max_size"] == 5  # Default

    async def test_create_party_already_in_party(
        self, async_client: AsyncClient, tokens: dict
    ):
        """Test creating a party when already in one."""
        # Create first party
        await async_client.post(
            "/v1/party",
            json={"max_size": 5},
            headers={"Authorization": f"Bearer {tokens['access_token']}"},
        )

        # Try to create another
        response = await async_client.post(
            "/v1/party",
            json={"max_size": 5},
            headers={"Authorization": f"Bearer {tokens['access_token']}"},
        )

        assert response.status_code == 400
        assert "already in a party" in response.json()["detail"]

    async def test_get_party(self, async_client: AsyncClient, tokens: dict):
        """Test getting party details."""
        # Create party
        create_response = await async_client.post(
            "/v1/party",
            json={"max_size": 4},
            headers={"Authorization": f"Bearer {tokens['access_token']}"},
        )
        party_id = create_response.json()["id"]

        # Get party
        response = await async_client.get(
            f"/v1/party/{party_id}",
            headers={"Authorization": f"Bearer {tokens['access_token']}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == party_id
        assert data["size"] == 1

    async def test_get_party_not_found(self, async_client: AsyncClient, tokens: dict):
        """Test getting a non-existent party."""
        response = await async_client.get(
            "/v1/party/00000000-0000-0000-0000-000000000000",
            headers={"Authorization": f"Bearer {tokens['access_token']}"},
        )

        assert response.status_code == 404

    async def test_join_party(
        self, async_client: AsyncClient, tokens: dict, second_user_tokens: dict
    ):
        """Test joining an existing party."""
        # User 1 creates party
        create_response = await async_client.post(
            "/v1/party",
            json={"max_size": 5},
            headers={"Authorization": f"Bearer {tokens['access_token']}"},
        )
        party_id = create_response.json()["id"]

        # User 2 joins party
        response = await async_client.post(
            f"/v1/party/{party_id}/join",
            headers={"Authorization": f"Bearer {second_user_tokens['access_token']}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["size"] == 2
        assert len(data["members"]) == 2
        # Second member should not be ready
        assert any(not m["ready"] for m in data["members"])

    async def test_join_party_already_in_party(
        self, async_client: AsyncClient, tokens: dict, second_user_tokens: dict
    ):
        """Test joining a party when already in one."""
        # User 1 creates party
        create_response = await async_client.post(
            "/v1/party",
            json={"max_size": 5},
            headers={"Authorization": f"Bearer {tokens['access_token']}"},
        )
        party_id = create_response.json()["id"]

        # User 2 creates their own party
        await async_client.post(
            "/v1/party",
            json={"max_size": 5},
            headers={"Authorization": f"Bearer {second_user_tokens['access_token']}"},
        )

        # User 2 tries to join User 1's party
        response = await async_client.post(
            f"/v1/party/{party_id}/join",
            headers={"Authorization": f"Bearer {second_user_tokens['access_token']}"},
        )

        assert response.status_code == 400
        assert "already in a party" in response.json()["detail"]

    async def test_join_party_full(
        self, async_client: AsyncClient, tokens: dict, second_user_tokens: dict
    ):
        """Test joining a full party."""
        # Create party with max_size=1
        create_response = await async_client.post(
            "/v1/party",
            json={"max_size": 1},
            headers={"Authorization": f"Bearer {tokens['access_token']}"},
        )
        party_id = create_response.json()["id"]

        # Try to join when full
        response = await async_client.post(
            f"/v1/party/{party_id}/join",
            headers={"Authorization": f"Bearer {second_user_tokens['access_token']}"},
        )

        assert response.status_code == 400
        assert "full" in response.json()["detail"].lower()

    async def test_leave_party(
        self, async_client: AsyncClient, tokens: dict, second_user_tokens: dict
    ):
        """Test leaving a party as a member."""
        # User 1 creates party
        create_response = await async_client.post(
            "/v1/party",
            json={"max_size": 5},
            headers={"Authorization": f"Bearer {tokens['access_token']}"},
        )
        party_id = create_response.json()["id"]

        # User 2 joins party
        await async_client.post(
            f"/v1/party/{party_id}/join",
            headers={"Authorization": f"Bearer {second_user_tokens['access_token']}"},
        )

        # User 2 leaves party
        response = await async_client.post(
            f"/v1/party/{party_id}/leave",
            headers={"Authorization": f"Bearer {second_user_tokens['access_token']}"},
        )

        assert response.status_code == 200
        assert "successfully" in response.json()["message"].lower()

        # Verify party size decreased
        get_response = await async_client.get(
            f"/v1/party/{party_id}",
            headers={"Authorization": f"Bearer {tokens['access_token']}"},
        )
        assert get_response.json()["size"] == 1

    async def test_leave_party_as_leader_disbands(
        self, async_client: AsyncClient, tokens: dict
    ):
        """Test that leader leaving disbands the party."""
        # Create party
        create_response = await async_client.post(
            "/v1/party",
            json={"max_size": 5},
            headers={"Authorization": f"Bearer {tokens['access_token']}"},
        )
        party_id = create_response.json()["id"]

        # Leader leaves
        response = await async_client.post(
            f"/v1/party/{party_id}/leave",
            headers={"Authorization": f"Bearer {tokens['access_token']}"},
        )

        assert response.status_code == 200
        assert "disbanded" in response.json()["message"].lower()

    async def test_toggle_ready(self, async_client: AsyncClient, tokens: dict):
        """Test toggling ready status."""
        # Create party
        create_response = await async_client.post(
            "/v1/party",
            json={"max_size": 5},
            headers={"Authorization": f"Bearer {tokens['access_token']}"},
        )
        party_id = create_response.json()["id"]

        # Toggle ready (should become false since leader starts ready)
        response = await async_client.post(
            f"/v1/party/{party_id}/ready",
            headers={"Authorization": f"Bearer {tokens['access_token']}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["party_id"] == party_id
        assert data["ready_count"] == 0
        assert data["total_count"] == 1
        assert data["all_ready"] is False

        # Toggle again (should become true)
        response2 = await async_client.post(
            f"/v1/party/{party_id}/ready",
            headers={"Authorization": f"Bearer {tokens['access_token']}"},
        )

        assert response2.status_code == 200
        data2 = response2.json()
        assert data2["ready_count"] == 1
        assert data2["all_ready"] is True

    async def test_enter_queue(self, async_client: AsyncClient, tokens: dict):
        """Test entering matchmaking queue."""
        # Create party
        create_response = await async_client.post(
            "/v1/party",
            json={"max_size": 5},
            headers={"Authorization": f"Bearer {tokens['access_token']}"},
        )
        party_id = create_response.json()["id"]

        # Leader is already ready, enter queue
        response = await async_client.post(
            f"/v1/party/{party_id}/queue",
            json={"mode": "ranked", "team_size": 5},
            headers={"Authorization": f"Bearer {tokens['access_token']}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "queueing"
        assert data["queue_mode"] == "ranked"
        assert data["team_size"] == 5
        assert data["avg_mmr"] is not None

    async def test_enter_queue_not_all_ready(
        self, async_client: AsyncClient, tokens: dict, second_user_tokens: dict
    ):
        """Test entering queue when not all members are ready."""
        # User 1 creates party
        create_response = await async_client.post(
            "/v1/party",
            json={"max_size": 5},
            headers={"Authorization": f"Bearer {tokens['access_token']}"},
        )
        party_id = create_response.json()["id"]

        # User 2 joins (and is not ready)
        await async_client.post(
            f"/v1/party/{party_id}/join",
            headers={"Authorization": f"Bearer {second_user_tokens['access_token']}"},
        )

        # Try to queue
        response = await async_client.post(
            f"/v1/party/{party_id}/queue",
            json={"mode": "ranked", "team_size": 5},
            headers={"Authorization": f"Bearer {tokens['access_token']}"},
        )

        assert response.status_code == 400
        assert "ready" in response.json()["detail"].lower()

    async def test_enter_queue_non_leader(
        self, async_client: AsyncClient, tokens: dict, second_user_tokens: dict
    ):
        """Test that non-leader cannot queue."""
        # User 1 creates party
        create_response = await async_client.post(
            "/v1/party",
            json={"max_size": 5},
            headers={"Authorization": f"Bearer {tokens['access_token']}"},
        )
        party_id = create_response.json()["id"]

        # User 2 joins
        await async_client.post(
            f"/v1/party/{party_id}/join",
            headers={"Authorization": f"Bearer {second_user_tokens['access_token']}"},
        )

        # User 2 tries to queue
        response = await async_client.post(
            f"/v1/party/{party_id}/queue",
            json={"mode": "ranked", "team_size": 5},
            headers={"Authorization": f"Bearer {second_user_tokens['access_token']}"},
        )

        assert response.status_code == 403
        assert "leader" in response.json()["detail"].lower()

    async def test_leave_queue(self, async_client: AsyncClient, tokens: dict):
        """Test leaving matchmaking queue."""
        # Create party and enter queue
        create_response = await async_client.post(
            "/v1/party",
            json={"max_size": 5},
            headers={"Authorization": f"Bearer {tokens['access_token']}"},
        )
        party_id = create_response.json()["id"]

        await async_client.post(
            f"/v1/party/{party_id}/queue",
            json={"mode": "ranked", "team_size": 5},
            headers={"Authorization": f"Bearer {tokens['access_token']}"},
        )

        # Leave queue
        response = await async_client.post(
            f"/v1/party/{party_id}/unqueue",
            headers={"Authorization": f"Bearer {tokens['access_token']}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "idle"
        assert data["queue_mode"] is None
        assert data["team_size"] is None

    async def test_leave_queue_not_queued(
        self, async_client: AsyncClient, tokens: dict
    ):
        """Test leaving queue when not in queue."""
        # Create party but don't queue
        create_response = await async_client.post(
            "/v1/party",
            json={"max_size": 5},
            headers={"Authorization": f"Bearer {tokens['access_token']}"},
        )
        party_id = create_response.json()["id"]

        # Try to leave queue
        response = await async_client.post(
            f"/v1/party/{party_id}/unqueue",
            headers={"Authorization": f"Bearer {tokens['access_token']}"},
        )

        assert response.status_code == 400
        assert "not in queue" in response.json()["detail"].lower()

    async def test_unauthorized_access(self, async_client: AsyncClient):
        """Test that endpoints require authentication."""
        response = await async_client.post("/v1/party", json={"max_size": 5})
        assert response.status_code == 401

    async def test_party_workflow(
        self, async_client: AsyncClient, tokens: dict, second_user_tokens: dict
    ):
        """Test complete party workflow."""
        # 1. User 1 creates party
        create_response = await async_client.post(
            "/v1/party",
            json={"max_size": 3, "region": "us-east"},
            headers={"Authorization": f"Bearer {tokens['access_token']}"},
        )
        assert create_response.status_code == 201
        party_id = create_response.json()["id"]

        # 2. User 2 joins
        join_response = await async_client.post(
            f"/v1/party/{party_id}/join",
            headers={"Authorization": f"Bearer {second_user_tokens['access_token']}"},
        )
        assert join_response.status_code == 200

        # 3. User 2 marks ready
        ready_response = await async_client.post(
            f"/v1/party/{party_id}/ready",
            headers={"Authorization": f"Bearer {second_user_tokens['access_token']}"},
        )
        assert ready_response.status_code == 200
        assert ready_response.json()["all_ready"] is True

        # 4. Leader queues
        queue_response = await async_client.post(
            f"/v1/party/{party_id}/queue",
            json={"mode": "casual", "team_size": 2},
            headers={"Authorization": f"Bearer {tokens['access_token']}"},
        )
        assert queue_response.status_code == 200
        assert queue_response.json()["status"] == "queueing"

        # 5. Leader unqueues
        unqueue_response = await async_client.post(
            f"/v1/party/{party_id}/unqueue",
            headers={"Authorization": f"Bearer {tokens['access_token']}"},
        )
        assert unqueue_response.status_code == 200

        # 6. User 2 leaves
        leave_response = await async_client.post(
            f"/v1/party/{party_id}/leave",
            headers={"Authorization": f"Bearer {second_user_tokens['access_token']}"},
        )
        assert leave_response.status_code == 200

        # 7. Verify party still exists with just leader
        get_response = await async_client.get(
            f"/v1/party/{party_id}",
            headers={"Authorization": f"Bearer {tokens['access_token']}"},
        )
        assert get_response.status_code == 200
        assert get_response.json()["size"] == 1
