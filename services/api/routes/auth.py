"""
Authentication endpoints: register, login, refresh.
"""
import logging
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from asyncpg import UniqueViolationError

from models.schemas import (
    RegisterRequest,
    LoginRequest,
    RefreshTokenRequest,
    AuthResponse,
    TokenResponse,
    ErrorResponse
)
from utils.auth import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    verify_refresh_token
)
from utils.database import get_db_connection
from config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()
router = APIRouter()


@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
async def register(
    request: RegisterRequest,
    conn = Depends(get_db_connection)
):
    """
    Register a new user account.

    Creates a new player with hashed password and returns auth tokens.
    """
    try:
        # Hash the password
        password_hash = hash_password(request.password)

        # Insert into database
        result = await conn.fetchrow(
            """
            INSERT INTO game.player (username, email, password_hash, region)
            VALUES ($1, $2, $3, $4)
            RETURNING id, username, email, region, mmr, created_at
            """,
            request.username,
            request.email,
            password_hash,
            request.region
        )

        player_id = str(result['id'])

        # Create tokens
        token_data = {"sub": player_id, "username": result['username']}
        access_token = create_access_token(token_data)
        refresh_token = create_refresh_token(token_data)

        logger.info(f"User registered: {request.username} (ID: {player_id})")

        return AuthResponse(
            player_id=player_id,
            username=result['username'],
            email=result['email'],
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=settings.jwt_access_token_expire_minutes * 60
        )

    except UniqueViolationError as e:
        # Username or email already exists
        if "username" in str(e):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already taken"
            )
        elif "email" in str(e):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Registration failed"
            )
    except Exception as e:
        logger.error(f"Registration error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration failed"
        )


@router.post("/login", response_model=AuthResponse)
async def login(
    request: LoginRequest,
    conn = Depends(get_db_connection)
):
    """
    Login with username and password.

    Returns auth tokens on success.
    """
    try:
        # Fetch user from database
        user = await conn.fetchrow(
            """
            SELECT id, username, email, password_hash, region, mmr, created_at
            FROM game.player
            WHERE username = $1
            """,
            request.username
        )

        # Verify user exists and password is correct
        if not user or not verify_password(request.password, user['password_hash']):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid username or password"
            )

        player_id = str(user['id'])

        # Create tokens
        token_data = {"sub": player_id, "username": user['username']}
        access_token = create_access_token(token_data)
        refresh_token = create_refresh_token(token_data)

        logger.info(f"User logged in: {request.username} (ID: {player_id})")

        return AuthResponse(
            player_id=player_id,
            username=user['username'],
            email=user['email'],
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=settings.jwt_access_token_expire_minutes * 60
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Login failed"
        )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    request: RefreshTokenRequest,
    conn = Depends(get_db_connection)
):
    """
    Refresh access token using a valid refresh token.

    Returns new access and refresh tokens.
    """
    try:
        # Verify refresh token
        payload = verify_refresh_token(request.refresh_token)
        if not payload:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired refresh token"
            )

        player_id = payload.get("sub")
        username = payload.get("username")

        if not player_id or not username:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload"
            )

        # Verify user still exists
        user = await conn.fetchrow(
            "SELECT id FROM game.player WHERE id = $1",
            player_id
        )

        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found"
            )

        # Create new tokens
        token_data = {"sub": player_id, "username": username}
        access_token = create_access_token(token_data)
        new_refresh_token = create_refresh_token(token_data)

        logger.info(f"Token refreshed for user: {username} (ID: {player_id})")

        return TokenResponse(
            access_token=access_token,
            refresh_token=new_refresh_token,
            token_type="bearer",
            expires_in=settings.jwt_access_token_expire_minutes * 60
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Token refresh error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Token refresh failed"
        )
