"""
Enhanced health check router with cache monitoring and system diagnostics.
"""
import os
import re
import time
import psutil
from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel

from app.core.cache import cache_health_check, cache_manager, cache_api_response
from app.core.database import check_database_health

router = APIRouter(tags=["health"])
START_TIME = time.time()

class HealthResponse(BaseModel):
    """Basic health check response model."""
    status: str
    service: str
    version: str
    uptime: float

class DetailedHealthResponse(BaseModel):
    """Detailed health check response with system diagnostics."""
    status: str
    service: str
    version: str
    uptime: float
    timestamp: str
    components: Dict[str, Any]
    system: Dict[str, Any]
    performance: Dict[str, Any]

def get_secure_app_version() -> str:
    """
    Securely retrieve application version with input validation.
    
    Returns:
        str: Validated application version
        
    Raises:
        HTTPException: If version format is invalid
    """
    try:
        # Get version from environment with secure default
        version = os.getenv("APP_VERSION", "1.0.0")
        
        # Validate version format (semantic versioning pattern)
        version_pattern = r'^(?P<major>0|[1-9]\d*)\.(?P<minor>0|[1-9]\d*)\.(?P<patch>0|[1-9]\d*)(?:-(?P<prerelease>(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*)(?:\.(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*))*))?(?:\+(?P<buildmetadata>[0-9a-zA-Z-]+(?:\.[0-9a-zA-Z-]+)*))?$'
        
        if not re.match(version_pattern, version):
            # Log the attempt but don't expose the invalid value
            print(f"Warning: Invalid APP_VERSION format detected, using default")
            return "1.0.0"
        
        # Additional length check to prevent potential buffer overflow scenarios
        if len(version) > 50:
            print(f"Warning: APP_VERSION too long, using default")
            return "1.0.0"
        
        return version
        
    except Exception as e:
        # Log error but don't expose details to client
        print(f"Error retrieving app version: {e}")
        return "1.0.0"

def calculate_secure_uptime() -> float:
    """
    Calculate uptime with bounds checking.
    
    Returns:
        float: Uptime in seconds (rounded to 2 decimal places)
    """
    try:
        uptime = time.time() - START_TIME
        # Sanity check for negative uptime (system clock issues)
        if uptime < 0:
            return 0.0
        # Reasonable maximum uptime (100 years in seconds)
        if uptime > 3153600000:
            return 3153600000.0
        return round(uptime, 2)
    except Exception:
        return 0.0

@router.get("/health", response_model=HealthResponse)
def health() -> Dict[str, Any]:
    """
    Basic health check endpoint with secure data handling.
    
    Returns:
        Dict: Basic health status information
        
    Raises:
        HTTPException: If health check fails
    """
    try:
        return {
            "status": "healthy",
            "service": "syferstack-backend",
            "version": get_secure_app_version(),
            "uptime": calculate_secure_uptime(),
        }
    except Exception as e:
        # Log the error but don't expose internal details
        print(f"Health check failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Health check unavailable"
        )

@router.get("/health/detailed", response_model=DetailedHealthResponse)
@cache_api_response(ttl=30)  # Cache for 30 seconds
async def detailed_health() -> Dict[str, Any]:
    """
    Detailed health check with system diagnostics and component status.
    
    Returns:
        Dict: Comprehensive health information
    """
    try:
        start_time = time.time()
        
        # Get component health
        database_health = await check_database_health()
        cache_health = await cache_health_check()
        
        # System metrics
        memory = psutil.virtual_memory()
        cpu_percent = psutil.cpu_percent(interval=0.1)
        disk_usage = psutil.disk_usage('/')
        
        # Performance metrics
        response_time = round((time.time() - start_time) * 1000, 2)
        
        # Determine overall status
        overall_status = "healthy"
        if database_health.get("status") != "healthy":
            overall_status = "degraded"
        if cache_health.get("status") not in ["healthy", "degraded"]:
            overall_status = "unhealthy"
        
        return {
            "status": overall_status,
            "service": "syferstack-backend",
            "version": get_secure_app_version(),
            "uptime": calculate_secure_uptime(),
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "components": {
                "database": database_health,
                "cache": cache_health,
            },
            "system": {
                "cpu_percent": cpu_percent,
                "memory": {
                    "total": memory.total,
                    "available": memory.available,
                    "used": memory.used,
                    "percent": memory.percent,
                },
                "disk": {
                    "total": disk_usage.total,
                    "used": disk_usage.used,
                    "free": disk_usage.free,
                    "percent": (disk_usage.used / disk_usage.total) * 100,
                }
            },
            "performance": {
                "response_time_ms": response_time,
                "cache_stats": await cache_manager.get_stats() if cache_manager._initialized else None,
            }
        }
        
    except Exception as e:
        print(f"Detailed health check failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Detailed health check unavailable"
        )

@router.get("/health/cache")
async def cache_health() -> Dict[str, Any]:
    """
    Cache-specific health endpoint.
    
    Returns:
        Dict: Cache system health and statistics
    """
    try:
        health = await cache_health_check()
        return health
    except Exception as e:
        print(f"Cache health check failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Cache health check unavailable"
        )

@router.get("/health/liveness")
def liveness() -> Dict[str, Any]:
    """
    Kubernetes liveness probe endpoint.
    Simple check to verify the application is running and responsive.
    
    Returns:
        Dict: Liveness status
    """
    try:
        return {
            "status": "alive",
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        }
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Service not alive"
        )

@router.get("/health/readiness")
async def readiness() -> Dict[str, Any]:
    """
    Kubernetes readiness probe endpoint.
    Comprehensive check of all dependencies to verify service is ready to accept traffic.
    
    Returns:
        Dict: Readiness status with component checks
        
    Raises:
        HTTPException: If any critical component is not ready
    """
    try:
        ready = True
        components = {}
        
        # Check database connectivity
        db_health = await check_database_health()
        components["database"] = db_health
        if db_health.get("status") != "healthy":
            ready = False
        
        # Check cache connectivity
        cache_health = await cache_health_check()
        components["cache"] = cache_health
        if cache_health.get("status") not in ["healthy", "degraded"]:
            ready = False
        
        # Check critical system resources
        memory = psutil.virtual_memory()
        disk_usage = psutil.disk_usage('/')
        
        # Memory check (fail if > 95% used)
        if memory.percent > 95:
            ready = False
            components["memory"] = {"status": "critical", "percent": memory.percent}
        else:
            components["memory"] = {"status": "healthy", "percent": memory.percent}
        
        # Disk check (fail if > 90% used)
        disk_percent = (disk_usage.used / disk_usage.total) * 100
        if disk_percent > 90:
            ready = False
            components["disk"] = {"status": "critical", "percent": disk_percent}
        else:
            components["disk"] = {"status": "healthy", "percent": disk_percent}
        
        if not ready:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail={
                    "status": "not_ready",
                    "components": components,
                    "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
                }
            )
        
        return {
            "status": "ready",
            "components": components,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Readiness check failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Readiness check failed"
        )

@router.get("/health/startup")
async def startup() -> Dict[str, Any]:
    """
    Kubernetes startup probe endpoint.
    Used during container startup to verify the application has initialized properly.
    
    Returns:
        Dict: Startup status
    """
    try:
        # Check if application has been running for at least 10 seconds
        uptime = calculate_secure_uptime()
        if uptime < 10:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Application still starting up"
            )
        
        # Basic connectivity checks
        db_health = await check_database_health()
        if db_health.get("status") != "healthy":
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Database not ready"
            )
        
        return {
            "status": "started",
            "uptime": uptime,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Startup check failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Startup check failed"
        )

@router.post("/health/cache/clear")
async def clear_cache(namespace: Optional[str] = None) -> Dict[str, Any]:
    """
    Clear cache namespace (admin endpoint).
    
    Args:
        namespace: Optional namespace to clear (clears all if not specified)
        
    Returns:
        Dict: Cache clear operation result
    """
    try:
        if namespace:
            cleared_count = await cache_manager.clear_namespace(namespace)
            return {
                "status": "success",
                "message": f"Cleared {cleared_count} keys from namespace '{namespace}'",
                "namespace": namespace,
                "cleared_keys": cleared_count
            }
        else:
            # Clear common namespaces
            namespaces = ["api_responses", "user_data", "computations"]
            total_cleared = 0
            for ns in namespaces:
                cleared = await cache_manager.clear_namespace(ns)
                total_cleared += cleared
            
            return {
                "status": "success",
                "message": f"Cleared {total_cleared} keys from {len(namespaces)} namespaces",
                "cleared_namespaces": namespaces,
                "total_cleared_keys": total_cleared
            }
            
    except Exception as e:
        print(f"Cache clear failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Cache clear operation failed"
        )