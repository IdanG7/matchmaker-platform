"""
WebSocket endpoints for real-time party updates.
"""

import logging
import json
from typing import Dict, Set
from datetime import datetime
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from fastapi.websockets import WebSocketState

from utils.auth import verify_access_token

logger = logging.getLogger(__name__)
router = APIRouter()


class ConnectionManager:
    """Manages WebSocket connections for party updates."""

    def __init__(self):
        # Map of party_id -> set of WebSocket connections
        self.party_connections: Dict[str, Set[WebSocket]] = {}
        # Map of WebSocket -> player_id for authentication tracking
        self.connection_players: Dict[WebSocket, str] = {}

    async def connect(self, websocket: WebSocket, party_id: str, player_id: str):
        """Register a new WebSocket connection for a party."""
        await websocket.accept()

        if party_id not in self.party_connections:
            self.party_connections[party_id] = set()

        self.party_connections[party_id].add(websocket)
        self.connection_players[websocket] = player_id

        logger.info(f"Player {player_id} connected to party {party_id} WebSocket")

    def disconnect(self, websocket: WebSocket, party_id: str):
        """Remove a WebSocket connection."""
        if party_id in self.party_connections:
            self.party_connections[party_id].discard(websocket)
            if not self.party_connections[party_id]:
                # Clean up empty party subscriptions
                del self.party_connections[party_id]

        player_id = self.connection_players.pop(websocket, "unknown")
        logger.info(f"Player {player_id} disconnected from party {party_id} WebSocket")

    async def broadcast_to_party(
        self, party_id: str, event: str, data: dict, exclude: WebSocket = None
    ):
        """Broadcast a message to all connections subscribed to a party."""
        if party_id not in self.party_connections:
            return

        message = {
            "event": event,
            "data": data,
            "timestamp": datetime.utcnow().isoformat(),
        }

        # Remove dead connections
        dead_connections = set()

        for connection in self.party_connections[party_id]:
            if exclude and connection == exclude:
                continue

            try:
                if connection.client_state == WebSocketState.CONNECTED:
                    await connection.send_json(message)
                else:
                    dead_connections.add(connection)
            except Exception as e:
                logger.error(f"Error broadcasting to connection: {e}", exc_info=True)
                dead_connections.add(connection)

        # Clean up dead connections
        for dead_conn in dead_connections:
            self.disconnect(dead_conn, party_id)


# Global connection manager
manager = ConnectionManager()


@router.websocket("/party/{party_id}")
async def party_websocket(websocket: WebSocket, party_id: str, token: str = Query(...)):
    """
    WebSocket endpoint for real-time party updates.

    Query parameters:
        token: JWT access token for authentication

    Events sent to client:
        - member_joined: When a player joins the party
        - member_left: When a player leaves the party
        - member_ready: When a player toggles ready status
        - party_updated: When party state changes
        - queue_entered: When party enters matchmaking queue
        - queue_left: When party leaves matchmaking queue
        - match_found: When a match is found
    """
    # Authenticate the connection
    payload = verify_access_token(token)
    if not payload:
        await websocket.close(code=4001, reason="Invalid or expired token")
        return

    player_id = payload.get("sub")
    if not player_id:
        await websocket.close(code=4001, reason="Invalid token payload")
        return

    # Verify player is a member of this party
    from utils.database import get_db_pool

    pool = await get_db_pool()
    async with pool.acquire() as conn:
        is_member = await conn.fetchval(
            """
            SELECT EXISTS(
                SELECT 1 FROM game.party_member
                WHERE party_id = $1 AND player_id = $2
            )
            """,
            party_id,
            player_id,
        )

        if not is_member:
            await websocket.close(code=4003, reason="Not a member of this party")
            return

    try:
        await manager.connect(websocket, party_id, player_id)

        # Send initial connection success message
        await websocket.send_json(
            {
                "event": "connected",
                "data": {"party_id": party_id, "player_id": player_id},
                "timestamp": datetime.utcnow().isoformat(),
            }
        )

        # Keep connection alive and handle incoming messages
        while True:
            try:
                # Receive messages from client (e.g., heartbeat/ping)
                data = await websocket.receive_text()
                message = json.loads(data)

                # Handle ping/pong for keepalive
                if message.get("type") == "ping":
                    await websocket.send_json(
                        {
                            "event": "pong",
                            "data": {},
                            "timestamp": datetime.utcnow().isoformat(),
                        }
                    )

            except json.JSONDecodeError:
                logger.warning(f"Invalid JSON from player {player_id}")
            except WebSocketDisconnect:
                break

    except Exception as e:
        logger.error(f"WebSocket error for player {player_id}: {e}", exc_info=True)
    finally:
        manager.disconnect(websocket, party_id)


# Helper functions to be called from party routes


async def broadcast_member_joined(party_id: str, player_id: str, username: str):
    """Broadcast when a new member joins the party."""
    await manager.broadcast_to_party(
        party_id,
        "member_joined",
        {"party_id": party_id, "player_id": player_id, "username": username},
    )


async def broadcast_member_left(party_id: str, player_id: str, username: str):
    """Broadcast when a member leaves the party."""
    await manager.broadcast_to_party(
        party_id,
        "member_left",
        {"party_id": party_id, "player_id": player_id, "username": username},
    )


async def broadcast_member_ready(
    party_id: str, player_id: str, username: str, ready: bool
):
    """Broadcast when a member toggles ready status."""
    await manager.broadcast_to_party(
        party_id,
        "member_ready",
        {
            "party_id": party_id,
            "player_id": player_id,
            "username": username,
            "ready": ready,
        },
    )


async def broadcast_party_updated(party_id: str, party_data: dict):
    """Broadcast general party state updates."""
    await manager.broadcast_to_party(
        party_id, "party_updated", {"party_id": party_id, "party": party_data}
    )


async def broadcast_queue_entered(party_id: str, mode: str, team_size: int):
    """Broadcast when party enters matchmaking queue."""
    await manager.broadcast_to_party(
        party_id,
        "queue_entered",
        {"party_id": party_id, "mode": mode, "team_size": team_size},
    )


async def broadcast_queue_left(party_id: str):
    """Broadcast when party leaves matchmaking queue."""
    await manager.broadcast_to_party(party_id, "queue_left", {"party_id": party_id})


async def broadcast_match_found(party_id: str, match_data: dict):
    """Broadcast when a match is found."""
    await manager.broadcast_to_party(
        party_id, "match_found", {"party_id": party_id, "match": match_data}
    )
