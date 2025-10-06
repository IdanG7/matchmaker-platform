"""
Rate limiting middleware using Redis.
"""

import time
import logging
from typing import Optional
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse
import redis.asyncio as redis

from config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Rate limiting middleware that uses Redis to track request counts.

    Implements a sliding window rate limiter per IP address.
    """

    def __init__(self, app):
        super().__init__(app)
        self.redis_client: Optional[redis.Redis] = None
        self.rate_limit = settings.rate_limit_per_minute
        self.window_seconds = 60

    async def dispatch(self, request: Request, call_next):
        """Process the request with rate limiting."""

        # Skip rate limiting for health check endpoints
        if request.url.path in ["/health", "/docs", "/redoc", "/openapi.json"]:
            return await call_next(request)

        # Initialize Redis client if needed
        if self.redis_client is None:
            try:
                self.redis_client = redis.from_url(
                    settings.redis_url,
                    decode_responses=True,
                    max_connections=settings.redis_max_connections,
                )
            except Exception as e:
                logger.error(f"Failed to connect to Redis for rate limiting: {e}")
                # Continue without rate limiting if Redis is unavailable
                return await call_next(request)

        # Get client identifier (IP address)
        client_ip = request.client.host
        key = f"rate_limit:{client_ip}"

        try:
            # Get current count
            current_count = await self.redis_client.get(key)

            if current_count is None:
                # First request in this window
                await self.redis_client.setex(key, self.window_seconds, 1)
            else:
                count = int(current_count)
                if count >= self.rate_limit:
                    # Rate limit exceeded
                    return JSONResponse(
                        status_code=429,
                        content={
                            "error": "rate_limit_exceeded",
                            "message": f"Rate limit of {self.rate_limit} requests per minute exceeded",
                        },
                    )
                # Increment counter
                await self.redis_client.incr(key)

        except Exception as e:
            logger.error(f"Rate limiting error: {e}")
            # Continue without rate limiting if Redis operation fails

        # Process the request
        response = await call_next(request)
        return response
