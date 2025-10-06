"""
Party/Lobby management endpoints.
"""

import logging
from typing import List
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from asyncpg import UniqueViolationError

from models.schemas import (
    CreatePartyRequest,
    PartyResponse,
    PartyMemberResponse,
    InvitePlayerRequest,
    QueueRequest,
    ReadyCheckResponse,
)
from utils.dependencies import get_current_user
from utils.database import get_db_connection
from routes.websocket import (
    broadcast_member_joined,
    broadcast_member_left,
    broadcast_member_ready,
    broadcast_queue_entered,
    broadcast_queue_left,
)
from utils.redis_cache import (
    cache_party,
    get_cached_party,
    invalidate_party_cache,
    track_player_session,
    clear_player_session,
    set_ready_check_timer,
    clear_ready_check_timer,
)
from utils.nats_events import publish_queue_enter, publish_queue_leave

logger = logging.getLogger(__name__)
router = APIRouter()


async def _get_party_with_members(conn, party_id: str) -> dict:
    """
    Helper function to fetch party with all members.

    Args:
        conn: Database connection
        party_id: Party UUID

    Returns:
        Party dict with members list

    Raises:
        HTTPException: If party not found
    """
    # Fetch party
    party = await conn.fetchrow(
        """
        SELECT id, leader_id, created_at, updated_at, region, size, max_size,
               status, queue_mode, team_size, avg_mmr
        FROM game.party
        WHERE id = $1
        """,
        party_id,
    )

    if not party:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Party not found"
        )

    # Fetch members with player info
    members = await conn.fetch(
        """
        SELECT pm.player_id, p.username, pm.joined_at, pm.ready, pm.role
        FROM game.party_member pm
        JOIN game.player p ON pm.player_id = p.id
        WHERE pm.party_id = $1
        ORDER BY pm.joined_at ASC
        """,
        party_id,
    )

    party_dict = dict(party)
    party_dict["members"] = [dict(m) for m in members]
    return party_dict


@router.post("", response_model=PartyResponse, status_code=status.HTTP_201_CREATED)
async def create_party(
    request: CreatePartyRequest,
    current_user: dict = Depends(get_current_user),
    conn=Depends(get_db_connection),
):
    """
    Create a new party.

    The authenticated user becomes the party leader.
    """
    try:
        player_id = current_user["id"]
        region = request.region or current_user["region"]

        # Check if player is already in a party
        existing = await conn.fetchval(
            "SELECT party_id FROM game.party_member WHERE player_id = $1", player_id
        )

        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Player is already in a party",
            )

        # Create party
        party = await conn.fetchrow(
            """
            INSERT INTO game.party (leader_id, region, size, max_size, status)
            VALUES ($1, $2, 1, $3, 'idle')
            RETURNING id, leader_id, created_at, updated_at, region, size, max_size,
                      status, queue_mode, team_size, avg_mmr
            """,
            player_id,
            region,
            request.max_size,
        )

        party_id = party["id"]

        # Add leader as first member
        await conn.execute(
            """
            INSERT INTO game.party_member (party_id, player_id, ready)
            VALUES ($1, $2, TRUE)
            """,
            party_id,
            player_id,
        )

        logger.info(f"Party {party_id} created by {current_user['username']}")

        # Fetch full party with members
        party_data = await _get_party_with_members(conn, str(party_id))

        # Cache party and track player session
        cache_party(str(party_id), party_data)
        track_player_session(player_id, str(party_id))

        return PartyResponse(**party_data)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Create party error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create party",
        )


@router.get("/{party_id}", response_model=PartyResponse)
async def get_party(
    party_id: str,
    current_user: dict = Depends(get_current_user),
    conn=Depends(get_db_connection),
):
    """Get party details."""
    try:
        # Try cache first
        cached = get_cached_party(party_id)
        if cached:
            return PartyResponse(**cached)

        # Cache miss - fetch from database
        party_data = await _get_party_with_members(conn, party_id)

        # Cache the result
        cache_party(party_id, party_data)

        return PartyResponse(**party_data)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get party error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch party",
        )


@router.post("/{party_id}/join", response_model=PartyResponse)
async def join_party(
    party_id: str,
    current_user: dict = Depends(get_current_user),
    conn=Depends(get_db_connection),
):
    """Join an existing party."""
    try:
        player_id = current_user["id"]

        # Check if player is already in a party
        existing = await conn.fetchval(
            "SELECT party_id FROM game.party_member WHERE player_id = $1", player_id
        )

        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Player is already in a party",
            )

        # Fetch party with lock
        party = await conn.fetchrow(
            """
            SELECT id, size, max_size, status
            FROM game.party
            WHERE id = $1
            FOR UPDATE
            """,
            party_id,
        )

        if not party:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Party not found"
            )

        # Check if party is full
        if party["size"] >= party["max_size"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Party is full"
            )

        # Check party status
        if party["status"] not in ["idle", "queueing"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot join party in {party['status']} status",
            )

        # Add member
        await conn.execute(
            """
            INSERT INTO game.party_member (party_id, player_id, ready)
            VALUES ($1, $2, FALSE)
            """,
            party_id,
            player_id,
        )

        # Update party size
        await conn.execute(
            """
            UPDATE game.party
            SET size = size + 1, updated_at = now()
            WHERE id = $1
            """,
            party_id,
        )

        logger.info(f"Player {current_user['username']} joined party {party_id}")

        # Broadcast member joined event
        await broadcast_member_joined(party_id, player_id, current_user["username"])

        # Invalidate cache and track player session
        invalidate_party_cache(party_id)
        track_player_session(player_id, party_id)

        # Fetch updated party
        party_data = await _get_party_with_members(conn, party_id)

        # Cache updated party
        cache_party(party_id, party_data)

        return PartyResponse(**party_data)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Join party error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to join party",
        )


@router.post("/{party_id}/leave", response_model=dict)
async def leave_party(
    party_id: str,
    current_user: dict = Depends(get_current_user),
    conn=Depends(get_db_connection),
):
    """Leave a party."""
    try:
        player_id = current_user["id"]

        # Check if player is in this party
        member = await conn.fetchval(
            """
            SELECT 1 FROM game.party_member
            WHERE party_id = $1 AND player_id = $2
            """,
            party_id,
            player_id,
        )

        if not member:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Player is not in this party",
            )

        # Fetch party
        party = await conn.fetchrow(
            """
            SELECT leader_id, size FROM game.party WHERE id = $1 FOR UPDATE
            """,
            party_id,
        )

        if not party:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Party not found"
            )

        is_leader = str(party["leader_id"]) == player_id

        # Remove member
        await conn.execute(
            "DELETE FROM game.party_member WHERE party_id = $1 AND player_id = $2",
            party_id,
            player_id,
        )

        # If leader left or party is now empty, disband party
        if is_leader or party["size"] <= 1:
            await conn.execute(
                """
                UPDATE game.party
                SET status = 'disbanded', updated_at = now()
                WHERE id = $1
                """,
                party_id,
            )
            logger.info(f"Party {party_id} disbanded")
            return {"message": "Party disbanded", "party_id": party_id}
        else:
            # Update party size
            await conn.execute(
                """
                UPDATE game.party
                SET size = size - 1, updated_at = now()
                WHERE id = $1
                """,
                party_id,
            )

        logger.info(f"Player {current_user['username']} left party {party_id}")

        # Broadcast member left event
        await broadcast_member_left(party_id, player_id, current_user["username"])

        # Invalidate cache and clear player session
        invalidate_party_cache(party_id)
        clear_player_session(player_id)

        return {"message": "Left party successfully", "party_id": party_id}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Leave party error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to leave party",
        )


@router.post("/{party_id}/ready", response_model=ReadyCheckResponse)
async def toggle_ready(
    party_id: str,
    current_user: dict = Depends(get_current_user),
    conn=Depends(get_db_connection),
):
    """Toggle ready status for the current player."""
    try:
        player_id = current_user["id"]

        # Toggle ready status
        result = await conn.fetchrow(
            """
            UPDATE game.party_member
            SET ready = NOT ready
            WHERE party_id = $1 AND player_id = $2
            RETURNING ready
            """,
            party_id,
            player_id,
        )

        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Player is not in this party",
            )

        # Get ready status
        ready_stats = await conn.fetchrow(
            """
            SELECT
                COUNT(*) as total,
                COUNT(*) FILTER (WHERE ready = TRUE) as ready_count
            FROM game.party_member
            WHERE party_id = $1
            """,
            party_id,
        )

        # Get not ready players
        not_ready = await conn.fetch(
            """
            SELECT p.username
            FROM game.party_member pm
            JOIN game.player p ON pm.player_id = p.id
            WHERE pm.party_id = $1 AND pm.ready = FALSE
            """,
            party_id,
        )

        total = ready_stats["total"]
        ready_count = ready_stats["ready_count"]
        all_ready = ready_count == total

        # Update party updated_at
        await conn.execute(
            "UPDATE game.party SET updated_at = now() WHERE id = $1", party_id
        )

        logger.info(
            f"Player {current_user['username']} toggled ready in party {party_id}"
        )

        # Broadcast member ready event
        await broadcast_member_ready(
            party_id, player_id, current_user["username"], result["ready"]
        )

        # Invalidate cache
        invalidate_party_cache(party_id)

        return ReadyCheckResponse(
            party_id=party_id,
            ready_count=ready_count,
            total_count=total,
            all_ready=all_ready,
            not_ready_players=[r["username"] for r in not_ready],
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Toggle ready error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to toggle ready status",
        )


@router.post("/{party_id}/queue", response_model=PartyResponse)
async def enter_queue(
    party_id: str,
    request: QueueRequest,
    current_user: dict = Depends(get_current_user),
    conn=Depends(get_db_connection),
):
    """Enter matchmaking queue."""
    try:
        player_id = current_user["id"]

        # Fetch party
        party = await conn.fetchrow(
            """
            SELECT leader_id, status, size, region FROM game.party WHERE id = $1 FOR UPDATE
            """,
            party_id,
        )

        if not party:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Party not found"
            )

        # Only leader can queue
        if str(party["leader_id"]) != player_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only party leader can queue",
            )

        # Check all members are ready
        ready_stats = await conn.fetchrow(
            """
            SELECT COUNT(*) as total, COUNT(*) FILTER (WHERE ready = TRUE) as ready
            FROM game.party_member WHERE party_id = $1
            """,
            party_id,
        )

        if ready_stats["ready"] != ready_stats["total"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="All members must be ready before queueing",
            )

        # Calculate average MMR
        avg_mmr = await conn.fetchval(
            """
            SELECT AVG(p.mmr)::int
            FROM game.party_member pm
            JOIN game.player p ON pm.player_id = p.id
            WHERE pm.party_id = $1
            """,
            party_id,
        )

        # Update party status to queueing
        await conn.execute(
            """
            UPDATE game.party
            SET status = 'queueing',
                queue_mode = $2,
                team_size = $3,
                avg_mmr = $4,
                updated_at = now()
            WHERE id = $1
            """,
            party_id,
            request.mode,
            request.team_size,
            avg_mmr,
        )

        # Publish queue event to NATS for matchmaker
        try:
            await publish_queue_enter(
                party_id=party_id,
                mode=request.mode,
                team_size=request.team_size,
                avg_mmr=avg_mmr,
                region=party["region"],
                party_size=party["size"],
            )
        except Exception as e:
            logger.warning(f"Failed to publish queue enter event: {e}")

        logger.info(
            f"Party {party_id} entered queue for mode={request.mode}, "
            f"team_size={request.team_size}, avg_mmr={avg_mmr}"
        )

        # Broadcast queue entered event
        await broadcast_queue_entered(party_id, request.mode, request.team_size)

        # Invalidate cache and set ready check timer
        invalidate_party_cache(party_id)
        set_ready_check_timer(party_id, timeout=30)

        # Fetch updated party
        party_data = await _get_party_with_members(conn, party_id)

        # Cache updated party
        cache_party(party_id, party_data)

        return PartyResponse(**party_data)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Enter queue error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to enter queue",
        )


@router.post("/{party_id}/unqueue", response_model=PartyResponse)
async def leave_queue(
    party_id: str,
    current_user: dict = Depends(get_current_user),
    conn=Depends(get_db_connection),
):
    """Leave matchmaking queue."""
    try:
        player_id = current_user["id"]

        # Fetch party
        party = await conn.fetchrow(
            """
            SELECT leader_id, status, queue_mode, region FROM game.party WHERE id = $1 FOR UPDATE
            """,
            party_id,
        )

        if not party:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Party not found"
            )

        # Only leader can unqueue
        if str(party["leader_id"]) != player_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only party leader can leave queue",
            )

        # Check party is queueing
        if party["status"] != "queueing":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Party is not in queue",
            )

        # Update party status back to idle
        await conn.execute(
            """
            UPDATE game.party
            SET status = 'idle',
                queue_mode = NULL,
                team_size = NULL,
                updated_at = now()
            WHERE id = $1
            """,
            party_id,
        )

        # Publish dequeue event to NATS for matchmaker
        try:
            await publish_queue_leave(
                party_id=party_id,
                mode=party["queue_mode"] or "unknown",
                region=party["region"],
            )
        except Exception as e:
            logger.warning(f"Failed to publish queue leave event: {e}")

        logger.info(f"Party {party_id} left queue")

        # Broadcast queue left event
        await broadcast_queue_left(party_id)

        # Invalidate cache and clear ready check timer
        invalidate_party_cache(party_id)
        clear_ready_check_timer(party_id)

        # Fetch updated party
        party_data = await _get_party_with_members(conn, party_id)

        # Cache updated party
        cache_party(party_id, party_data)

        return PartyResponse(**party_data)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Leave queue error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to leave queue",
        )
