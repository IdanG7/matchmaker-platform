"""
Pydantic schemas for request and response models.
"""

from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, EmailStr, Field, validator


# ============================================================================
# Auth Schemas
# ============================================================================


class RegisterRequest(BaseModel):
    """User registration request."""

    username: str = Field(..., min_length=3, max_length=32, pattern="^[a-zA-Z0-9_-]+$")
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)
    region: str = Field(default="us-west", pattern="^[a-z]{2}-[a-z]+$")

    @validator("username")
    def username_alphanumeric(cls, v):
        """Validate username is alphanumeric."""
        if not v.replace("-", "").replace("_", "").isalnum():
            raise ValueError(
                "Username must be alphanumeric with hyphens or underscores"
            )
        return v


class LoginRequest(BaseModel):
    """User login request."""

    username: str = Field(..., min_length=3, max_length=32)
    password: str = Field(..., min_length=8, max_length=128)


class RefreshTokenRequest(BaseModel):
    """Token refresh request."""

    refresh_token: str


class TokenResponse(BaseModel):
    """Token response for login and refresh."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds


class AuthResponse(BaseModel):
    """Authentication response with user info and tokens."""

    player_id: str
    username: str
    email: str
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


# ============================================================================
# Profile Schemas
# ============================================================================


class ProfileResponse(BaseModel):
    """Player profile response."""

    player_id: str
    username: str
    email: str
    region: str
    mmr: int
    created_at: datetime

    class Config:
        from_attributes = True


class UpdateProfileRequest(BaseModel):
    """Update profile request."""

    region: Optional[str] = Field(None, pattern="^[a-z]{2}-[a-z]+$")
    # Add more updatable fields as needed

    class Config:
        # Allow partial updates
        extra = "forbid"


# ============================================================================
# Party Schemas
# ============================================================================


class PartyMemberResponse(BaseModel):
    """Party member information."""

    player_id: str
    username: str
    joined_at: datetime
    ready: bool
    role: Optional[str] = None

    class Config:
        from_attributes = True


class CreatePartyRequest(BaseModel):
    """Create party request."""

    max_size: int = Field(default=5, ge=2, le=10)
    region: Optional[str] = Field(None, pattern="^[a-z]{2}-[a-z]+$")


class PartyResponse(BaseModel):
    """Party information response."""

    id: str
    leader_id: str
    created_at: datetime
    updated_at: datetime
    region: str
    size: int
    max_size: int
    status: str  # idle, queueing, ready, in_match, disbanded
    queue_mode: Optional[str] = None
    team_size: Optional[int] = None
    avg_mmr: Optional[int] = None
    members: List[PartyMemberResponse] = []

    class Config:
        from_attributes = True


class InvitePlayerRequest(BaseModel):
    """Invite player to party request."""

    player_id: str = Field(..., description="ID of player to invite")


class QueueRequest(BaseModel):
    """Enter matchmaking queue request."""

    mode: str = Field(..., pattern="^[a-z0-9_]+$", description="Game mode")
    team_size: int = Field(..., ge=1, le=10, description="Players per team")


class ReadyCheckResponse(BaseModel):
    """Ready check status response."""

    party_id: str
    ready_count: int
    total_count: int
    all_ready: bool
    not_ready_players: List[str] = []


# ============================================================================
# WebSocket Event Schemas
# ============================================================================


class WSEventType:
    """WebSocket event type constants."""

    PARTY_UPDATED = "party_updated"
    MEMBER_JOINED = "member_joined"
    MEMBER_LEFT = "member_left"
    MEMBER_READY = "member_ready"
    MATCH_FOUND = "match_found"
    QUEUE_ENTERED = "queue_entered"
    QUEUE_LEFT = "queue_left"
    ERROR = "error"


class WebSocketMessage(BaseModel):
    """WebSocket message format."""

    event: str
    data: dict
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# ============================================================================
# Session Schemas
# ============================================================================


class SessionStatus:
    """Session status constants."""

    ALLOCATING = "allocating"
    ACTIVE = "active"
    ENDED = "ended"
    CANCELLED = "cancelled"


class SessionResponse(BaseModel):
    """Session details response."""

    match_id: str
    status: str
    server_endpoint: Optional[str] = None
    server_token: Optional[str] = None
    created_at: datetime
    started_at: Optional[datetime] = None
    mode: str
    region: str
    teams: List[List[str]] = []
    avg_mmr: Optional[int] = None


class MatchResultRequest(BaseModel):
    """Match result submission from game server."""

    match_id: str
    winner_team: int = Field(..., ge=0, description="Winning team index (0-based)")
    player_stats: dict = Field(default_factory=dict, description="Player stats by player_id")
    duration_seconds: int = Field(..., gt=0, description="Match duration in seconds")
    metadata: Optional[dict] = None


class HeartbeatRequest(BaseModel):
    """Game server heartbeat."""

    match_id: str
    server_id: str
    active_players: int = Field(..., ge=0)


# ============================================================================
# Error Schemas
# ============================================================================


class ErrorResponse(BaseModel):
    """Standard error response."""

    error: str
    message: str
    details: Optional[dict] = None
