"""
Leaderboard and Match History API routes.
"""

import logging
from typing import Optional
from fastapi import APIRouter, HTTPException, Depends, Query, status
from utils.database import get_db_pool
from models.schemas import (
    MatchHistoryResponse,
    MatchHistoryEntry,
    LeaderboardResponse,
    LeaderboardEntry,
)
from utils.dependencies import get_current_user
from utils.mmr_calculator import get_season_id

logger = logging.getLogger(__name__)

router = APIRouter()


# ============================================================================
# Match History Endpoints
# ============================================================================


@router.get("/matches/history", response_model=MatchHistoryResponse)
async def get_match_history(
    player_id: Optional[str] = None,
    mode: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: dict = Depends(get_current_user),
):
    """
    Get match history (paginated).

    Players can query their own match history or specify another player's ID.

    Args:
        player_id: Player ID to query (defaults to current user)
        mode: Filter by game mode (optional)
        page: Page number (starts at 1)
        page_size: Number of entries per page (1-100)
        current_user: Authenticated user

    Returns:
        Paginated match history
    """
    try:
        # Default to current user if no player_id specified
        if player_id is None:
            player_id = current_user["id"]

        pool = await get_db_pool()
        async with pool.acquire() as conn:
            # Build query with parameterized placeholders
            params = [player_id]

            if mode:
                count_query = """
                    SELECT COUNT(*) as total
                    FROM game.match_history
                    WHERE player_id = $1 AND mode = $2
                """
                params.append(mode)
            else:
                count_query = """
                    SELECT COUNT(*) as total
                    FROM game.match_history
                    WHERE player_id = $1
                """

            count_result = await conn.fetchrow(count_query, *params)
            total = count_result["total"]

            # Get paginated entries
            offset = (page - 1) * page_size
            params.extend([page_size, offset])

            if mode:
                entries_query = """
                    SELECT match_id, played_at, mode, result, mmr_change, team, stats
                    FROM game.match_history
                    WHERE player_id = $1 AND mode = $2
                    ORDER BY played_at DESC
                    LIMIT $3 OFFSET $4
                """
            else:
                entries_query = """
                    SELECT match_id, played_at, mode, result, mmr_change, team, stats
                    FROM game.match_history
                    WHERE player_id = $1
                    ORDER BY played_at DESC
                    LIMIT $2 OFFSET $3
                """

            rows = await conn.fetch(entries_query, *params)

            entries = [
                MatchHistoryEntry(
                    match_id=str(row["match_id"]),
                    played_at=row["played_at"],
                    mode=row["mode"],
                    result=row["result"],
                    mmr_change=row["mmr_change"],
                    team=row["team"],
                    stats=row["stats"] or {},
                )
                for row in rows
            ]

            has_more = (page * page_size) < total

            return MatchHistoryResponse(
                entries=entries,
                total=total,
                page=page,
                page_size=page_size,
                has_more=has_more,
            )

    except Exception as e:
        logger.error(f"Get match history error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch match history",
        )


# ============================================================================
# Leaderboard Endpoints
# ============================================================================


@router.get("/leaderboard/{season}", response_model=LeaderboardResponse)
async def get_leaderboard(
    season: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
):
    """
    Get leaderboard for a season (paginated).

    Args:
        season: Season identifier (e.g., "2025-Q1")
        page: Page number (starts at 1)
        page_size: Number of entries per page (1-100)

    Returns:
        Paginated leaderboard
    """
    try:
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            # Get total count for season
            count_result = await conn.fetchrow(
                """
                SELECT COUNT(*) as total
                FROM game.leaderboard
                WHERE season = $1
                """,
                season,
            )
            total = count_result["total"]

            # Get paginated leaderboard entries
            offset = (page - 1) * page_size

            rows = await conn.fetch(
                """
                SELECT
                    l.player_id,
                    p.username,
                    l.rating,
                    l.rank,
                    l.wins,
                    l.losses,
                    l.games_played
                FROM game.leaderboard l
                JOIN game.player p ON l.player_id = p.id
                WHERE l.season = $1
                ORDER BY l.rating DESC, l.wins DESC
                LIMIT $2 OFFSET $3
                """,
                season,
                page_size,
                offset,
            )

            entries = [
                LeaderboardEntry(
                    player_id=str(row["player_id"]),
                    username=row["username"],
                    rating=row["rating"],
                    rank=row["rank"] or (offset + idx + 1),  # Calculate rank if not set
                    wins=row["wins"],
                    losses=row["losses"],
                    games_played=row["games_played"],
                    win_rate=(
                        row["wins"] / row["games_played"]
                        if row["games_played"] > 0
                        else 0.0
                    ),
                )
                for idx, row in enumerate(rows)
            ]

            return LeaderboardResponse(
                season=season,
                entries=entries,
                total=total,
                page=page,
                page_size=page_size,
            )

    except Exception as e:
        logger.error(f"Get leaderboard error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch leaderboard",
        )


@router.get("/leaderboard", response_model=LeaderboardResponse)
async def get_current_leaderboard(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
):
    """
    Get leaderboard for current season (paginated).

    Args:
        page: Page number (starts at 1)
        page_size: Number of entries per page (1-100)

    Returns:
        Paginated leaderboard for current season
    """
    season = get_season_id()
    return await get_leaderboard(season, page, page_size)
