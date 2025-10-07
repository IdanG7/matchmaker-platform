"""
MMR Calculator - Simple Elo-based MMR calculation.
"""

import logging
from typing import List, Tuple

logger = logging.getLogger(__name__)

# Default K-factor for Elo rating
DEFAULT_K_FACTOR = 32

# Base MMR for new players
BASE_MMR = 1500


def calculate_expected_score(rating_a: int, rating_b: int) -> float:
    """
    Calculate expected score for player A vs player B using Elo formula.

    Args:
        rating_a: Player A's current rating
        rating_b: Player B's current rating

    Returns:
        Expected score (probability) for player A (0.0 to 1.0)
    """
    return 1 / (1 + 10 ** ((rating_b - rating_a) / 400))


def calculate_mmr_change(
    player_rating: int,
    opponent_avg_rating: int,
    result: str,
    k_factor: int = DEFAULT_K_FACTOR,
) -> int:
    """
    Calculate MMR change for a player using simplified Elo.

    Args:
        player_rating: Player's current MMR
        opponent_avg_rating: Average MMR of opposing team
        result: Match result ('win', 'loss', 'draw')
        k_factor: K-factor for rating adjustment (default 32)

    Returns:
        MMR change (positive for gain, negative for loss)
    """
    # Actual score: 1.0 for win, 0.5 for draw, 0.0 for loss
    score_map = {"win": 1.0, "draw": 0.5, "loss": 0.0}
    actual_score = score_map.get(result, 0.0)

    # Expected score based on ratings
    expected_score = calculate_expected_score(player_rating, opponent_avg_rating)

    # MMR change = K * (actual - expected)
    mmr_change = int(k_factor * (actual_score - expected_score))

    return mmr_change


def calculate_team_mmr_changes(
    team_ratings: List[int],
    opponent_avg_rating: int,
    won: bool,
    k_factor: int = DEFAULT_K_FACTOR,
) -> List[int]:
    """
    Calculate MMR changes for all players in a team.

    Args:
        team_ratings: List of current ratings for team members
        opponent_avg_rating: Average rating of opposing team
        won: True if team won, False if lost
        k_factor: K-factor for rating adjustment

    Returns:
        List of MMR changes for each player
    """
    result = "win" if won else "loss"

    return [
        calculate_mmr_change(rating, opponent_avg_rating, result, k_factor)
        for rating in team_ratings
    ]


def get_season_id() -> str:
    """
    Get current season identifier.

    In production, this would be configured or calculated from calendar.
    For now, returns a static season.

    Returns:
        Season identifier (e.g., "2025-Q1")
    """
    # TODO: Calculate based on current date or config
    return "2025-Q1"
