"""
Session API routes - Game session management endpoints.
"""

import logging
import json
from typing import Optional
from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends, status
from models.database import get_db_pool
from models.schemas import (
    SessionResponse,
    SessionStatus,
    MatchResultRequest,
    HeartbeatRequest,
)
from utils.dependencies import get_current_user
from utils.heartbeat_tracker import track_heartbeat, clear_heartbeat
from utils.session_manager import (
    SessionLifecycleManager,
    get_server_allocator,
    verify_session_token,
)

logger = logging.getLogger(__name__)

router = APIRouter()


# ============================================================================
# Session Endpoints
# ============================================================================


@router.get("/{match_id}", response_model=SessionResponse)
async def get_session(match_id: str, current_user: dict = Depends(get_current_user)):
    """
    Get session details for a match.

    Players can retrieve server endpoint and session token to connect to the game.

    Args:
        match_id: Match UUID
        current_user: Authenticated user (from JWT)

    Returns:
        SessionResponse with server details

    Raises:
        404: Match not found
        403: User is not a participant in this match
    """
    try:
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            # Fetch match
            match = await conn.fetchrow(
                """
                SELECT id, status, server_endpoint, server_token, created_at,
                       started_at, mode, region, mmr_avg, metadata
                FROM game.match
                WHERE id = $1
                """,
                match_id,
            )

            if not match:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Match not found",
                )

            # Check if user is a participant
            player_id = current_user["id"]
            participant = await conn.fetchrow(
                """
                SELECT 1 FROM game.match_player
                WHERE match_id = $1 AND player_id = $2
                """,
                match_id,
                player_id,
            )

            if not participant:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You are not a participant in this match",
                )

            # Parse teams from metadata
            metadata = match["metadata"] or {}
            teams = metadata.get("teams", [])

            return SessionResponse(
                match_id=str(match["id"]),
                status=match["status"],
                server_endpoint=match["server_endpoint"],
                server_token=match["server_token"],
                created_at=match["created_at"],
                started_at=match["started_at"],
                mode=match["mode"],
                region=match["region"],
                teams=teams,
                avg_mmr=match["mmr_avg"],
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get session error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch session",
        )


@router.post("/{match_id}/heartbeat", status_code=status.HTTP_204_NO_CONTENT)
async def session_heartbeat(match_id: str, request: HeartbeatRequest):
    """
    Game server heartbeat endpoint.

    Game servers should send heartbeats every 15-20 seconds to indicate they are alive.

    Args:
        match_id: Match UUID
        request: Heartbeat data (server_id, active_players)

    Raises:
        404: Match not found or not active
    """
    try:
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            # Verify match exists and is active
            match = await conn.fetchrow(
                "SELECT status FROM game.match WHERE id = $1", match_id
            )

            if not match:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Match not found",
                )

            if match["status"] != SessionStatus.ACTIVE:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Match is not active (status: {match['status']})",
                )

            # Track heartbeat in Redis
            track_heartbeat(match_id, request.server_id, request.active_players)

            logger.debug(
                f"Heartbeat from server {request.server_id} for match {match_id}"
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Heartbeat error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process heartbeat",
        )


@router.post("/{match_id}/result", status_code=status.HTTP_200_OK)
async def submit_match_result(match_id: str, request: MatchResultRequest):
    """
    Submit match result (called by game server).

    Updates match status to 'ended' and persists player results.

    Args:
        match_id: Match UUID
        request: Match result data

    Raises:
        404: Match not found
        400: Invalid state transition or data
    """
    try:
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            # Fetch match
            match = await conn.fetchrow(
                "SELECT status, metadata FROM game.match WHERE id = $1", match_id
            )

            if not match:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Match not found",
                )

            # Validate state transition
            current_status = match["status"]
            SessionLifecycleManager.validate_transition(
                current_status, SessionStatus.ENDED
            )

            metadata = match["metadata"] or {}
            teams = metadata.get("teams", [])

            if request.winner_team >= len(teams):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid winner_team: {request.winner_team}",
                )

            # Update match status
            await conn.execute(
                """
                UPDATE game.match
                SET status = $1,
                    ended_at = $2,
                    result = $3
                WHERE id = $4
                """,
                SessionStatus.ENDED,
                datetime.utcnow(),
                json.dumps(
                    {
                        "winner_team": request.winner_team,
                        "duration_seconds": request.duration_seconds,
                        "metadata": request.metadata or {},
                    }
                ),
                match_id,
            )

            # Update match_player results
            for team_idx, team in enumerate(teams):
                result_type = "win" if team_idx == request.winner_team else "loss"

                for player_id in team:
                    # Get player stats from request
                    player_stats = request.player_stats.get(player_id, {})

                    await conn.execute(
                        """
                        UPDATE game.match_player
                        SET result = $1,
                            stats = $2,
                            mmr_after = mmr_before
                        WHERE match_id = $3 AND player_id = $4
                        """,
                        result_type,
                        json.dumps(player_stats),
                        match_id,
                        player_id,
                    )

            # Update party statuses to idle
            party_ids = metadata.get("party_ids", [])
            for party_id in party_ids:
                await conn.execute(
                    """
                    UPDATE game.party
                    SET status = 'idle'
                    WHERE id = $1
                    """,
                    party_id,
                )

            # Clear heartbeat tracking
            clear_heartbeat(match_id)

            # Deallocate server
            allocator = get_server_allocator()
            allocator.deallocate_server(match_id)

            logger.info(
                f"Match {match_id} ended, winner: team {request.winner_team}, "
                f"duration: {request.duration_seconds}s"
            )

            return {"status": "success", "match_id": match_id}

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Submit match result error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to submit match result",
        )
