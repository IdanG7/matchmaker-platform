"""
Main FastAPI application entry point.
"""

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import get_settings
from routes import auth, profile, party, websocket, session, leaderboard
from middleware.rate_limit import RateLimitMiddleware
from utils.database import db
from utils import redis_cache, nats_events, session_manager
from utils.nats_client import SimpleNatsClient
from consumers.match_consumer import start_match_consumer

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    logger.info(f"Starting {settings.service_name} service")

    # Startup - Initialize database connection pool
    try:
        await db.connect()
        logger.info("Database connection pool initialized")
    except Exception as e:
        logger.error(f"Failed to connect to database: {e}")
        raise

    # Startup - Initialize Redis connection
    try:
        from redis import Redis

        redis_client = Redis.from_url(
            settings.redis_url,
            decode_responses=True,
            socket_timeout=5,
            socket_connect_timeout=5,
        )
        redis_client.ping()
        redis_cache.init_redis(redis_client)
        logger.info("Redis connection initialized")
    except Exception as e:
        logger.warning(f"Failed to connect to Redis: {e}. Caching disabled.")

    # Startup - Initialize NATS connection
    nats_client = None
    try:
        nats_client = SimpleNatsClient(settings.nats_url)
        await nats_client.connect()
        nats_events.init_nats(nats_client)
        logger.info("NATS connection initialized")

        # Start match consumer for session allocation
        await start_match_consumer(nats_client)
        logger.info("Match consumer started")
    except Exception as e:
        logger.warning(f"Failed to connect to NATS: {e}. Queue events disabled.")

    # Startup - Initialize session manager
    try:
        session_manager.init_session_secret(settings.jwt_secret_key)
        session_manager.init_server_allocator()
        logger.info("Session manager initialized")
    except Exception as e:
        logger.error(f"Failed to initialize session manager: {e}")
        raise

    yield

    # Shutdown - Close NATS connection
    if nats_client and nats_client.is_connected():
        try:
            await nats_client.disconnect()
            logger.info("NATS connection closed")
        except Exception as e:
            logger.error(f"Error closing NATS connection: {e}")

    # Shutdown - Close database connection pool
    logger.info(f"Shutting down {settings.service_name} service")
    try:
        await db.disconnect()
        logger.info("Database connection pool closed")
    except Exception as e:
        logger.error(f"Error closing database connection: {e}")


# Create FastAPI app
app = FastAPI(
    title="Game Services API",
    description="REST API for matchmaking and game services",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Rate limiting middleware
if settings.rate_limit_enabled:
    app.add_middleware(RateLimitMiddleware)

# Include routers
app.include_router(auth.router, prefix="/v1/auth", tags=["auth"])
app.include_router(profile.router, prefix="/v1/profile", tags=["profile"])
app.include_router(party.router, prefix="/v1/party", tags=["party"])
app.include_router(websocket.router, prefix="/v1/ws", tags=["websocket"])
app.include_router(session.router, prefix="/v1/session", tags=["session"])
app.include_router(leaderboard.router, prefix="/v1", tags=["leaderboard"])


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": settings.service_name,
        "environment": settings.environment,
    }


@app.get("/")
async def root():
    """Root endpoint."""
    return {"service": "Game Services API", "version": "1.0.0", "docs": "/docs"}
