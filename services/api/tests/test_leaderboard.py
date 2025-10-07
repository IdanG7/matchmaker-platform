"""
Tests for leaderboard and match history endpoints.
"""

import pytest
import uuid
import json
from datetime import datetime, timedelta
from httpx import AsyncClient
from utils.mmr_calculator import calculate_mmr_change, get_season_id


class TestMatchHistory:
    """Test match history endpoints."""

    @pytest.fixture
    async def setup_match_history(self, tokens):
        """Create match history entries for testing."""
        from utils.database import get_db_pool

        pool = await get_db_pool()
        async with pool.acquire() as conn:
            # Get test user ID
            user = await conn.fetchrow(
                "SELECT id FROM game.player WHERE username LIKE 'testuser_%' LIMIT 1"
            )
            player_id = str(user["id"])

            # Create match history entries
            match_ids = []
            for i in range(5):
                match_id = str(uuid.uuid4())
                match_ids.append(match_id)

                # Create match first
                await conn.execute(
                    """
                    INSERT INTO game.match (id, mode, region, status)
                    VALUES ($1, 'ranked', 'us-west', 'ended')
                    """,
                    match_id,
                )

                # Create match history
                await conn.execute(
                    """
                    INSERT INTO game.match_history
                    (match_id, player_id, mode, result, mmr_change, team, played_at)
                    VALUES ($1, $2, 'ranked', $3, $4, 0, $5)
                    """,
                    match_id,
                    player_id,
                    "win" if i % 2 == 0 else "loss",
                    25 if i % 2 == 0 else -20,
                    datetime.utcnow() - timedelta(hours=i),
                )

            yield {"player_id": player_id, "match_ids": match_ids}

            # Cleanup
            for match_id in match_ids:
                await conn.execute("DELETE FROM game.match WHERE id = $1", match_id)

    async def test_get_match_history_own(
        self, async_client, tokens, setup_match_history
    ):
        """Test getting own match history."""
        data = await setup_match_history

        response = await async_client.get(
            "/v1/matches/history",
            headers={"Authorization": f"Bearer {tokens['access_token']}"},
        )

        assert response.status_code == 200
        result = response.json()
        assert result["total"] >= 5
        assert len(result["entries"]) >= 5
        assert result["page"] == 1
        assert result["page_size"] == 20

        # Check entry structure
        entry = result["entries"][0]
        assert "match_id" in entry
        assert "played_at" in entry
        assert "mode" in entry
        assert "result" in entry
        assert "mmr_change" in entry
        assert "team" in entry

    async def test_get_match_history_pagination(
        self, async_client, tokens, setup_match_history
    ):
        """Test match history pagination."""
        await setup_match_history

        response = await async_client.get(
            "/v1/matches/history?page=1&page_size=2",
            headers={"Authorization": f"Bearer {tokens['access_token']}"},
        )

        assert response.status_code == 200
        result = response.json()
        assert len(result["entries"]) <= 2
        assert result["page"] == 1
        assert result["page_size"] == 2

    async def test_get_match_history_filter_mode(
        self, async_client, tokens, setup_match_history
    ):
        """Test match history filtering by mode."""
        await setup_match_history

        response = await async_client.get(
            "/v1/matches/history?mode=ranked",
            headers={"Authorization": f"Bearer {tokens['access_token']}"},
        )

        assert response.status_code == 200
        result = response.json()
        assert all(entry["mode"] == "ranked" for entry in result["entries"])


class TestLeaderboard:
    """Test leaderboard endpoints."""

    @pytest.fixture
    async def setup_leaderboard(self):
        """Create leaderboard entries for testing."""
        from utils.database import get_db_pool

        pool = await get_db_pool()
        async with pool.acquire() as conn:
            season = get_season_id()
            player_ids = []

            # Create test players with leaderboard entries
            for i in range(10):
                player_id = str(uuid.uuid4())
                username = f"leader_{i}_{uuid.uuid4().hex[:8]}"
                player_ids.append(player_id)

                await conn.execute(
                    """
                    INSERT INTO game.player
                    (id, username, email, password_hash, region, mmr)
                    VALUES ($1, $2, $3, 'hash', 'us-west', $4)
                    """,
                    player_id,
                    username,
                    f"{username}@example.com",
                    1500 + (i * 50),
                )

                await conn.execute(
                    """
                    INSERT INTO game.leaderboard
                    (season, player_id, rating, wins, losses, games_played)
                    VALUES ($1, $2, $3, $4, $5, $6)
                    """,
                    season,
                    player_id,
                    1500 + (i * 50),
                    10 + i,
                    5,
                    15 + i,
                )

            yield {"season": season, "player_ids": player_ids}

            # Cleanup
            for player_id in player_ids:
                await conn.execute("DELETE FROM game.player WHERE id = $1", player_id)

    async def test_get_leaderboard(self, async_client, setup_leaderboard):
        """Test getting leaderboard."""
        data = await setup_leaderboard

        response = await async_client.get(f"/v1/leaderboard/{data['season']}")

        assert response.status_code == 200
        result = response.json()
        assert result["season"] == data["season"]
        assert result["total"] >= 10
        assert len(result["entries"]) >= 10

        # Check leaderboard is sorted by rating desc
        ratings = [entry["rating"] for entry in result["entries"]]
        assert ratings == sorted(ratings, reverse=True)

        # Check entry structure
        entry = result["entries"][0]
        assert "player_id" in entry
        assert "username" in entry
        assert "rating" in entry
        assert "rank" in entry
        assert "wins" in entry
        assert "losses" in entry
        assert "games_played" in entry
        assert "win_rate" in entry

    async def test_get_leaderboard_pagination(self, async_client, setup_leaderboard):
        """Test leaderboard pagination."""
        data = await setup_leaderboard

        response = await async_client.get(
            f"/v1/leaderboard/{data['season']}?page=1&page_size=5"
        )

        assert response.status_code == 200
        result = response.json()
        assert len(result["entries"]) <= 5
        assert result["page"] == 1
        assert result["page_size"] == 5

    async def test_get_current_leaderboard(self, async_client, setup_leaderboard):
        """Test getting current season leaderboard."""
        await setup_leaderboard

        response = await async_client.get("/v1/leaderboard")

        assert response.status_code == 200
        result = response.json()
        assert result["season"] == get_season_id()


class TestMMRCalculation:
    """Test MMR calculation logic."""

    def test_calculate_mmr_change_win(self):
        """Test MMR change calculation for a win."""
        player_rating = 1500
        opponent_rating = 1500

        mmr_change = calculate_mmr_change(player_rating, opponent_rating, "win")

        assert mmr_change == 16  # K=32, expected=0.5, actual=1.0, change=32*0.5=16

    def test_calculate_mmr_change_loss(self):
        """Test MMR change calculation for a loss."""
        player_rating = 1500
        opponent_rating = 1500

        mmr_change = calculate_mmr_change(player_rating, opponent_rating, "loss")

        assert mmr_change == -16  # K=32, expected=0.5, actual=0.0, change=32*-0.5=-16

    def test_calculate_mmr_change_underdog_win(self):
        """Test MMR change for underdog winning."""
        player_rating = 1400
        opponent_rating = 1600  # Opponent is 200 MMR higher

        mmr_change = calculate_mmr_change(player_rating, opponent_rating, "win")

        # Underdog win should give more MMR
        assert mmr_change > 16

    def test_calculate_mmr_change_favorite_loss(self):
        """Test MMR change for favorite losing."""
        player_rating = 1600
        opponent_rating = 1400  # Opponent is 200 MMR lower

        mmr_change = calculate_mmr_change(player_rating, opponent_rating, "loss")

        # Favorite loss should lose more MMR
        assert mmr_change < -16

    def test_calculate_mmr_change_draw(self):
        """Test MMR change for a draw."""
        player_rating = 1500
        opponent_rating = 1500

        mmr_change = calculate_mmr_change(player_rating, opponent_rating, "draw")

        assert mmr_change == 0  # Equal players drawing = no change
