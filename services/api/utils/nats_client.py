"""
Simple NATS client wrapper for the API service.
"""

import logging
import json
from typing import Optional, Dict, Any
from nats.aio.client import Client as NATS

logger = logging.getLogger(__name__)


class SimpleNatsClient:
    """Simple NATS client for publishing events."""

    def __init__(self, url: str):
        """
        Initialize NATS client.

        Args:
            url: NATS connection URL
        """
        self.url = url
        self._client: Optional[NATS] = None

    async def connect(self):
        """Connect to NATS server."""
        if self._client is None or not self._client.is_connected:
            try:
                self._client = NATS()
                await self._client.connect(
                    servers=[self.url],
                    max_reconnect_attempts=10,
                    reconnect_time_wait=2,
                )
                logger.info(f"Connected to NATS at {self.url}")
            except Exception as e:
                logger.error(f"Failed to connect to NATS: {e}")
                raise

    async def disconnect(self):
        """Close NATS connection."""
        if self._client and self._client.is_connected:
            await self._client.drain()
            await self._client.close()
            self._client = None
            logger.info("Disconnected from NATS")

    async def publish(self, subject: str, data: Dict[str, Any]):
        """
        Publish a message to a NATS subject.

        Args:
            subject: NATS subject to publish to
            data: Dictionary to serialize as JSON
        """
        if not self._client or not self._client.is_connected:
            await self.connect()

        try:
            payload = json.dumps(data, default=str).encode()
            await self._client.publish(subject, payload)
            logger.debug(f"Published to {subject}: {data}")
        except Exception as e:
            logger.error(f"Failed to publish to {subject}: {e}")
            raise

    def is_connected(self) -> bool:
        """Check if NATS is connected."""
        return self._client is not None and self._client.is_connected
