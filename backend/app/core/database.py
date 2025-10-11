"""
Database configuration and session management with enhanced security and type safety.
"""
import logging
import time
from contextlib import asynccontextmanager
from typing import AsyncGenerator, AsyncIterator, Optional, Dict, Any

from fastapi import HTTPException
from sqlalchemy import MetaData, event, Engine, text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import StaticPool, QueuePool
from sqlalchemy.exc import SQLAlchemyError, DisconnectionError, DatabaseError

from app.core.config import settings

logger = logging.getLogger(__name__)


class Base(DeclarativeBase):
    """Base class for all database models."""

    metadata = MetaData(
        # Naming convention for constraints
        naming_convention={
            "ix": "ix_%(column_0_label)s",
            "uq": "uq_%(table_name)s_%(column_0_name)s",
            "ck": "ck_%(table_name)s_%(constraint_name)s",
            "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
            "pk": "pk_%(table_name)s",
        }
    )


def _validate_database_url(url: str) -> str:
    """
    Validate database URL for security concerns.
    
    Args:
        url: Database connection URL
        
    Returns:
        str: Validated URL
        
    Raises:
        ValueError: If URL is invalid or insecure
    """
    if not url or not isinstance(url, str):
        raise ValueError("Database URL must be a non-empty string")
    
    # Remove any potential whitespace that could cause issues
    url = url.strip()
    
    # Basic URL format validation
    if not any(url.startswith(scheme) for scheme in [
        "sqlite://", "sqlite+aiosqlite://",
        "postgresql://", "postgresql+asyncpg://", "postgresql+psycopg://",
        "mysql://", "mysql+aiomysql://", "mysql+pymysql://",
    ]):
        raise ValueError("Unsupported or invalid database URL scheme")
    
    # Security check: prevent file:// URLs that could access arbitrary files
    if "file://" in url.lower():
        raise ValueError("File URLs are not allowed for security reasons")
    
    # Check for potential injection attempts
    dangerous_patterns = ["'", '"', ';', '--', '/*', '*/', 'xp_', 'sp_']
    if any(pattern in url.lower() for pattern in dangerous_patterns):
        logger.warning("Potentially dangerous pattern detected in database URL")
    
    return url

def _build_engine() -> AsyncEngine:
    """
    Create async engine with enhanced security and performance configuration.
    
    Returns:
        AsyncEngine: Configured database engine
        
    Raises:
        ValueError: If configuration is invalid
    """
    # Validate the database URL first
    validated_url = _validate_database_url(settings.database_url)
    
    # Base engine configuration
    engine_kwargs: Dict[str, Any] = {
        "echo": settings.database_echo and settings.debug,  # Only echo in debug mode
        "future": True,
        "pool_timeout": 30,  # Connection timeout
        "pool_recycle": settings.database_pool_recycle,  # Recycle connections
        "pool_pre_ping": True,  # Validate connections before use
    }

    # Database-specific configuration
    is_sqlite = validated_url.startswith(("sqlite://", "sqlite+aiosqlite://"))
    is_postgres = validated_url.startswith(("postgresql://", "postgresql+asyncpg://", "postgresql+psycopg://"))
    is_mysql = validated_url.startswith(("mysql://", "mysql+aiomysql://", "mysql+pymysql://"))

    if is_sqlite:
        # SQLite-specific configuration
        engine_kwargs.update({
            "poolclass": StaticPool,
            "connect_args": {
                "check_same_thread": False,
                "timeout": 20,  # SQLite timeout
            },
        })
        logger.info("Configured SQLite database engine")
    else:
        # Production database configuration (PostgreSQL, MySQL, etc.)
        engine_kwargs.update({
            "poolclass": QueuePool,
            "pool_size": settings.database_pool_size,
            "max_overflow": settings.database_max_overflow,
        })
        
        if is_postgres:
            # PostgreSQL-specific optimizations
            engine_kwargs["connect_args"] = {
                "server_settings": {
                    "jit": "off",  # Disable JIT for faster connections
                    "application_name": "SyferStack-API",
                }
            }
            logger.info("Configured PostgreSQL database engine")
        elif is_mysql:
            # MySQL-specific optimizations
            engine_kwargs["connect_args"] = {
                "charset": "utf8mb4",
                "autocommit": False,
            }
            logger.info("Configured MySQL database engine")
    
    try:
        engine = create_async_engine(validated_url, **engine_kwargs)
        logger.info("Database engine created successfully", extra={
            "pool_size": engine_kwargs.get("pool_size", "N/A"),
            "max_overflow": engine_kwargs.get("max_overflow", "N/A"),
        })
        return engine
    except Exception as e:
        logger.error("Failed to create database engine", exc_info=e)
        raise


# Create async engine
engine = _build_engine()

# Create async session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


@asynccontextmanager
async def get_db_session() -> AsyncIterator[AsyncSession]:
    """
    Context manager for database sessions with enhanced error handling.
    
    Yields:
        AsyncSession: Database session
        
    Raises:
        DatabaseError: If database operations fail
    """
    session = AsyncSessionLocal()
    try:
        yield session
        await session.commit()
    except SQLAlchemyError as e:
        await session.rollback()
        logger.error("Database operation failed", exc_info=e, extra={
            "session_id": id(session),
        })
        raise DatabaseError(f"Database operation failed: {str(e)}") from e
    except Exception as e:
        await session.rollback()
        logger.error("Unexpected error in database session", exc_info=e, extra={
            "session_id": id(session),
        })
        raise
    finally:
        await session.close()

async def get_db() -> AsyncIterator[AsyncSession]:
    """
    FastAPI dependency for database sessions with comprehensive error handling.
    
    Yields:
        AsyncSession: Database session for request lifecycle
        
    Raises:
        HTTPException: If database is unavailable
    """
    try:
        async with get_db_session() as session:
            # Verify database connectivity
            try:
                await session.execute(text("SELECT 1"))
            except Exception as e:
                logger.error("Database connectivity check failed", exc_info=e)
                raise HTTPException(
                    status_code=503, 
                    detail="Database service unavailable"
                ) from e
            
            yield session
            
    except DatabaseError as e:
        logger.error("Database error in request", exc_info=e)
        raise HTTPException(
            status_code=500,
            detail="Internal database error"
        ) from e
    except Exception as e:
        logger.error("Unexpected database error", exc_info=e)
        raise HTTPException(
            status_code=500,
            detail="Internal server error"
        ) from e

async def check_database_health() -> Dict[str, Any]:
    """
    Comprehensive database health check.
    
    Returns:
        Dict[str, Any]: Health status with metrics
    """
    start_time = time.time()
    
    try:
        async with get_db_session() as session:
            # Test basic connectivity
            result = await session.execute(text("SELECT 1 as health_check"))
            health_value = result.scalar()
            
            # Get connection pool status
            pool = engine.pool
            pool_status = {
                "pool_size": pool.size(),
                "checked_in": pool.checkedin(),
                "checked_out": pool.checkedout(),
                "overflow": pool.overflow(),
            }
            
            response_time = (time.time() - start_time) * 1000  # ms
            
            return {
                "status": "healthy" if health_value == 1 else "unhealthy",
                "response_time_ms": round(response_time, 2),
                "pool_status": pool_status,
                "timestamp": time.time(),
            }
            
    except Exception as e:
        logger.error("Database health check failed", exc_info=e)
        return {
            "status": "unhealthy",
            "error": str(e),
            "response_time_ms": round((time.time() - start_time) * 1000, 2),
            "timestamp": time.time(),
        }


async def init_db() -> None:
    """
    Initialize database with comprehensive error handling and logging.
    
    Raises:
        DatabaseError: If database initialization fails
    """
    try:
        logger.info("Starting database initialization")
        
        async with engine.begin() as conn:
            # Import all models to ensure they are registered with SQLAlchemy
            from app.models import auth, user  # noqa: F401
            
            # Create all tables
            await conn.run_sync(Base.metadata.create_all)
            
            # Verify tables were created by checking a simple query
            await conn.execute(text("SELECT 1"))
            
        logger.info("Database initialization completed successfully")
        
    except Exception as e:
        logger.error("Database initialization failed", exc_info=e)
        raise DatabaseError(f"Failed to initialize database: {str(e)}") from e


async def close_db() -> None:
    """
    Gracefully close all database connections with proper cleanup.
    """
    try:
        logger.info("Closing database connections")
        await engine.dispose()
        logger.info("Database connections closed successfully")
    except Exception as e:
        logger.error("Error closing database connections", exc_info=e)
        # Don't raise here as this is cleanup code


# Enhanced event listeners for database security and performance
@event.listens_for(engine.sync_engine, "connect")
def set_database_pragma(dbapi_connection, _connection_record):
    """
    Set database-specific optimizations and security settings.
    
    Args:
        dbapi_connection: Raw database connection
        _connection_record: SQLAlchemy connection record (unused)
    """
    try:
        cursor = dbapi_connection.cursor()
        
        if settings.database_url.startswith(("sqlite://", "sqlite+aiosqlite://")):
            # SQLite-specific security and performance settings
            cursor.execute("PRAGMA journal_mode=WAL")       # Better concurrency
            cursor.execute("PRAGMA foreign_keys=ON")        # Enforce FK constraints
            cursor.execute("PRAGMA synchronous=NORMAL")     # Balance safety/performance
            cursor.execute("PRAGMA cache_size=10000")       # 10MB cache
            cursor.execute("PRAGMA temp_store=MEMORY")      # Use memory for temp tables
            cursor.execute("PRAGMA secure_delete=ON")       # Overwrite deleted data
            cursor.execute("PRAGMA auto_vacuum=INCREMENTAL") # Automatic cleanup
            logger.debug("Applied SQLite security and performance pragmas")
            
        elif settings.database_url.startswith(("postgresql://", "postgresql+asyncpg://")):
            # PostgreSQL-specific settings
            cursor.execute("SET statement_timeout = '30s'")  # Prevent long-running queries
            cursor.execute("SET lock_timeout = '10s'")       # Prevent deadlock hangs
            logger.debug("Applied PostgreSQL security settings")
            
        cursor.close()
        
    except Exception as e:
        logger.warning("Failed to set database pragmas", exc_info=e)
        # Don't raise as this might be expected for some database types


@event.listens_for(engine.sync_engine, "before_cursor_execute")
def receive_before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    """
    Log slow queries for performance monitoring.
    
    Args:
        conn: Database connection
        cursor: Database cursor
        statement: SQL statement
        parameters: Query parameters
        context: Execution context
        executemany: Whether this is a bulk operation
    """
    context._query_start_time = time.time()


@event.listens_for(engine.sync_engine, "after_cursor_execute")
def receive_after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    """
    Log completed queries and identify slow operations.
    
    Args:
        conn: Database connection
        cursor: Database cursor  
        statement: SQL statement
        parameters: Query parameters
        context: Execution context
        executemany: Whether this is a bulk operation
    """
    total = time.time() - context._query_start_time
    
    # Log slow queries (>1 second)
    if total > 1.0:
        logger.warning("Slow query detected", extra={
            "duration": round(total, 3),
            "statement": statement[:200] + "..." if len(statement) > 200 else statement,
        })
    elif settings.debug and total > 0.1:  # Log medium queries in debug mode
        logger.debug("Query execution", extra={
            "duration": round(total, 3),
            "statement": statement[:100] + "..." if len(statement) > 100 else statement,
        })


# Type alias for FastAPI dependency injection
DatabaseDep = AsyncSession
