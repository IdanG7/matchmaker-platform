"""
Profile management endpoints.
"""

import logging
from fastapi import APIRouter, Depends, HTTPException, status

from models.schemas import ProfileResponse, UpdateProfileRequest, ErrorResponse
from utils.dependencies import get_current_user
from utils.database import get_db_connection

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/me", response_model=ProfileResponse)
async def get_my_profile(current_user: dict = Depends(get_current_user)):
    """
    Get the authenticated user's profile.

    Requires valid JWT token in Authorization header.
    """
    try:
        return ProfileResponse(
            player_id=str(current_user["id"]),
            username=current_user["username"],
            email=current_user["email"],
            region=current_user["region"],
            mmr=current_user["mmr"],
            created_at=current_user["created_at"],
        )
    except Exception as e:
        logger.error(f"Get profile error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch profile",
        )


@router.patch("/me", response_model=ProfileResponse)
async def update_my_profile(
    updates: UpdateProfileRequest,
    current_user: dict = Depends(get_current_user),
    conn=Depends(get_db_connection),
):
    """
    Update the authenticated user's profile.

    Requires valid JWT token in Authorization header.
    Only specified fields will be updated.
    """
    try:
        player_id = current_user["id"]

        # Build dynamic update query based on provided fields
        update_fields = []
        params = []
        param_count = 1

        if updates.region is not None:
            update_fields.append(f"region = ${param_count}")
            params.append(updates.region)
            param_count += 1

        # If no fields to update, return current profile
        if not update_fields:
            return ProfileResponse(
                player_id=str(current_user["id"]),
                username=current_user["username"],
                email=current_user["email"],
                region=current_user["region"],
                mmr=current_user["mmr"],
                created_at=current_user["created_at"],
            )

        # Add player_id to params
        params.append(player_id)

        # Execute update
        query = f"""
            UPDATE game.player
            SET {', '.join(update_fields)}
            WHERE id = ${param_count}
            RETURNING id, username, email, region, mmr, created_at
        """

        result = await conn.fetchrow(query, *params)

        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found"
            )

        logger.info(
            f"Profile updated for user: {current_user['username']} (ID: {player_id})"
        )

        return ProfileResponse(
            player_id=str(result["id"]),
            username=result["username"],
            email=result["email"],
            region=result["region"],
            mmr=result["mmr"],
            created_at=result["created_at"],
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Update profile error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update profile",
        )
