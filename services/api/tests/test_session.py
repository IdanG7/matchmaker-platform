"""
Tests for session management endpoints and functionality.
"""

import pytest
import uuid
import json
from datetime import datetime
from httpx import AsyncClient
from models.schemas import SessionStatus
from utils.session_manager import (
    generate_session_token,
    verify_session_token,
    SessionLifecycleManager,
)
from consumers.match_consumer import handle_match_found


class TestSessionEndpoints:
    """Test session API endpoints."""

    @pytest.fixture
    async def setup_match(self, async_client, tokens):
        """Create a match for testing."""
        # Create match in database
        from utils.database import get_db_pool

        pool = await get_db_pool()
        async with pool.acquire() as conn:
            # Get test user ID
            user = await conn.fetchrow(
                "SELECT id FROM game.player WHERE username LIKE 'testuser_%' LIMIT 1"
            )
            player_id = str(user["id"])

            # Create match
            match_id = str(uuid.uuid4())
            await conn.execute(
                """
                INSERT INTO game.match
                (id, mode, region, status, server_endpoint, server_token, metadata)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
                """,
                match_id,
                "ranked",
                "us-west",
                SessionStatus.ACTIVE,
                "us-west.game.example.com:7777",
                "test_token_123",
                json.dumps({"teams": [[player_id], [str(uuid.uuid4())]]}),
            )

            # Add player to match
            await conn.execute(
                """
                INSERT INTO game.match_player
                (match_id, player_id, team, mmr_before)
                VALUES ($1, $2, 0, 1500)
                """,
                match_id,
                player_id,
            )

            yield {"match_id": match_id, "player_id": player_id}

            # Cleanup
            await conn.execute("DELETE FROM game.match WHERE id = $1", match_id)

    async def test_get_session_success(self, async_client, tokens, setup_match):
        """Test getting session details as participant."""
        match_data = await setup_match

        response = await async_client.get(
            f"/v1/session/{match_data['match_id']}",
            headers={"Authorization": f"Bearer {tokens['access_token']}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["match_id"] == match_data["match_id"]
        assert data["status"] == SessionStatus.ACTIVE
        assert data["server_endpoint"] == "us-west.game.example.com:7777"
        assert data["server_token"] == "test_token_123"
        assert data["mode"] == "ranked"
        assert data["region"] == "us-west"

    async def test_get_session_not_participant(
        self, async_client, second_user_tokens, setup_match
    ):
        """Test getting session as non-participant returns 403."""
        match_data = await setup_match

        response = await async_client.get(
            f"/v1/session/{match_data['match_id']}",
            headers={"Authorization": f"Bearer {second_user_tokens['access_token']}"},
        )

        assert response.status_code == 403
        assert "not a participant" in response.json()["detail"]

    async def test_get_session_not_found(self, async_client, tokens):
        """Test getting non-existent session returns 404."""
        fake_match_id = str(uuid.uuid4())

        response = await async_client.get(
            f"/v1/session/{fake_match_id}",
            headers={"Authorization": f"Bearer {tokens['access_token']}"},
        )

        assert response.status_code == 404

    async def test_session_heartbeat(self, async_client, setup_match):
        """Test game server heartbeat."""
        match_data = await setup_match

        response = await async_client.post(
            f"/v1/session/{match_data['match_id']}/heartbeat",
            json={
                "match_id": match_data["match_id"],
                "server_id": "server_1",
                "active_players": 10,
            },
        )

        assert response.status_code == 204

    async def test_heartbeat_inactive_match(self, async_client):
        """Test heartbeat on inactive match returns error."""
        from utils.database import get_db_pool

        pool = await get_db_pool()
        async with pool.acquire() as conn:
            match_id = str(uuid.uuid4())
            await conn.execute(
                """
                INSERT INTO game.match (id, mode, region, status)
                VALUES ($1, 'ranked', 'us-west', $2)
                """,
                match_id,
                SessionStatus.ENDED,
            )

            response = await async_client.post(
                f"/v1/session/{match_id}/heartbeat",
                json={
                    "match_id": match_id,
                    "server_id": "server_1",
                    "active_players": 0,
                },
            )

            assert response.status_code == 400
            assert "not active" in response.json()["detail"].lower()

            # Cleanup
            await conn.execute("DELETE FROM game.match WHERE id = $1", match_id)

    async def test_submit_match_result(self, async_client, setup_match):
        """Test submitting match result."""
        match_data = await setup_match

        response = await async_client.post(
            f"/v1/session/{match_data['match_id']}/result",
            json={
                "match_id": match_data["match_id"],
                "winner_team": 0,
                "player_stats": {},
                "duration_seconds": 1800,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"

        # Verify match status updated
        from utils.database import get_db_pool

        pool = await get_db_pool()
        async with pool.acquire() as conn:
            match = await conn.fetchrow(
                "SELECT status, ended_at, result FROM game.match WHERE id = $1",
                match_data["match_id"],
            )

            assert match["status"] == SessionStatus.ENDED
            assert match["ended_at"] is not None
            result = json.loads(match["result"]) if match["result"] else {}
            assert result.get("winner_team") == 0


class TestSessionManager:
    """Test session manager components."""

    def test_generate_session_token(self):
        """Test session token generation."""
        from utils.session_manager import init_session_secret

        init_session_secret("test_secret_key_12345")

        match_id = str(uuid.uuid4())
        player_ids = [str(uuid.uuid4()) for _ in range(10)]

        token = generate_session_token(match_id, player_ids)

        assert token is not None
        assert len(token) == 64  # SHA256 hex is 64 characters
        assert isinstance(token, str)

    def test_verify_session_token(self):
        """Test session token verification."""
        from utils.session_manager import init_session_secret

        init_session_secret("test_secret_key_12345")

        match_id = str(uuid.uuid4())
        player_ids = [str(uuid.uuid4()) for _ in range(10)]

        token = generate_session_token(match_id, player_ids)
        assert verify_session_token(match_id, player_ids, token) is True

        # Wrong token
        assert verify_session_token(match_id, player_ids, "invalid_token") is False

        # Wrong player IDs
        wrong_players = [str(uuid.uuid4()) for _ in range(10)]
        assert verify_session_token(match_id, wrong_players, token) is False

    def test_session_lifecycle_transitions(self):
        """Test valid and invalid session state transitions."""
        # Valid transitions
        assert SessionLifecycleManager.can_transition(
            SessionStatus.ALLOCATING, SessionStatus.ACTIVE
        )
        assert SessionLifecycleManager.can_transition(
            SessionStatus.ACTIVE, SessionStatus.ENDED
        )
        assert SessionLifecycleManager.can_transition(
            SessionStatus.ALLOCATING, SessionStatus.CANCELLED
        )

        # Invalid transitions
        assert not SessionLifecycleManager.can_transition(
            SessionStatus.ENDED, SessionStatus.ACTIVE
        )
        assert not SessionLifecycleManager.can_transition(
            SessionStatus.ENDED, SessionStatus.ALLOCATING
        )

    def test_session_lifecycle_validation(self):
        """Test session lifecycle validation raises errors."""
        # Valid transition should not raise
        SessionLifecycleManager.validate_transition(
            SessionStatus.ALLOCATING, SessionStatus.ACTIVE
        )

        # Invalid transition should raise ValueError
        with pytest.raises(ValueError, match="Invalid session state transition"):
            SessionLifecycleManager.validate_transition(
                SessionStatus.ENDED, SessionStatus.ACTIVE
            )

    def test_server_allocator(self):
        """Test mock server allocator."""
        from utils.session_manager import MockServerAllocator

        allocator = MockServerAllocator()

        match_id = str(uuid.uuid4())
        endpoint = allocator.allocate_server(match_id, "us-west", "ranked")

        assert endpoint is not None
        assert "us-west" in endpoint
        assert ":" in endpoint

        allocator.deallocate_server(match_id)


class TestMatchConsumer:
    """Test NATS match consumer."""

    async def test_handle_match_found(self):
        """Test handling match.found event."""
        from utils.database import get_db_pool
        from utils.session_manager import init_session_secret, init_server_allocator

        # Initialize session manager
        init_session_secret("test_secret_key_12345")
        init_server_allocator()

        # Create test players
        pool = await get_db_pool()
        player_ids = []
        async with pool.acquire() as conn:
            for i in range(10):
                player_id = str(uuid.uuid4())
                await conn.execute(
                    """
                    INSERT INTO game.player
                    (id, username, email, password_hash, region, mmr)
                    VALUES ($1, $2, $3, $4, 'us-west', 1500)
                    """,
                    player_id,
                    f"test_match_player_{i}_{uuid.uuid4().hex[:8]}",
                    f"test_{i}_{uuid.uuid4().hex[:8]}@example.com",
                    "hash",
                )
                player_ids.append(player_id)

        # Create match.found message
        match_id = f"match_{uuid.uuid4().hex[:16]}"
        teams = [player_ids[:5], player_ids[5:]]
        message = {
            "match_id": match_id,
            "region": "us-west",
            "mode": "ranked",
            "team_size": 5,
            "teams": teams,
            "party_ids": [str(uuid.uuid4())],
            "avg_mmr": 1500,
            "mmr_variance": 50,
            "quality_score": 0.85,
        }

        # Handle match.found event
        await handle_match_found(message)

        # Verify match created
        async with pool.acquire() as conn:
            match = await conn.fetchrow(
                "SELECT * FROM game.match WHERE id = $1", match_id
            )

            assert match is not None
            assert match["status"] == SessionStatus.ACTIVE
            assert match["server_endpoint"] is not None
            assert match["server_token"] is not None
            assert match["mode"] == "ranked"
            assert match["region"] == "us-west"

            # Verify match_player records created
            match_players = await conn.fetch(
                "SELECT * FROM game.match_player WHERE match_id = $1", match_id
            )

            assert len(match_players) == 10

            # Cleanup
            await conn.execute("DELETE FROM game.match WHERE id = $1", match_id)
            for player_id in player_ids:
                await conn.execute("DELETE FROM game.player WHERE id = $1", player_id)
