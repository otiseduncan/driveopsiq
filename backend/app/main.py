"""
SyferStack FastAPI application with enhanced security configuration.
"""
import logging
import os
import time
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Dict, List

from fastapi import FastAPI, Request, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from fastapi.security import HTTPBearer
from prometheus_fastapi_instrumentator import Instrumentator
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException

from .core.config import settings
from .logging_config import setup_json_logging
from .routers import health

# Setup secure logging
setup_json_logging()
logger = logging.getLogger(__name__)

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Middleware to add security headers to all responses."""
    
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        
        # Security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        
        # Remove server header for security
        response.headers.pop("Server", None)
        
        return response

class RateLimitMiddleware(BaseHTTPMiddleware):
    """Simple rate limiting middleware."""
    
    def __init__(self, app, calls_per_minute: int = 100):
        super().__init__(app)
        self.calls_per_minute = calls_per_minute
        self.clients: Dict[str, List[float]] = {}
        
    async def dispatch(self, request: Request, call_next):
        client_ip = request.client.host if request.client else "unknown"
        current_time = time.time()
        
        # Clean old entries (older than 1 minute)
        cutoff_time = current_time - 60
        self.clients = {
            ip: timestamps for ip, timestamps in self.clients.items()
            if timestamps and timestamps[-1] > cutoff_time
        }
        
        # Check rate limit
        if client_ip not in self.clients:
            self.clients[client_ip] = []
            
        # Remove old timestamps for this client
        self.clients[client_ip] = [
            ts for ts in self.clients[client_ip] if ts > cutoff_time
        ]
        
        if len(self.clients[client_ip]) >= self.calls_per_minute:
            return JSONResponse(
                status_code=429,
                content={"detail": "Too many requests. Please try again later."},
                headers={"Retry-After": "60"}
            )
        
        self.clients[client_ip].append(current_time)
        return await call_next(request)

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan manager for startup/shutdown events."""
    # Startup
    logger.info("🚀 SyferStack API starting up...")
    
    # Initialize database connections, caches, etc. here
    # await database.connect()
    
    logger.info("✅ SyferStack API startup complete")
    
    yield
    
    # Shutdown
    logger.info("🛑 SyferStack API shutting down...")
    
    # Cleanup resources here
    # await database.disconnect()
    
    logger.info("✅ SyferStack API shutdown complete")

# Create FastAPI app with secure configuration
app = FastAPI(
    title="SyferStack API",
    description="Secure production-grade API for SyferStack",
    version="2.0.0",
    docs_url="/docs" if settings.debug else None,  # Disable docs in production
    redoc_url="/redoc" if settings.debug else None,
    openapi_url="/openapi.json" if settings.debug else None,
    lifespan=lifespan,
    # Security configurations
    dependencies=[],  # Global dependencies can be added here
)

# Exception handlers for better error management
@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """Handle HTTP exceptions with secure error responses."""
    
    # Log the error (without sensitive data)
    logger.warning(
        "HTTP exception occurred",
        extra={
            "status_code": exc.status_code,
            "path": request.url.path,
            "method": request.method,
            "client_ip": request.client.host if request.client else "unknown"
        }
    )
    
    # Return sanitized error response
    if exc.status_code == 404:
        return JSONResponse(
            status_code=404,
            content={"detail": "Resource not found"}
        )
    elif exc.status_code == 500:
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error"}
        )
    else:
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail}
        )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle unexpected exceptions securely."""
    
    # Log the full error for debugging (server-side only)
    logger.error(
        "Unexpected error occurred",
        exc_info=exc,
        extra={
            "path": request.url.path,
            "method": request.method,
            "client_ip": request.client.host if request.client else "unknown"
        }
    )
    
    # Return generic error to client (don't leak internal details)
    return JSONResponse(
        status_code=500,
        content={"detail": "An unexpected error occurred"}
    )

# Security middleware (order matters!)
# 1. Trusted hosts
app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.allowed_hosts)

# 2. CORS (if needed)
if settings.debug or settings.allowed_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=True,
        allow_methods=settings.allowed_methods,
        allow_headers=settings.allowed_headers,
    )

# 3. Security headers
app.add_middleware(SecurityHeadersMiddleware)

# 4. Rate limiting
app.add_middleware(RateLimitMiddleware, calls_per_minute=100)

# Set up Prometheus instrumentation (after middleware)
instrumentator = Instrumentator(
    should_group_status_codes=False,
    should_ignore_untemplated=True,
    should_respect_env_var=True,
    should_instrument_requests_inprogress=True,
    excluded_handlers=["/metrics", "/health"],  # Don't monitor these endpoints
    env_var_name="ENABLE_METRICS",
    inprogress_name="http_requests_inprogress",
    inprogress_labels=True,
)

# Only enable metrics if configured
if settings.metrics_enabled:
    instrumentator.instrument(app).expose(app, include_in_schema=False, endpoint=settings.metrics_endpoint)
else:
    logger.info("Metrics disabled via configuration")

# Include routers
app.include_router(health.router, prefix="/api/v1")

# Add root endpoint
@app.get("/", include_in_schema=False)
async def root():
    """Root endpoint with basic API information."""
    return {
        "service": "SyferStack API",
        "version": "2.0.0",
        "status": "operational",
        "docs": "/docs" if settings.debug else "Documentation disabled in production"
    }

# Health check endpoint at root level
@app.get("/health", include_in_schema=False, tags=["monitoring"])
async def root_health():
    """Root level health check for load balancers."""
    return {"status": "ok", "service": "SyferStack API"}

if __name__ == "__main__":
    import uvicorn
    
    # Configuration for development
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
        log_level="info",
        access_log=True,
    )
