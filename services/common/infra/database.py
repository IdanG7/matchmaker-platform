"""PostgreSQL database connection and session management."""

import os
import logging
from typing import Optional, Generator
from contextlib import contextmanager
from sqlalchemy import create_engine, event, pool
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.engine import Engine

logger = logging.getLogger(__name__)

# Base class for SQLAlchemy models
Base = declarative_base()


class Database:
    """Database connection manager."""

    def __init__(self, url: Optional[str] = None):
        """
        Initialize database connection.

        Args:
            url: Database connection URL (default: from DATABASE_URL env var)
        """
        self.url = url or os.getenv(
            "DATABASE_URL", "postgresql://postgres:password@localhost:5432/game"
        )
        self._engine: Optional[Engine] = None
        self._session_factory: Optional[sessionmaker] = None

    def connect(self):
        """Create database engine and session factory."""
        if self._engine is None:
            try:
                self._engine = create_engine(
                    self.url,
                    poolclass=pool.QueuePool,
                    pool_size=20,
                    max_overflow=40,
                    pool_pre_ping=True,
                    pool_recycle=3600,
                    echo=False,
                )

                # Set schema search path
                @event.listens_for(self._engine, "connect", insert=True)
                def set_search_path(dbapi_conn, connection_record):
                    cursor = dbapi_conn.cursor()
                    cursor.execute("SET search_path TO game, public")
                    cursor.close()

                self._session_factory = sessionmaker(
                    autocommit=False,
                    autoflush=False,
                    bind=self._engine,
                )

                # Test connection
                with self._engine.connect() as conn:
                    conn.execute("SELECT 1")

                logger.info(f"Connected to database at {self.url}")
            except Exception as e:
                logger.error(f"Failed to connect to database: {e}")
                raise

    def disconnect(self):
        """Close database connections."""
        if self._engine:
            self._engine.dispose()
            self._engine = None
            self._session_factory = None
            logger.info("Disconnected from database")

    @contextmanager
    def session(self) -> Generator[Session, None, None]:
        """
        Context manager for database sessions.

        Yields:
            SQLAlchemy session

        Example:
            with db.session() as session:
                user = session.query(Player).first()
        """
        if self._session_factory is None:
            self.connect()

        session = self._session_factory()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def health_check(self) -> bool:
        """
        Check if database is healthy.

        Returns:
            True if database responds, False otherwise
        """
        try:
            if self._engine:
                with self._engine.connect() as conn:
                    conn.execute("SELECT 1")
                return True
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
        return False

    @property
    def engine(self) -> Engine:
        """Get SQLAlchemy engine."""
        if self._engine is None:
            self.connect()
        return self._engine


# Global database instance
_database: Optional[Database] = None


def get_db() -> Database:
    """
    Get global database instance.

    Returns:
        Database instance
    """
    global _database
    if _database is None:
        _database = Database()
        _database.connect()
    return _database


def close_db():
    """Close global database connection."""
    global _database
    if _database:
        _database.disconnect()
        _database = None


# Dependency for FastAPI
def get_db_session() -> Generator[Session, None, None]:
    """
    FastAPI dependency for database sessions.

    Yields:
        SQLAlchemy session

    Example:
        @app.get("/users")
        def get_users(db: Session = Depends(get_db_session)):
            return db.query(User).all()
    """
    db = get_db()
    with db.session() as session:
        yield session
