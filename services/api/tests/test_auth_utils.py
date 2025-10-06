"""
Unit tests for authentication utilities.
"""

from datetime import timedelta

from utils.auth import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_token,
    verify_access_token,
    verify_refresh_token,
)


def test_password_hashing():
    """Test password hashing and verification."""
    password = "my_secure_password_123"

    # Hash password
    hashed = hash_password(password)

    # Verify it's different from plain text
    assert hashed != password

    # Verify correct password
    assert verify_password(password, hashed) is True

    # Verify incorrect password
    assert verify_password("wrong_password", hashed) is False


def test_password_hash_uniqueness():
    """Test that hashing the same password twice produces different hashes."""
    password = "my_password"
    hash1 = hash_password(password)
    hash2 = hash_password(password)

    # Hashes should be different (bcrypt uses salt)
    assert hash1 != hash2

    # But both should verify correctly
    assert verify_password(password, hash1) is True
    assert verify_password(password, hash2) is True


def test_create_access_token():
    """Test access token creation."""
    data = {"sub": "user123", "username": "testuser"}

    token = create_access_token(data)

    # Token should be a non-empty string
    assert isinstance(token, str)
    assert len(token) > 0

    # Decode and verify payload
    payload = decode_token(token)
    assert payload is not None
    assert payload["sub"] == "user123"
    assert payload["username"] == "testuser"
    assert payload["type"] == "access"
    assert "exp" in payload


def test_create_refresh_token():
    """Test refresh token creation."""
    data = {"sub": "user123", "username": "testuser"}

    token = create_refresh_token(data)

    # Token should be a non-empty string
    assert isinstance(token, str)
    assert len(token) > 0

    # Decode and verify payload
    payload = decode_token(token)
    assert payload is not None
    assert payload["sub"] == "user123"
    assert payload["username"] == "testuser"
    assert payload["type"] == "refresh"
    assert "exp" in payload


def test_verify_access_token():
    """Test access token verification."""
    data = {"sub": "user123", "username": "testuser"}

    # Create access token
    access_token = create_access_token(data)

    # Verify it
    payload = verify_access_token(access_token)
    assert payload is not None
    assert payload["type"] == "access"

    # Create refresh token
    refresh_token = create_refresh_token(data)

    # Should not verify as access token
    payload = verify_access_token(refresh_token)
    assert payload is None


def test_verify_refresh_token():
    """Test refresh token verification."""
    data = {"sub": "user123", "username": "testuser"}

    # Create refresh token
    refresh_token = create_refresh_token(data)

    # Verify it
    payload = verify_refresh_token(refresh_token)
    assert payload is not None
    assert payload["type"] == "refresh"

    # Create access token
    access_token = create_access_token(data)

    # Should not verify as refresh token
    payload = verify_refresh_token(access_token)
    assert payload is None


def test_invalid_token():
    """Test decoding invalid tokens."""
    # Invalid token format
    payload = decode_token("invalid.token.format")
    assert payload is None

    # Completely invalid string
    payload = decode_token("not_a_token")
    assert payload is None


def test_token_expiration():
    """Test that tokens respect expiration time."""
    data = {"sub": "user123"}

    # Create token with very short expiration (negative time = already expired)
    expired_token = create_access_token(data, expires_delta=timedelta(seconds=-10))

    # Should not verify as expired
    payload = verify_access_token(expired_token)
    assert payload is None
