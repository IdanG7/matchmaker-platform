"""
Redis caching utilities for party state.
"""

import json
import logging
from typing import Optional, Dict, Any
from datetime import timedelta

logger = logging.getLogger(__name__)

# Global Redis client reference
_redis = None


def init_redis(redis_client):
    """Initialize the global Redis client."""
    global _redis
    _redis = redis_client
    logger.info("Redis cache initialized")


def get_redis():
    """Get the global Redis client."""
    if _redis is None:
        raise RuntimeError("Redis client not initialized. Call init_redis() first.")
    return _redis


# ============================================================================
# Party Cache Functions
# ============================================================================


def cache_party(party_id: str, party_data: dict, ttl: int = 300):
    """
    Cache party data in Redis.

    Args:
        party_id: Party UUID
        party_data: Party data dictionary
        ttl: Time to live in seconds (default 5 minutes)
    """
    try:
        redis = get_redis()
        key = f"party:{party_id}"
        redis.setex(key, ttl, json.dumps(party_data, default=str))
        logger.debug(f"Cached party {party_id} with TTL {ttl}s")
    except Exception as e:
        logger.error(f"Failed to cache party {party_id}: {e}")


def get_cached_party(party_id: str) -> Optional[Dict[str, Any]]:
    """
    Get cached party data from Redis.

    Args:
        party_id: Party UUID

    Returns:
        Party data dictionary or None if not found/expired
    """
    try:
        redis = get_redis()
        key = f"party:{party_id}"
        data = redis.get(key)
        if data:
            logger.debug(f"Cache hit for party {party_id}")
            return json.loads(data)
        logger.debug(f"Cache miss for party {party_id}")
        return None
    except Exception as e:
        logger.error(f"Failed to get cached party {party_id}: {e}")
        return None


def invalidate_party_cache(party_id: str):
    """
    Invalidate party cache.

    Args:
        party_id: Party UUID
    """
    try:
        redis = get_redis()
        key = f"party:{party_id}"
        redis.delete(key)
        logger.debug(f"Invalidated cache for party {party_id}")
    except Exception as e:
        logger.error(f"Failed to invalidate party cache {party_id}: {e}")


# ============================================================================
# Ready Check Timer Functions
# ============================================================================


def set_ready_check_timer(party_id: str, timeout: int = 30):
    """
    Set a timer for ready check expiration.

    Args:
        party_id: Party UUID
        timeout: Timeout in seconds (default 30)

    Returns:
        True if timer set successfully, False otherwise
    """
    try:
        redis = get_redis()
        key = f"ready_check:{party_id}"
        redis.setex(key, timeout, "1")
        logger.info(f"Set ready check timer for party {party_id} ({timeout}s)")
        return True
    except Exception as e:
        logger.error(f"Failed to set ready check timer for party {party_id}: {e}")
        return False


def get_ready_check_ttl(party_id: str) -> Optional[int]:
    """
    Get remaining time on ready check timer.

    Args:
        party_id: Party UUID

    Returns:
        Remaining seconds or None if timer expired/not set
    """
    try:
        redis = get_redis()
        key = f"ready_check:{party_id}"
        ttl = redis.ttl(key)
        if ttl > 0:
            return ttl
        return None
    except Exception as e:
        logger.error(f"Failed to get ready check TTL for party {party_id}: {e}")
        return None


def clear_ready_check_timer(party_id: str):
    """
    Clear ready check timer.

    Args:
        party_id: Party UUID
    """
    try:
        redis = get_redis()
        key = f"ready_check:{party_id}"
        redis.delete(key)
        logger.debug(f"Cleared ready check timer for party {party_id}")
    except Exception as e:
        logger.error(f"Failed to clear ready check timer for party {party_id}: {e}")


# ============================================================================
# Queue Position Tracking
# ============================================================================


def cache_queue_position(party_id: str, position: int, ttl: int = 60):
    """
    Cache party's queue position.

    Args:
        party_id: Party UUID
        position: Position in queue
        ttl: Time to live in seconds (default 1 minute)
    """
    try:
        redis = get_redis()
        key = f"queue_pos:{party_id}"
        redis.setex(key, ttl, str(position))
        logger.debug(f"Cached queue position {position} for party {party_id}")
    except Exception as e:
        logger.error(f"Failed to cache queue position for party {party_id}: {e}")


def get_cached_queue_position(party_id: str) -> Optional[int]:
    """
    Get cached queue position.

    Args:
        party_id: Party UUID

    Returns:
        Queue position or None if not found/expired
    """
    try:
        redis = get_redis()
        key = f"queue_pos:{party_id}"
        position = redis.get(key)
        if position:
            return int(position)
        return None
    except Exception as e:
        logger.error(f"Failed to get cached queue position for party {party_id}: {e}")
        return None


# ============================================================================
# Player Session Tracking
# ============================================================================


def track_player_session(player_id: str, party_id: str, ttl: int = 3600):
    """
    Track player's current party session.

    Args:
        player_id: Player UUID
        party_id: Party UUID
        ttl: Time to live in seconds (default 1 hour)
    """
    try:
        redis = get_redis()
        key = f"player_session:{player_id}"
        redis.setex(key, ttl, party_id)
        logger.debug(f"Tracked session for player {player_id} in party {party_id}")
    except Exception as e:
        logger.error(f"Failed to track player session for {player_id}: {e}")


def get_player_session(player_id: str) -> Optional[str]:
    """
    Get player's current party session.

    Args:
        player_id: Player UUID

    Returns:
        Party UUID or None if not in a party/session expired
    """
    try:
        redis = get_redis()
        key = f"player_session:{player_id}"
        party_id = redis.get(key)
        return party_id
    except Exception as e:
        logger.error(f"Failed to get player session for {player_id}: {e}")
        return None


def clear_player_session(player_id: str):
    """
    Clear player's party session.

    Args:
        player_id: Player UUID
    """
    try:
        redis = get_redis()
        key = f"player_session:{player_id}"
        redis.delete(key)
        logger.debug(f"Cleared session for player {player_id}")
    except Exception as e:
        logger.error(f"Failed to clear player session for {player_id}: {e}")
