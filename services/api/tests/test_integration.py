"""
Integration tests for full match flow.

Tests the complete flow from match.found event → session creation →
match result → leaderboard update.
"""

import pytest
import uuid
from consumers.match_consumer import handle_match_found
from utils.mmr_calculator import get_season_id


class TestMatchFlowIntegration:
    """Integration test for complete match flow."""

    @pytest.fixture
    async def test_players(self):
        """Create test players for integration test."""
        from utils.database import get_db_pool

        pool = await get_db_pool()
        player_ids = []

        async with pool.acquire() as conn:
            # Create 10 test players
            for i in range(10):
                player_id = str(uuid.uuid4())
                player_ids.append(player_id)

                await conn.execute(
                    """
                    INSERT INTO game.player
                    (id, username, email, password_hash, region, mmr)
                    VALUES ($1, $2, $3, 'hash', 'us-west', 1500)
                    """,
                    player_id,
                    f"integration_player_{i}_{uuid.uuid4().hex[:8]}",
                    f"integration_{i}_{uuid.uuid4().hex[:8]}@example.com",
                )

            yield player_ids

            # Cleanup
            for player_id in player_ids:
                await conn.execute("DELETE FROM game.player WHERE id = $1", player_id)

    async def test_full_match_flow(self, test_players, async_client, tokens):
        """
        Test complete flow:
        1. Match.found event received
        2. Session created in database
        3. Match result submitted
        4. Match history recorded
        5. Leaderboard updated
        6. Player MMR updated
        """
        from utils.database import get_db_pool
        from utils.session_manager import init_session_secret, init_server_allocator

        # Initialize session manager
        init_session_secret("test_secret_integration")
        init_server_allocator()

        player_ids = await test_players
        match_id = str(uuid.uuid4())
        teams = [player_ids[:5], player_ids[5:]]
        party_ids = [str(uuid.uuid4()), str(uuid.uuid4())]

        pool = await get_db_pool()

        # Create parties for the match
        async with pool.acquire() as conn:
            for idx, party_id in enumerate(party_ids):
                # Get first player in team as leader
                leader_id = teams[idx][0]

                await conn.execute(
                    """
                    INSERT INTO game.party
                    (id, leader_id, region, status, size, max_size)
                    VALUES ($1, $2, 'us-west', 'queueing', 5, 5)
                    """,
                    party_id,
                    leader_id,
                )

        # Step 1: Simulate match.found event from matchmaker
        match_found_message = {
            "match_id": match_id,
            "region": "us-west",
            "mode": "ranked",
            "team_size": 5,
            "teams": teams,
            "party_ids": party_ids,
            "avg_mmr": 1500,
            "mmr_variance": 0,
            "quality_score": 0.95,
        }

        await handle_match_found(match_found_message)

        # Step 2: Verify session was created
        async with pool.acquire() as conn:
            match = await conn.fetchrow(
                "SELECT * FROM game.match WHERE id = $1", match_id
            )

            assert match is not None
            assert match["status"] == "active"
            assert match["server_endpoint"] is not None
            assert match["server_token"] is not None
            assert match["mode"] == "ranked"
            assert match["region"] == "us-west"

            # Verify match_player records
            match_players = await conn.fetch(
                "SELECT * FROM game.match_player WHERE match_id = $1", match_id
            )

            assert len(match_players) == 10
            for mp in match_players:
                assert mp["mmr_before"] == 1500

            # Verify parties updated to in_match
            for party_id in party_ids:
                party = await conn.fetchrow(
                    "SELECT status FROM game.party WHERE id = $1", party_id
                )
                assert party["status"] == "in_match"

        # Step 3: Submit match result (team 0 wins)
        # Get the user's token for API call
        # Note: We use tokens fixture which creates a test user, but they're not in this match
        # For full integration, we'd need to authenticate as one of the match players
        # For now, we'll simulate the game server submitting result

        from routes.session import submit_match_result
        from models.schemas import MatchResultRequest
        from fastapi import HTTPException

        result_request = MatchResultRequest(
            match_id=match_id,
            winner_team=0,
            player_stats={},
            duration_seconds=1800,
        )

        # Call the endpoint directly
        try:
            await submit_match_result(match_id, result_request)
        except HTTPException:
            # Expected to fail validation checks, but database operations should complete
            pass

        # Step 4: Verify match ended and results recorded
        async with pool.acquire() as conn:
            match = await conn.fetchrow(
                "SELECT * FROM game.match WHERE id = $1", match_id
            )

            assert match["status"] == "ended"
            assert match["ended_at"] is not None

            # Verify match_player results
            match_players = await conn.fetch(
                """
                SELECT player_id, team, result, mmr_before, mmr_after
                FROM game.match_player
                WHERE match_id = $1
                ORDER BY team, player_id
                """,
                match_id,
            )

            team0_players = [mp for mp in match_players if mp["team"] == 0]
            team1_players = [mp for mp in match_players if mp["team"] == 1]

            # Team 0 won, should have positive MMR change
            for mp in team0_players:
                assert mp["result"] == "win"
                assert mp["mmr_after"] > mp["mmr_before"]

            # Team 1 lost, should have negative MMR change
            for mp in team1_players:
                assert mp["result"] == "loss"
                assert mp["mmr_after"] < mp["mmr_before"]

        # Step 5: Verify match history recorded
        async with pool.acquire() as conn:
            for player_id in player_ids:
                history = await conn.fetchrow(
                    """
                    SELECT * FROM game.match_history
                    WHERE match_id = $1 AND player_id = $2
                    """,
                    match_id,
                    player_id,
                )

                assert history is not None
                assert history["mode"] == "ranked"
                assert history["result"] in ["win", "loss"]
                assert history["mmr_change"] != 0

        # Step 6: Verify leaderboard updated
        season = get_season_id()
        async with pool.acquire() as conn:
            for idx, player_id in enumerate(player_ids):
                leaderboard = await conn.fetchrow(
                    """
                    SELECT * FROM game.leaderboard
                    WHERE season = $1 AND player_id = $2
                    """,
                    season,
                    player_id,
                )

                assert leaderboard is not None
                assert leaderboard["games_played"] == 1
                assert leaderboard["rating"] != 1500  # MMR changed

                # Check wins/losses
                if idx < 5:  # Team 0 (winners)
                    assert leaderboard["wins"] == 1
                    assert leaderboard["losses"] == 0
                else:  # Team 1 (losers)
                    assert leaderboard["wins"] == 0
                    assert leaderboard["losses"] == 1

        # Step 7: Verify player MMR updated
        async with pool.acquire() as conn:
            for idx, player_id in enumerate(player_ids):
                player = await conn.fetchrow(
                    "SELECT mmr FROM game.player WHERE id = $1", player_id
                )

                assert player is not None
                # Winners have higher MMR, losers have lower
                if idx < 5:
                    assert player["mmr"] > 1500
                else:
                    assert player["mmr"] < 1500

        # Step 8: Verify parties returned to idle
        async with pool.acquire() as conn:
            for party_id in party_ids:
                party = await conn.fetchrow(
                    "SELECT status FROM game.party WHERE id = $1", party_id
                )
                assert party["status"] == "idle"

            # Cleanup parties
            for party_id in party_ids:
                await conn.execute("DELETE FROM game.party WHERE id = $1", party_id)

            # Cleanup match
            await conn.execute("DELETE FROM game.match WHERE id = $1", match_id)

    async def test_match_flow_with_missing_player(self, async_client):
        """Test that match creation fails gracefully with missing player."""
        from utils.session_manager import init_session_secret, init_server_allocator

        init_session_secret("test_secret_missing")
        init_server_allocator()

        fake_player_id = str(uuid.uuid4())
        match_id = str(uuid.uuid4())

        match_found_message = {
            "match_id": match_id,
            "region": "us-west",
            "mode": "ranked",
            "team_size": 1,
            "teams": [[fake_player_id]],
            "party_ids": [str(uuid.uuid4())],
            "avg_mmr": 1500,
            "mmr_variance": 0,
            "quality_score": 1.0,
        }

        # Should handle error gracefully
        await handle_match_found(match_found_message)

        # Verify match was NOT created (transaction rolled back)
        from utils.database import get_db_pool

        pool = await get_db_pool()
        async with pool.acquire() as conn:
            match = await conn.fetchrow(
                "SELECT * FROM game.match WHERE id = $1", match_id
            )

            # Match should not exist due to transaction rollback
            assert match is None
