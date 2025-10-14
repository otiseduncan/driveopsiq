"""
SyferStack FastAPI application with enhanced security and performance configuration.
"""
import asyncio
import gzip
import logging
import os
import time
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Dict, List, Optional

from fastapi import FastAPI, Request, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from fastapi.security import HTTPBearer
from prometheus_fastapi_instrumentator import Instrumentator
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.responses import Response

# Performance imports
try:
    import orjson
    HAS_ORJSON = True
except ImportError:
    HAS_ORJSON = False

from .core.config import settings
from .logging_config import setup_json_logging
from .modules.driveops_iq.router import router as driveops_router
from .routers import health
from .services.demo_seed import seed_demo_users
from .db.session import SessionLocal

# Setup secure logging
setup_json_logging()
logger = logging.getLogger(__name__)

class PerformanceMiddleware(BaseHTTPMiddleware):
    """Enhanced middleware for performance monitoring and optimization."""
    
    async def dispatch(self, request: Request, call_next):
        # Start timing
        start_time = time.perf_counter()
        
        # Add request ID for tracing
        request_id = f"req_{int(time.time() * 1000)}_{hash(request.url.path) % 10000:04d}"
        
        # Process request
        response = await call_next(request)
        
        # Calculate response time
        process_time = time.perf_counter() - start_time
        
        # Add performance headers
        response.headers["X-Process-Time"] = f"{process_time:.6f}"
        response.headers["X-Request-ID"] = request_id
        
        # Log slow requests
        if process_time > 1.0:  # Log requests taking more than 1 second
            logger.warning(
                "Slow request detected",
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "process_time": process_time,
                    "status_code": response.status_code,
                }
            )
        
        return response


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
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        
        # Remove server header for security
        if "Server" in response.headers:
            del response.headers["Server"]
        
        return response


class CacheControlMiddleware(BaseHTTPMiddleware):
    """Middleware to add appropriate caching headers based on route."""
    
    def __init__(self, app):
        super().__init__(app)
        # Define caching rules for different endpoints
        self.cache_rules = {
            "/health": {"max_age": 60, "public": True},
            "/metrics": {"max_age": 30, "public": False},
            "/api/v1/users/me": {"max_age": 300, "public": False},
            "/openapi.json": {"max_age": 3600, "public": True},
            "/docs": {"max_age": 3600, "public": True},
            "/redoc": {"max_age": 3600, "public": True},
        }
    
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        
        # Apply caching rules
        path = request.url.path
        
        # Find matching cache rule
        cache_config = None
        for route_pattern, config in self.cache_rules.items():
            if path.startswith(route_pattern) or path == route_pattern:
                cache_config = config
                break
        
        if cache_config:
            cache_directive = f"max-age={cache_config['max_age']}"
            if cache_config.get("public", False):
                cache_directive = f"public, {cache_directive}"
            else:
                cache_directive = f"private, {cache_directive}"
            
            response.headers["Cache-Control"] = cache_directive
        else:
            # Default: no cache for API endpoints
            response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        
        return response


class CompressionMiddleware(BaseHTTPMiddleware):
    """Enhanced compression middleware with better performance."""
    
    def __init__(self, app, minimum_size: int = 1024, compression_level: int = 6):
        super().__init__(app)
        self.minimum_size = minimum_size
        self.compression_level = compression_level
        
        # Content types that benefit from compression
        self.compressible_types = {
            "application/json",
            "application/javascript",
            "text/css", 
            "text/html",
            "text/plain",
            "text/xml",
            "application/xml",
            "application/atom+xml",
            "application/rss+xml",
        }
    
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        
        # Check if client accepts gzip
        accept_encoding = request.headers.get("accept-encoding", "")
        if "gzip" not in accept_encoding.lower():
            return response
        
        # Check content type
        content_type = response.headers.get("content-type", "").split(";")[0]
        if content_type not in self.compressible_types:
            return response
        
        # Check if already compressed
        if response.headers.get("content-encoding"):
            return response
        
        # Get response body
        if hasattr(response, 'body'):
            body = response.body
            
            # Check minimum size
            if len(body) < self.minimum_size:
                return response
            
            # Compress the body
            compressed_body = gzip.compress(body, compresslevel=self.compression_level)
            
            # Update response
            response.headers["content-encoding"] = "gzip"
            response.headers["content-length"] = str(len(compressed_body))
            response.body = compressed_body
        
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
    
    try:
        # Initialize database connections (cache temporarily disabled)
        from app.core.database import init_db
        await init_db()
        logger.info("✅ Database initialized")
        
    except Exception as e:
        logger.error(f"❌ Startup failed: {e}")
        raise
    
    logger.info("✅ SyferStack API startup complete")
    
    yield
    
    # Shutdown
    logger.info("🛑 SyferStack API shutting down...")
    
    try:
        # Cleanup database connections (cache temporarily disabled)
        
        # Cleanup database connections
        from app.core.database import close_db
        await close_db()
        logger.info("✅ Database connections closed")
        
    except Exception as e:
        logger.error(f"❌ Shutdown error: {e}")
    
    logger.info("✅ SyferStack API shutdown complete")

# Create custom JSON response class for better performance
if HAS_ORJSON:
    from fastapi.responses import ORJSONResponse
    
    class FastJSONResponse(ORJSONResponse):
        """Ultra-fast JSON response using orjson."""
        pass
    
    default_response_class = FastJSONResponse
    logger.info("Using orjson for enhanced JSON performance")
else:
    default_response_class = JSONResponse
    logger.info("Using standard JSON encoder (consider installing orjson for better performance)")

# Create FastAPI app with secure and performance configuration
app = FastAPI(
    title="SyferStack API",
    description="Secure high-performance API for SyferStack with enterprise-grade features",
    version="2.0.0",
    docs_url="/docs" if settings.debug else None,  # Disable docs in production
    redoc_url="/redoc" if settings.debug else None,
    openapi_url="/openapi.json" if settings.debug else None,
    default_response_class=default_response_class,
    lifespan=lifespan,
    # Performance configurations
    generate_unique_id_function=lambda route: f"{route.tags[0] if route.tags else 'default'}_{route.name}",
    # Security configurations
    dependencies=[],  # Global dependencies can be added here
)

@app.on_event("startup")
def startup_event() -> None:
    """Seed demo data when running in demo mode."""
    if not settings.DEMO_MODE:
        return

    logger.info("Running DriveOps-IQ demo seeder…")
    db = SessionLocal()
    try:
        seed_demo_users(db)
    except Exception as exc:  # pragma: no cover - startup logging
        logger.exception("Failed to seed demo users: %s", exc)
    finally:
        db.close()

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

# Performance and Security middleware (order matters!)
# 1. Trusted hosts (first for security)
app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.allowed_hosts)

# 2. Performance monitoring (early for accurate timing)
app.add_middleware(PerformanceMiddleware)

# 3. Compression (before security headers to ensure proper compression)
app.add_middleware(GZipMiddleware, minimum_size=1000)

# 4. CORS (if needed, before security headers)
if settings.debug or settings.allowed_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=True,
        allow_methods=settings.allowed_methods,
        allow_headers=settings.allowed_headers,
        max_age=3600,  # Cache CORS headers
    )

# 5. Cache control (before security headers)
app.add_middleware(CacheControlMiddleware)

# 6. Security headers
app.add_middleware(SecurityHeadersMiddleware)

# 7. Rate limiting (last middleware for performance)
rate_limit = 200 if settings.debug else 100  # Higher limit in development
app.add_middleware(RateLimitMiddleware, calls_per_minute=rate_limit)

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
app.include_router(driveops_router, prefix="/api/v1")

# Import and include auth routes
from .api.routes import auth, users
app.include_router(auth.router, prefix="/api/v1/auth", tags=["authentication"])
app.include_router(users.router, prefix="/api/v1/users", tags=["users"])

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
    
    # Check for performance dependencies
    try:
        import uvloop
        asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
        logger.info("Using uvloop for enhanced async performance")
    except ImportError:
        logger.info("uvloop not available, using default asyncio")
    
    # Configuration for development
    config = {
        "app": "app.main:app",
        "host": "0.0.0.0", 
        "port": 8000,
        "reload": settings.debug,
        "log_level": "info",
        "access_log": True,
        "loop": "asyncio",
        "interface": "asgi3",
        "lifespan": "on",
    }
    
    # Performance optimizations for development
    if not settings.debug:
        config.update({
            "workers": 1,  # Single worker for development
            "timeout_keep_alive": 5,
            "limit_concurrency": 100,
            "backlog": 2048,
        })
    
    # Use httptools if available
    try:
        import httptools
        config["http"] = "httptools"
        logger.info("Using httptools for faster HTTP parsing")
    except ImportError:
        config["http"] = "h11"
        logger.info("httptools not available, using h11")
    
    uvicorn.run(**config)
