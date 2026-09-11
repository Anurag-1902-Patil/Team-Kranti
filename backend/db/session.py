"""
Async database session factory.
Uses asyncpg for async operations (FastAPI endpoints, Celery tasks via anyio).
Provides both async context manager and FastAPI dependency.
"""

import socket
from urllib.parse import urlparse
import structlog
from collections.abc import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from backend.core.config import get_settings

settings = get_settings()
log = structlog.get_logger(__name__)


def _build_engine():
    db_url = settings.database_url

    # In local development outside Docker, test if PostgreSQL is actually listening
    if "postgresql" in db_url:
        try:
            parsed = urlparse(db_url.replace("+asyncpg", ""))
            host = parsed.hostname or "127.0.0.1"
            if host == "localhost":
                host = "127.0.0.1"
            port = parsed.port or 5432
            probe = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            probe.settimeout(0.1)
            probe.connect((host, port))
            probe.close()
        except Exception:
            log.info(
                "db.storage_mode",
                engine="sqlite",
                database="sih26122.db",
                reason="PostgreSQL not detected on 127.0.0.1:5432; running in standalone local mode with SQLite",
            )
            db_url = "sqlite+aiosqlite:///./sih26122.db"

    if "sqlite" in db_url:
        return create_async_engine(
            db_url,
            connect_args={"check_same_thread": False},
            echo=settings.app_env == "development",
        )

    return create_async_engine(
        db_url,
        pool_pre_ping=True,
        pool_size=10,
        max_overflow=20,
        echo=settings.app_env == "development",
    )


engine = _build_engine()

AsyncSessionFactory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency that yields a database session per request.
    Always closes the session on exit, even on exception.
    """
    async with AsyncSessionFactory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
