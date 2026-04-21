"""Synchronous database session factory for management tasks."""

from __future__ import annotations

import logging
from typing import Any, Dict

from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker

from app.core.config import settings

logger = logging.getLogger(__name__)


def _resolve_sync_driver(async_driver: str) -> str:
    """Map async SQLAlchemy drivers to their synchronous counterparts."""
    driver_map = {
        "sqlite+aiosqlite": "sqlite",
        "postgresql+asyncpg": "postgresql+psycopg2",
        "postgresql+psycopg": "postgresql+psycopg2",
        "mysql+aiomysql": "mysql+pymysql",
        "mysql+asyncmy": "mysql+pymysql",
    }
    return driver_map.get(async_driver, async_driver)


def _build_sync_database_url(database_url: str) -> str:
    """Convert the configured async database URL into a synchronous URL."""
    url = make_url(database_url)
    sync_driver = _resolve_sync_driver(url.drivername)
    if sync_driver != url.drivername:
        url = url.set(drivername=sync_driver)
    return str(url)


SYNC_DATABASE_URL = _build_sync_database_url(settings.database_url)

connect_args: Dict[str, Any] = {}
if SYNC_DATABASE_URL.startswith("sqlite"):
    # Mirror async SQLite configuration: allow usage across threads.
    connect_args["check_same_thread"] = False

engine = create_engine(
    SYNC_DATABASE_URL,
    future=True,
    pool_pre_ping=True,
    connect_args=connect_args,
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)

logger.debug("Synchronous SessionLocal configured for seeding tasks", extra={"url": SYNC_DATABASE_URL})
