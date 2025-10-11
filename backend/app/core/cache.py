"""
Advanced caching system with Redis backend and intelligent cache strategies.
"""

import asyncio
import json
import logging
import time
from datetime import datetime, timedelta
from functools import wraps
from typing import Any, Callable, Dict, Optional, Union, TypeVar, ParamSpec
import hashlib
import pickle

from aiocache import Cache
from aiocache.serializers import PickleSerializer, JsonSerializer
import redis.asyncio as redis
from pydantic import BaseModel

from app.core.config import settings

logger = logging.getLogger(__name__)

# Type hints for decorators
P = ParamSpec('P')
T = TypeVar('T')


class CacheConfig(BaseModel):
    """Cache configuration model."""
    default_ttl: int = 3600  # 1 hour
    user_data_ttl: int = 900  # 15 minutes
    session_ttl: int = 86400  # 24 hours
    api_response_ttl: int = 300  # 5 minutes
    heavy_computation_ttl: int = 7200  # 2 hours
    redis_url: str = settings.redis_url
    redis_db: int = 0
    key_prefix: str = "syferstack"


class CacheStats(BaseModel):
    """Cache statistics model."""
    hits: int = 0
    misses: int = 0
    sets: int = 0
    deletes: int = 0
    errors: int = 0
    
    @property
    def hit_rate(self) -> float:
        total = self.hits + self.misses
        return (self.hits / total * 100) if total > 0 else 0.0


class AdvancedCacheManager:
    """
    Advanced cache manager with multiple backends and intelligent strategies.
    """
    
    def __init__(self, config: Optional[CacheConfig] = None):
        self.config = config or CacheConfig()
        self.stats = CacheStats()
        self._redis_pool: Optional[redis.Redis] = None
        self._memory_cache: Optional[Cache] = None
        self._initialized = False
    
    async def initialize(self) -> None:
        """Initialize cache backends."""
        if self._initialized:
            return
        
        try:
            # Initialize Redis connection pool
            self._redis_pool = redis.from_url(
                self.config.redis_url,
                db=self.config.redis_db,
                encoding="utf-8",
                decode_responses=True,
                max_connections=20,
                retry_on_timeout=True,
            )
            
            # Test Redis connection
            await self._redis_pool.ping()
            logger.info("Redis cache backend initialized successfully")
            
            # Initialize in-memory cache as fallback
            self._memory_cache = Cache.from_url("memory://", serializer=PickleSerializer())
            
            self._initialized = True
            
        except Exception as e:
            logger.error(f"Failed to initialize cache backends: {e}")
            # Fallback to memory-only cache
            self._memory_cache = Cache.from_url("memory://", serializer=PickleSerializer())
            self._initialized = True
            
    async def close(self) -> None:
        """Close cache connections."""
        if self._redis_pool:
            await self._redis_pool.close()
        if self._memory_cache:
            await self._memory_cache.close()
        self._initialized = False
    
    def _generate_key(self, namespace: str, key: str, **params) -> str:
        """Generate cache key with namespace and parameters."""
        if params:
            # Sort parameters for consistent key generation
            param_str = "&".join(f"{k}={v}" for k, v in sorted(params.items()))
            key = f"{key}?{param_str}"
        
        # Hash long keys to avoid Redis key length limits
        if len(key) > 200:
            key = hashlib.sha256(key.encode()).hexdigest()
        
        return f"{self.config.key_prefix}:{namespace}:{key}"
    
    async def get(
        self, 
        namespace: str, 
        key: str, 
        deserializer: Optional[Callable] = None,
        **params
    ) -> Optional[Any]:
        """Get value from cache with fallback strategy."""
        if not self._initialized:
            await self.initialize()
        
        cache_key = self._generate_key(namespace, key, **params)
        
        try:
            # Try Redis first
            if self._redis_pool:
                value = await self._redis_pool.get(cache_key)
                if value is not None:
                    self.stats.hits += 1
                    
                    # Deserialize based on type
                    if deserializer:
                        return deserializer(value)
                    
                    try:
                        # Try JSON first (most common)
                        return json.loads(value)
                    except (json.JSONDecodeError, TypeError):
                        try:
                            # Fallback to pickle
                            return pickle.loads(value.encode() if isinstance(value, str) else value)
                        except:
                            return value
            
            # Fallback to memory cache
            if self._memory_cache:
                value = await self._memory_cache.get(cache_key)
                if value is not None:
                    self.stats.hits += 1
                    return value
            
            self.stats.misses += 1
            return None
            
        except Exception as e:
            logger.error(f"Cache get error for key {cache_key}: {e}")
            self.stats.errors += 1
            return None
    
    async def set(
        self, 
        namespace: str, 
        key: str, 
        value: Any, 
        ttl: Optional[int] = None,
        serializer: Optional[Callable] = None,
        **params
    ) -> bool:
        """Set value in cache with intelligent serialization."""
        if not self._initialized:
            await self.initialize()
        
        cache_key = self._generate_key(namespace, key, **params)
        ttl = ttl or self.config.default_ttl
        
        try:
            # Serialize value
            if serializer:
                serialized_value = serializer(value)
            elif isinstance(value, (dict, list, str, int, float, bool, type(None))):
                serialized_value = json.dumps(value, default=str)
            else:
                serialized_value = pickle.dumps(value)
            
            # Set in Redis
            if self._redis_pool:
                await self._redis_pool.setex(cache_key, ttl, serialized_value)
            
            # Set in memory cache as backup
            if self._memory_cache:
                await self._memory_cache.set(cache_key, value, ttl=ttl)
            
            self.stats.sets += 1
            return True
            
        except Exception as e:
            logger.error(f"Cache set error for key {cache_key}: {e}")
            self.stats.errors += 1
            return False
    
    async def delete(self, namespace: str, key: str, **params) -> bool:
        """Delete key from cache."""
        if not self._initialized:
            await self.initialize()
        
        cache_key = self._generate_key(namespace, key, **params)
        
        try:
            success = True
            
            # Delete from Redis
            if self._redis_pool:
                deleted = await self._redis_pool.delete(cache_key)
                success = success and (deleted > 0)
            
            # Delete from memory cache
            if self._memory_cache:
                await self._memory_cache.delete(cache_key)
            
            if success:
                self.stats.deletes += 1
            
            return success
            
        except Exception as e:
            logger.error(f"Cache delete error for key {cache_key}: {e}")
            self.stats.errors += 1
            return False
    
    async def clear_namespace(self, namespace: str) -> int:
        """Clear all keys in a namespace."""
        if not self._initialized:
            await self.initialize()
        
        pattern = f"{self.config.key_prefix}:{namespace}:*"
        deleted_count = 0
        
        try:
            if self._redis_pool:
                keys = await self._redis_pool.keys(pattern)
                if keys:
                    deleted_count = await self._redis_pool.delete(*keys)
            
            # Memory cache doesn't support pattern deletion easily
            # This is a limitation we accept for the fallback cache
            
            logger.info(f"Cleared {deleted_count} keys from namespace '{namespace}'")
            return deleted_count
            
        except Exception as e:
            logger.error(f"Cache clear namespace error for '{namespace}': {e}")
            self.stats.errors += 1
            return 0
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics and health information."""
        stats_dict = self.stats.model_dump()
        
        # Add Redis info if available
        if self._redis_pool:
            try:
                redis_info = await self._redis_pool.info()
                stats_dict["redis"] = {
                    "connected": True,
                    "used_memory": redis_info.get("used_memory_human"),
                    "keyspace": redis_info.get(f"db{self.config.redis_db}", {}),
                    "version": redis_info.get("redis_version"),
                }
            except Exception as e:
                stats_dict["redis"] = {"connected": False, "error": str(e)}
        else:
            stats_dict["redis"] = {"connected": False, "reason": "Redis not configured"}
        
        return stats_dict


# Global cache manager instance
cache_manager = AdvancedCacheManager()


def cached(
    namespace: str, 
    ttl: Optional[int] = None,
    key_generator: Optional[Callable] = None,
    condition: Optional[Callable] = None,
) -> Callable[[Callable[P, T]], Callable[P, T]]:
    """
    Decorator for caching function results with intelligent key generation.
    
    Args:
        namespace: Cache namespace for organization
        ttl: Time to live in seconds (uses default if None)
        key_generator: Custom function to generate cache key from arguments
        condition: Function to determine if result should be cached
    """
    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        @wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            # Generate cache key
            if key_generator:
                cache_key = key_generator(*args, **kwargs)
            else:
                # Default key generation
                func_name = func.__name__
                args_str = "_".join(str(arg) for arg in args)
                kwargs_str = "_".join(f"{k}={v}" for k, v in sorted(kwargs.items()))
                cache_key = f"{func_name}_{args_str}_{kwargs_str}"
            
            # Try to get cached result
            cached_result = await cache_manager.get(namespace, cache_key)
            if cached_result is not None:
                logger.debug(f"Cache hit for {namespace}:{cache_key}")
                return cached_result
            
            # Execute function
            logger.debug(f"Cache miss for {namespace}:{cache_key}, executing function")
            result = await func(*args, **kwargs)
            
            # Cache result if condition is met
            should_cache = condition(result) if condition else True
            if should_cache:
                await cache_manager.set(namespace, cache_key, result, ttl)
            
            return result
        
        return wrapper
    return decorator


def cache_user_data(ttl: Optional[int] = None):
    """Decorator for caching user-specific data."""
    return cached(
        namespace="user_data", 
        ttl=ttl or cache_manager.config.user_data_ttl,
        key_generator=lambda *args, **kwargs: f"user_{kwargs.get('user_id', args[0] if args else 'anonymous')}"
    )


def cache_api_response(ttl: Optional[int] = None):
    """Decorator for caching API responses."""
    return cached(
        namespace="api_responses",
        ttl=ttl or cache_manager.config.api_response_ttl,
        condition=lambda result: result is not None and not isinstance(result, Exception)
    )


def cache_heavy_computation(ttl: Optional[int] = None):
    """Decorator for caching expensive computations."""
    return cached(
        namespace="computations",
        ttl=ttl or cache_manager.config.heavy_computation_ttl
    )


class SessionCache:
    """Specialized cache for user sessions with enhanced security."""
    
    @staticmethod
    async def set_session(user_id: str, session_data: Dict[str, Any], ttl: Optional[int] = None) -> str:
        """Create a new session and return session token."""
        session_token = hashlib.sha256(f"{user_id}_{time.time()}_{id(session_data)}".encode()).hexdigest()
        
        session_info = {
            "user_id": user_id,
            "created_at": datetime.utcnow().isoformat(),
            "last_accessed": datetime.utcnow().isoformat(),
            "data": session_data,
        }
        
        success = await cache_manager.set(
            "sessions", 
            session_token, 
            session_info,
            ttl or cache_manager.config.session_ttl
        )
        
        if success:
            logger.info(f"Session created for user {user_id}")
            return session_token
        else:
            raise RuntimeError("Failed to create session")
    
    @staticmethod
    async def get_session(session_token: str) -> Optional[Dict[str, Any]]:
        """Get session data and update last accessed time."""
        session_info = await cache_manager.get("sessions", session_token)
        
        if session_info:
            # Update last accessed time
            session_info["last_accessed"] = datetime.utcnow().isoformat()
            await cache_manager.set(
                "sessions", 
                session_token, 
                session_info,
                cache_manager.config.session_ttl
            )
            
            return session_info
        
        return None
    
    @staticmethod
    async def delete_session(session_token: str) -> bool:
        """Delete a session."""
        success = await cache_manager.delete("sessions", session_token)
        if success:
            logger.info(f"Session {session_token[:8]}... deleted")
        return success
    
    @staticmethod
    async def delete_user_sessions(user_id: str) -> int:
        """Delete all sessions for a user (requires Redis)."""
        # This is a simplified implementation
        # In production, you might want to maintain a user->sessions mapping
        logger.info(f"Session cleanup requested for user {user_id}")
        return 0


# Utility functions for common caching patterns
async def cache_with_timeout(
    key: str, 
    fetch_func: Callable[[], Any], 
    ttl: int = 300,
    namespace: str = "general"
) -> Any:
    """Cache pattern with automatic fetch on miss."""
    cached_value = await cache_manager.get(namespace, key)
    
    if cached_value is not None:
        return cached_value
    
    # Fetch fresh data
    fresh_value = await fetch_func() if asyncio.iscoroutinefunction(fetch_func) else fetch_func()
    
    # Cache for future requests
    await cache_manager.set(namespace, key, fresh_value, ttl)
    
    return fresh_value


async def invalidate_user_cache(user_id: str) -> None:
    """Invalidate all cached data for a specific user."""
    await cache_manager.clear_namespace(f"user_data")
    await SessionCache.delete_user_sessions(user_id)
    logger.info(f"Cache invalidated for user {user_id}")


async def warm_cache() -> None:
    """Pre-populate cache with commonly accessed data."""
    logger.info("Starting cache warm-up process")
    
    # Add your cache warming logic here
    # Example: Pre-load frequently accessed data
    
    logger.info("Cache warm-up completed")


# Health check for cache system
async def cache_health_check() -> Dict[str, Any]:
    """Check cache system health."""
    if not cache_manager._initialized:
        await cache_manager.initialize()
    
    health = {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "backends": {},
    }
    
    # Test Redis
    if cache_manager._redis_pool:
        try:
            start_time = time.time()
            await cache_manager._redis_pool.ping()
            response_time = (time.time() - start_time) * 1000
            
            health["backends"]["redis"] = {
                "status": "healthy",
                "response_time_ms": round(response_time, 2),
            }
        except Exception as e:
            health["backends"]["redis"] = {
                "status": "unhealthy",
                "error": str(e),
            }
            health["status"] = "degraded"
    
    # Test memory cache
    if cache_manager._memory_cache:
        try:
            test_key = "health_check_test"
            await cache_manager._memory_cache.set(test_key, "test", ttl=1)
            value = await cache_manager._memory_cache.get(test_key)
            
            health["backends"]["memory"] = {
                "status": "healthy" if value == "test" else "unhealthy",
            }
        except Exception as e:
            health["backends"]["memory"] = {
                "status": "unhealthy",
                "error": str(e),
            }
    
    # Add cache statistics
    health["statistics"] = await cache_manager.get_stats()
    
    return health