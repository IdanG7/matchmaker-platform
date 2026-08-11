"""
Session Manager - Game session allocation and lifecycle management.
"""

import hmac
import hashlib
import logging
import os
from typing import Optional, List, Dict, Union
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
    Returns synthetic endpoints. Nothing listens on them, so this is only
    suitable for tests that never open a socket. Real deployments configure
    GAME_SERVER_AGENT_URL and get HttpServerAllocator instead.
    """

    def __init__(self, base_host: str = "game.example.com", base_port: int = 7777):
        self.base_host = base_host
        self.base_port = base_port
        self._allocated_servers: Dict[str, str] = {}

    async def allocate_server(
        self, match_id: str, region: str, mode: str, players: int = 0
    ) -> str:
        """
        Allocate a game server for the match.

        Args:
            match_id: Match UUID
            region: Server region
            mode: Game mode
            players: Expected player count

        Returns:
            Server endpoint (host:port)
        """
        port = self.base_port + len(self._allocated_servers)
        endpoint = f"{region}.{self.base_host}:{port}"

        self._allocated_servers[match_id] = endpoint

        logger.warning(
            f"Allocated MOCK server for match {match_id}: {endpoint} "
            f"(nothing is listening there; set GAME_SERVER_AGENT_URL for real servers)"
        )
        return endpoint

    def server_url(self, match_id: str) -> str:
        """No proxy in front of a mock server, so there is no URL to give."""
        return ""

    async def deallocate_server(self, match_id: str):
        """
        Deallocate a game server.

        Args:
            match_id: Match UUID
        """
        if match_id in self._allocated_servers:
            endpoint = self._allocated_servers.pop(match_id)
            logger.info(f"Deallocated server for match {match_id}: {endpoint}")


class HttpServerAllocator:
    """
    Allocates real game servers through a game-server agent.

    The agent owns the game binary and the port range; this service only asks
    for a server and is told where to send players. Keeping the game out of the
    platform is what lets the same matchmaker serve more than one title.
    """

    def __init__(self, agent_url: str, timeout_seconds: float = 10.0):
        self.agent_url = agent_url.rstrip("/")
        self.timeout = timeout_seconds
        self._allocated_servers: Dict[str, str] = {}
        self._server_urls: Dict[str, str] = {}

    async def allocate_server(
        self, match_id: str, region: str, mode: str, players: int = 0
    ) -> str:
        import httpx

        payload = {
            "match_id": match_id,
            "region": region,
            "mode": mode,
            "players": players,
        }

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(f"{self.agent_url}/allocate", json=payload)
            response.raise_for_status()
            data = response.json()

        endpoint = data.get("endpoint")
        if not endpoint:
            raise RuntimeError(f"Agent returned no endpoint for match {match_id}")

        # Browser clients cannot dial host:port over TLS, so the agent also
        # reports the URL to use. Kept separately from the endpoint so native
        # clients are unaffected.
        self._server_urls[match_id] = data.get("url", "")

        self._allocated_servers[match_id] = endpoint
        logger.info(f"Allocated server for match {match_id}: {endpoint}")
        return endpoint

    def server_url(self, match_id: str) -> str:
        """The URL a browser client should connect to, empty if unknown."""
        return self._server_urls.get(match_id, "")

    async def deallocate_server(self, match_id: str):
        if match_id not in self._allocated_servers:
            return

        import httpx

        self._server_urls.pop(match_id, None)
        endpoint = self._allocated_servers.pop(match_id)
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                await client.post(
                    f"{self.agent_url}/release", json={"match_id": match_id}
                )
            logger.info(f"Deallocated server for match {match_id}: {endpoint}")
        except Exception as e:
            # The agent reaps servers that finish on their own, so a failed
            # release is not fatal.
            logger.warning(f"Failed to release server for match {match_id}: {e}")


# Global server allocator instance
ServerAllocator = Union[MockServerAllocator, "HttpServerAllocator"]

_server_allocator: Optional[ServerAllocator] = None


def init_server_allocator(
    base_host: str = "game.example.com",
    base_port: int = 7777,
    agent_url: Optional[str] = None,
):
    """
    Initialize the global server allocator.

    With an agent URL configured, matches get real game servers. Without one it
    falls back to the mock, which hands out endpoints nothing is listening on.
    """
    global _server_allocator

    if agent_url is None:
        agent_url = os.getenv("GAME_SERVER_AGENT_URL", "").strip()

    if agent_url:
        _server_allocator = HttpServerAllocator(agent_url)
        logger.info(f"Server allocator using game server agent at {agent_url}")
    else:
        _server_allocator = MockServerAllocator(base_host, base_port)
        logger.warning(
            "GAME_SERVER_AGENT_URL is not set - allocating mock servers. "
            "Clients will be told to connect to an address that does not exist."
        )


def get_server_allocator() -> ServerAllocator:
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
