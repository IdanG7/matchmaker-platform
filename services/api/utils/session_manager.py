"""
Session Manager - Game session allocation and lifecycle management.
"""

import hmac
import hashlib
import logging
from typing import Optional, List, Dict
from models.schemas import SessionStatus

logger = logging.getLogger(__name__)

# Global session secret for HMAC tokens
_session_secret: Optional[bytes] = None


def init_session_secret(secret: str):
    """Initialize the session token secret."""
    global _session_secret
    _session_secret = secret.encode("utf-8")
    logger.info("Session secret initialized")


def get_session_secret() -> bytes:
    """Get the session secret."""
    if _session_secret is None:
        raise RuntimeError(
            "Session secret not initialized. Call init_session_secret() first."
        )
    return _session_secret


# ============================================================================
# Mock Server Allocator
# ============================================================================


class MockServerAllocator:
    """
    Mock server allocator that returns static endpoints.
    In production, this would integrate with Agones/GameLift/etc.
    """

    def __init__(self, base_host: str = "game.example.com", base_port: int = 7777):
        self.base_host = base_host
        self.base_port = base_port
        self._allocated_servers: Dict[str, str] = {}

    def allocate_server(self, match_id: str, region: str, mode: str) -> str:
        """
        Allocate a game server for the match.

        Args:
            match_id: Match UUID
            region: Server region
            mode: Game mode

        Returns:
            Server endpoint (host:port)
        """
        # Mock allocation - in production would call cloud provider API
        # For now, return a static endpoint with incremented port
        port = self.base_port + len(self._allocated_servers)
        endpoint = f"{region}.{self.base_host}:{port}"

        self._allocated_servers[match_id] = endpoint

        logger.info(f"Allocated server for match {match_id}: {endpoint}")
        return endpoint

    def deallocate_server(self, match_id: str):
        """
        Deallocate a game server.

        Args:
            match_id: Match UUID
        """
        if match_id in self._allocated_servers:
            endpoint = self._allocated_servers.pop(match_id)
            logger.info(f"Deallocated server for match {match_id}: {endpoint}")


# Global server allocator instance
_server_allocator: Optional[MockServerAllocator] = None


def init_server_allocator(base_host: str = "game.example.com", base_port: int = 7777):
    """Initialize the global server allocator."""
    global _server_allocator
    _server_allocator = MockServerAllocator(base_host, base_port)
    logger.info("Server allocator initialized")


def get_server_allocator() -> MockServerAllocator:
    """Get the global server allocator."""
    if _server_allocator is None:
        raise RuntimeError(
            "Server allocator not initialized. Call init_server_allocator() first."
        )
    return _server_allocator


# ============================================================================
# Session Token Generation
# ============================================================================


def generate_session_token(match_id: str, player_ids: List[str]) -> str:
    """
    Generate HMAC session token for game server authentication.

    Args:
        match_id: Match UUID
        player_ids: List of player IDs in the match

    Returns:
        HMAC-SHA256 hex token
    """
    secret = get_session_secret()

    # Create message to sign: match_id + sorted player IDs
    message = f"{match_id}:{'|'.join(sorted(player_ids))}".encode("utf-8")

    # Generate HMAC-SHA256
    token = hmac.new(secret, message, hashlib.sha256).hexdigest()

    logger.debug(f"Generated session token for match {match_id}")
    return token


def verify_session_token(match_id: str, player_ids: List[str], token: str) -> bool:
    """
    Verify a session token.

    Args:
        match_id: Match UUID
        player_ids: List of player IDs in the match
        token: Token to verify

    Returns:
        True if token is valid
    """
    expected_token = generate_session_token(match_id, player_ids)
    return hmac.compare_digest(token, expected_token)


# ============================================================================
# Session Lifecycle Manager
# ============================================================================


class SessionLifecycleManager:
    """
    Manages session state transitions and lifecycle.

    States:
    - allocating: Server allocation in progress
    - active: Match is running
    - ended: Match completed normally
    - cancelled: Match cancelled/timed out
    """

    VALID_TRANSITIONS = {
        SessionStatus.ALLOCATING: [SessionStatus.ACTIVE, SessionStatus.CANCELLED],
        SessionStatus.ACTIVE: [SessionStatus.ENDED, SessionStatus.CANCELLED],
        SessionStatus.ENDED: [],
        SessionStatus.CANCELLED: [],
    }

    @staticmethod
    def can_transition(from_status: str, to_status: str) -> bool:
        """Check if state transition is valid."""
        return to_status in SessionLifecycleManager.VALID_TRANSITIONS.get(
            from_status, []
        )

    @staticmethod
    def validate_transition(from_status: str, to_status: str):
        """Validate state transition, raise ValueError if invalid."""
        if not SessionLifecycleManager.can_transition(from_status, to_status):
            raise ValueError(
                f"Invalid session state transition: {from_status} -> {to_status}"
            )
