"""NATS messaging client for pub/sub and request/reply."""

import os
import logging
import asyncio
import json
from typing import Optional, Callable, Any, Dict
from nats.aio.client import Client as NATS
from nats.errors import TimeoutError as NatsTimeoutError

logger = logging.getLogger(__name__)


class NatsClient:
    """NATS client wrapper for pub/sub and RPC."""

    def __init__(self, url: Optional[str] = None):
        """
        Initialize NATS client.

        Args:
            url: NATS connection URL (default: from NATS_URL env var)
        """
        self.url = url or os.getenv("NATS_URL", "nats://localhost:4222")
        self._client: Optional[NATS] = None

    async def connect(self) -> NATS:
        """
        Connect to NATS server.

        Returns:
            NATS client instance
        """
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

        return self._client

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
            payload = json.dumps(data).encode()
            await self._client.publish(subject, payload)
            logger.debug(f"Published to {subject}: {data}")
        except Exception as e:
            logger.error(f"Failed to publish to {subject}: {e}")
            raise

    async def request(
        self, subject: str, data: Dict[str, Any], timeout: float = 5.0
    ) -> Dict[str, Any]:
        """
        Send a request and wait for response (RPC pattern).

        Args:
            subject: NATS subject to send request to
            data: Request payload as dictionary
            timeout: Request timeout in seconds

        Returns:
            Response payload as dictionary
        """
        if not self._client or not self._client.is_connected:
            await self.connect()

        try:
            payload = json.dumps(data).encode()
            response = await self._client.request(subject, payload, timeout=timeout)
            return json.loads(response.data.decode())
        except NatsTimeoutError:
            logger.error(f"Request to {subject} timed out after {timeout}s")
            raise
        except Exception as e:
            logger.error(f"Request to {subject} failed: {e}")
            raise

    async def subscribe(
        self, subject: str, callback: Callable[[Dict[str, Any]], None], queue: str = ""
    ):
        """
        Subscribe to a NATS subject.

        Args:
            subject: NATS subject pattern to subscribe to
            callback: Async function to handle messages
            queue: Queue group name (for load balancing)
        """
        if not self._client or not self._client.is_connected:
            await self.connect()

        async def message_handler(msg):
            try:
                data = json.loads(msg.data.decode())
                await callback(data)
            except Exception as e:
                logger.error(f"Error handling message on {subject}: {e}")

        try:
            await self._client.subscribe(subject, queue=queue, cb=message_handler)
            logger.info(
                f"Subscribed to {subject}" + (f" (queue: {queue})" if queue else "")
            )
        except Exception as e:
            logger.error(f"Failed to subscribe to {subject}: {e}")
            raise

    async def subscribe_sync(
        self,
        subject: str,
        callback: Callable[[Dict[str, Any]], Dict[str, Any]],
        queue: str = "",
    ):
        """
        Subscribe to a NATS subject with synchronous reply (for RPC handlers).

        Args:
            subject: NATS subject to subscribe to
            callback: Async function that returns response
            queue: Queue group name
        """
        if not self._client or not self._client.is_connected:
            await self.connect()

        async def message_handler(msg):
            try:
                data = json.loads(msg.data.decode())
                response = await callback(data)
                reply_payload = json.dumps(response).encode()
                await self._client.publish(msg.reply, reply_payload)
            except Exception as e:
                logger.error(f"Error handling RPC on {subject}: {e}")
                error_response = json.dumps({"error": str(e)}).encode()
                await self._client.publish(msg.reply, error_response)

        try:
            await self._client.subscribe(subject, queue=queue, cb=message_handler)
            logger.info(
                f"Subscribed to RPC {subject}" + (f" (queue: {queue})" if queue else "")
            )
        except Exception as e:
            logger.error(f"Failed to subscribe to RPC {subject}: {e}")
            raise

    async def health_check(self) -> bool:
        """
        Check if NATS connection is healthy.

        Returns:
            True if connected, False otherwise
        """
        if self._client and self._client.is_connected:
            return True
        return False

    @property
    def client(self) -> NATS:
        """Get NATS client instance."""
        return self._client


# Global NATS client instance
_nats_client: Optional[NatsClient] = None


async def get_nats() -> NATS:
    """
    Get global NATS client instance.

    Returns:
        NATS client
    """
    global _nats_client
    if _nats_client is None:
        _nats_client = NatsClient()
        await _nats_client.connect()
    return _nats_client.client


async def close_nats():
    """Close global NATS connection."""
    global _nats_client
    if _nats_client:
        await _nats_client.disconnect()
        _nats_client = None
