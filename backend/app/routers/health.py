"""
Health check router with secure environment variable handling.
"""
import os
import re
import time
from typing import Dict, Any
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

router = APIRouter(tags=["health"])
START_TIME = time.time()

class HealthResponse(BaseModel):
    """Health check response model."""
    status: str
    service: str
    version: str
    uptime: float

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
    Health check endpoint with secure data handling.
    
    Returns:
        Dict: Health status information
        
    Raises:
        HTTPException: If health check fails
    """
    try:
        return {
            "status": "ok",
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