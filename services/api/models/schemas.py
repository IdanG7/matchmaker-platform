"""
Pydantic schemas for request and response models.
"""

from typing import Optional
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
# Error Schemas
# ============================================================================


class ErrorResponse(BaseModel):
    """Standard error response."""

    error: str
    message: str
    details: Optional[dict] = None
