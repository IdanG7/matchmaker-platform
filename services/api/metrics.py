"""
Prometheus metrics for API service.

Tracks:
- HTTP request rate and latency
- Error rates by status code
- Active WebSocket connections
- Authentication attempts
"""

from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
from fastapi import Response
import time

# HTTP Metrics
http_requests_total = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status']
)

http_request_duration_seconds = Histogram(
    'http_request_duration_seconds',
    'HTTP request latency in seconds',
    ['method', 'endpoint'],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0)
)

http_requests_in_progress = Gauge(
    'http_requests_in_progress',
    'Number of HTTP requests currently being processed',
    ['method', 'endpoint']
)

# WebSocket Metrics
websocket_connections_active = Gauge(
    'websocket_connections_active',
    'Number of active WebSocket connections',
    ['party_id']
)

websocket_messages_total = Counter(
    'websocket_messages_total',
    'Total WebSocket messages sent/received',
    ['direction', 'type']
)

# Authentication Metrics
auth_attempts_total = Counter(
    'auth_attempts_total',
    'Total authentication attempts',
    ['type', 'result']  # type: login/register/refresh, result: success/failure
)

# Party/Queue Metrics
party_operations_total = Counter(
    'party_operations_total',
    'Total party operations',
    ['operation', 'result']  # operation: create/join/leave/ready, result: success/failure
)

queue_operations_total = Counter(
    'queue_operations_total',
    'Total queue operations',
    ['operation', 'mode']  # operation: enqueue/dequeue
)

active_parties = Gauge(
    'active_parties',
    'Number of active parties'
)

players_in_queue = Gauge(
    'players_in_queue',
    'Number of players currently in matchmaking queue',
    ['mode', 'region']
)

# Database Metrics
db_queries_total = Counter(
    'db_queries_total',
    'Total database queries',
    ['operation', 'table']
)

db_query_duration_seconds = Histogram(
    'db_query_duration_seconds',
    'Database query duration in seconds',
    ['operation', 'table'],
    buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0)
)

# Redis Metrics
redis_operations_total = Counter(
    'redis_operations_total',
    'Total Redis operations',
    ['operation', 'result']  # operation: get/set/delete, result: hit/miss/error
)


def metrics_endpoint():
    """
    Prometheus metrics endpoint.

    Returns:
        Response with Prometheus metrics in text format
    """
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST
    )


class PrometheusMiddleware:
    """
    FastAPI middleware to track HTTP request metrics.

    Automatically records:
    - Request count per endpoint
    - Request duration per endpoint
    - Requests in progress
    """

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        method = scope["method"]
        path = scope["path"]

        # Skip metrics endpoint to avoid recursion
        if path == "/metrics":
            await self.app(scope, receive, send)
            return

        # Normalize path (remove IDs)
        normalized_path = self._normalize_path(path)

        # Track in-progress requests
        http_requests_in_progress.labels(method=method, endpoint=normalized_path).inc()

        start_time = time.time()
        status_code = 500  # Default to error

        async def send_wrapper(message):
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message["status"]
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        finally:
            # Record metrics
            duration = time.time() - start_time
            http_request_duration_seconds.labels(
                method=method,
                endpoint=normalized_path
            ).observe(duration)

            http_requests_total.labels(
                method=method,
                endpoint=normalized_path,
                status=status_code
            ).inc()

            http_requests_in_progress.labels(
                method=method,
                endpoint=normalized_path
            ).dec()

    def _normalize_path(self, path: str) -> str:
        """
        Normalize path to group similar endpoints.

        Examples:
            /v1/party/abc123 → /v1/party/{id}
            /v1/profile/me → /v1/profile/me
        """
        parts = path.split("/")
        normalized_parts = []

        for i, part in enumerate(parts):
            # Check if part looks like a UUID or ID
            if len(part) == 36 and "-" in part:  # UUID
                normalized_parts.append("{id}")
            elif i > 0 and parts[i-1] in ("party", "session", "match") and part != "queue":
                # IDs after party/session/match
                normalized_parts.append("{id}")
            else:
                normalized_parts.append(part)

        return "/".join(normalized_parts)
