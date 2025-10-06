"""
NATS event publishing for matchmaking queue.
"""

import logging
from typing import Optional
from datetime import datetime

logger = logging.getLogger(__name__)

# Global NATS client reference
_nats = None


def init_nats(nats_client):
    """Initialize the global NATS client."""
    global _nats
    _nats = nats_client
    logger.info("NATS events initialized")


def get_nats():
    """Get the global NATS client."""
    if _nats is None:
        raise RuntimeError("NATS client not initialized. Call init_nats() first.")
    return _nats


# ============================================================================
# Queue Event Publishers
# ============================================================================


async def publish_queue_enter(
    party_id: str,
    mode: str,
    team_size: int,
    avg_mmr: int,
    region: str,
    party_size: int,
):
    """
    Publish party enter queue event to matchmaker.

    Args:
        party_id: Party UUID
        mode: Game mode
        team_size: Players per team
        avg_mmr: Average MMR of party
        region: Party region
        party_size: Number of players in party
    """
    try:
        nats = get_nats()
        event = {
            "event_type": "queue_enter",
            "party_id": party_id,
            "mode": mode,
            "team_size": team_size,
            "avg_mmr": avg_mmr,
            "region": region,
            "party_size": party_size,
            "timestamp": datetime.utcnow().isoformat(),
        }

        # Publish to matchmaker queue subject
        # Subject pattern: matchmaker.queue.{mode}.{region}
        subject = f"matchmaker.queue.{mode}.{region}"
        await nats.publish(subject, event)

        logger.info(f"Published queue enter event for party {party_id} to {subject}")
    except Exception as e:
        logger.error(f"Failed to publish queue enter event for party {party_id}: {e}")


async def publish_queue_leave(party_id: str, mode: str, region: str):
    """
    Publish party leave queue event to matchmaker.

    Args:
        party_id: Party UUID
        mode: Game mode
        region: Party region
    """
    try:
        nats = get_nats()
        event = {
            "event_type": "queue_leave",
            "party_id": party_id,
            "mode": mode,
            "region": region,
            "timestamp": datetime.utcnow().isoformat(),
        }

        # Publish to matchmaker queue subject
        subject = f"matchmaker.queue.{mode}.{region}"
        await nats.publish(subject, event)

        logger.info(f"Published queue leave event for party {party_id} to {subject}")
    except Exception as e:
        logger.error(f"Failed to publish queue leave event for party {party_id}: {e}")


async def publish_party_disbanded(party_id: str, reason: str = "leader_left"):
    """
    Publish party disbanded event.

    Args:
        party_id: Party UUID
        reason: Reason for disbanding
    """
    try:
        nats = get_nats()
        event = {
            "event_type": "party_disbanded",
            "party_id": party_id,
            "reason": reason,
            "timestamp": datetime.utcnow().isoformat(),
        }

        # Publish to party events subject
        subject = "party.events"
        await nats.publish(subject, event)

        logger.info(f"Published party disbanded event for party {party_id}")
    except Exception as e:
        logger.error(
            f"Failed to publish party disbanded event for party {party_id}: {e}"
        )


async def publish_party_updated(
    party_id: str, update_type: str, data: Optional[dict] = None
):
    """
    Publish general party update event.

    Args:
        party_id: Party UUID
        update_type: Type of update (member_joined, member_left, ready_status, etc.)
        data: Additional update data
    """
    try:
        nats = get_nats()
        event = {
            "event_type": "party_updated",
            "party_id": party_id,
            "update_type": update_type,
            "data": data or {},
            "timestamp": datetime.utcnow().isoformat(),
        }

        # Publish to party events subject
        subject = "party.events"
        await nats.publish(subject, event)

        logger.debug(
            f"Published party updated event for party {party_id} ({update_type})"
        )
    except Exception as e:
        logger.error(f"Failed to publish party updated event for party {party_id}: {e}")
