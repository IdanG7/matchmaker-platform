"""
Match Consumer - NATS event consumer for match.found events.

Listens for matches created by the matchmaker and allocates game sessions.
"""

import logging
import json
from datetime import datetime
from utils.database import get_db_pool
from utils.session_manager import (
    get_server_allocator,
    generate_session_token,
)
from models.schemas import SessionStatus

logger = logging.getLogger(__name__)


async def handle_match_found(message: dict):
    """
    Handle match.found event from matchmaker.

    Expected message format:
    {
        "match_id": "match_abc123",
        "region": "us-west",
        "mode": "ranked",
        "team_size": 5,
        "teams": [
            ["p1", "p2", "p3", "p4", "p5"],
            ["p6", "p7", "p8", "p9", "p10"]
        ],
        "party_ids": ["party1", "party2", ...],
        "avg_mmr": 1520,
        "mmr_variance": 45,
        "quality_score": 0.87
    }

    This function:
    1. Creates match record in database (status: allocating)
    2. Allocates game server
    3. Generates session token
    4. Updates match with server details (status: active)
    5. Updates player parties to in_match status
    """
    try:
        match_id = message.get("match_id")
        region = message.get("region")
        mode = message.get("mode")
        teams = message.get("teams", [])
        party_ids = message.get("party_ids", [])
        avg_mmr = message.get("avg_mmr")
        quality_score = message.get("quality_score")

        if not match_id or not teams:
            logger.error(f"Invalid match.found message: {message}")
            return

        # Flatten teams to get all player IDs
        all_player_ids = [player_id for team in teams for player_id in team]

        logger.info(
            f"Processing match.found: {match_id}, "
            f"{len(all_player_ids)} players, quality={quality_score:.2f}"
        )

        pool = await get_db_pool()
        async with pool.acquire() as conn:
            # 1. Create match record
            await conn.execute(
                """
                INSERT INTO game.match (id, mode, region, mmr_avg, status, metadata)
                VALUES ($1, $2, $3, $4, $5, $6)
                """,
                match_id,
                mode,
                region,
                avg_mmr,
                SessionStatus.ALLOCATING,
                json.dumps(
                    {
                        "quality_score": quality_score,
                        "party_ids": party_ids,
                        "teams": teams,
                    }
                ),
            )

            # 2. Insert match_player records
            for team_idx, team in enumerate(teams):
                for player_id in team:
                    # Get player's current MMR
                    player = await conn.fetchrow(
                        "SELECT mmr FROM game.player WHERE id = $1", player_id
                    )

                    if player:
                        await conn.execute(
                            """
                            INSERT INTO game.match_player
                            (match_id, player_id, team, mmr_before)
                            VALUES ($1, $2, $3, $4)
                            """,
                            match_id,
                            player_id,
                            team_idx,
                            player["mmr"],
                        )

            # 3. Allocate game server
            allocator = get_server_allocator()
            server_endpoint = allocator.allocate_server(match_id, region, mode)

            # 4. Generate session token
            session_token = generate_session_token(match_id, all_player_ids)

            # 5. Update match with server details and set to active
            await conn.execute(
                """
                UPDATE game.match
                SET server_endpoint = $1,
                    server_token = $2,
                    status = $3,
                    started_at = $4
                WHERE id = $5
                """,
                server_endpoint,
                session_token,
                SessionStatus.ACTIVE,
                datetime.utcnow(),
                match_id,
            )

            # 6. Update party statuses to in_match
            for party_id in party_ids:
                await conn.execute(
                    """
                    UPDATE game.party
                    SET status = 'in_match'
                    WHERE id = $1
                    """,
                    party_id,
                )

            logger.info(
                f"Session created for match {match_id}: "
                f"server={server_endpoint}, token={session_token[:16]}..."
            )

    except Exception as e:
        logger.error(f"Failed to handle match.found event: {e}", exc_info=True)


async def start_match_consumer(nats_client):
    """
    Start the match.found event consumer.

    Args:
        nats_client: NATS client instance
    """
    subject = "match.found"

    async def message_handler(msg):
        try:
            data = json.loads(msg.data.decode())
            await handle_match_found(data)
        except Exception as e:
            logger.error(f"Error processing NATS message: {e}", exc_info=True)

    # Subscribe to match.found events
    await nats_client.subscribe(subject, message_handler)
    logger.info(f"Match consumer started, listening on '{subject}'")
