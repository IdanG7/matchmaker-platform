"""
Heartbeat Tracker - Redis-based game server heartbeat monitoring.
"""

import logging
from typing import Optional
from datetime import timedelta
from utils.redis_cache import get_redis

logger = logging.getLogger(__name__)

# Heartbeat TTL - servers must send heartbeat within this window
HEARTBEAT_TTL_SECONDS = 30

# Stale threshold - consider server dead after this many seconds
STALE_THRESHOLD_SECONDS = 60


def track_heartbeat(match_id: str, server_id: str, active_players: int):
    """
    Track a game server heartbeat in Redis.

    Args:
        match_id: Match UUID
        server_id: Game server identifier
        active_players: Number of active players

    The heartbeat is stored with a TTL. If the server stops sending heartbeats,
    the key will expire and we can detect the server is dead.
    """
    redis = get_redis()
    if redis is None:
        logger.warning("Redis not available, heartbeat tracking disabled")
        return

    try:
        key = f"heartbeat:{match_id}"
        value = f"{server_id}:{active_players}"

        # Set with TTL
        redis.setex(key, HEARTBEAT_TTL_SECONDS, value)

        logger.debug(
            f"Heartbeat tracked for match {match_id}, "
            f"server {server_id}, players {active_players}"
        )
    except Exception as e:
        logger.error(f"Failed to track heartbeat for match {match_id}: {e}")


def get_heartbeat(match_id: str) -> Optional[dict]:
    """
    Get the latest heartbeat for a match.

    Args:
        match_id: Match UUID

    Returns:
        Dict with server_id and active_players, or None if no heartbeat
    """
    redis = get_redis()
    if redis is None:
        return None

    try:
        key = f"heartbeat:{match_id}"
        value = redis.get(key)

        if value is None:
            return None

        # Parse value: "server_id:active_players"
        parts = value.split(":")
        if len(parts) != 2:
            logger.warning(f"Invalid heartbeat value for match {match_id}: {value}")
            return None

        return {"server_id": parts[0], "active_players": int(parts[1])}

    except Exception as e:
        logger.error(f"Failed to get heartbeat for match {match_id}: {e}")
        return None


def is_server_alive(match_id: str) -> bool:
    """
    Check if a game server is still sending heartbeats.

    Args:
        match_id: Match UUID

    Returns:
        True if server heartbeat is recent
    """
    return get_heartbeat(match_id) is not None


def clear_heartbeat(match_id: str):
    """
    Clear heartbeat tracking for a match.

    Args:
        match_id: Match UUID
    """
    redis = get_redis()
    if redis is None:
        return

    try:
        key = f"heartbeat:{match_id}"
        redis.delete(key)
        logger.debug(f"Cleared heartbeat for match {match_id}")
    except Exception as e:
        logger.error(f"Failed to clear heartbeat for match {match_id}: {e}")
