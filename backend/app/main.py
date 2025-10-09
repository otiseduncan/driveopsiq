"""
SyferStack Backend - FastAPI Application
"""
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address
from prometheus_fastapi_instrumentator import Instrumentator

from app.api.routes import auth, users, ai
from app.core.config import settings
from app.core.database import init_db, close_db


def _prepare_upload_dir(upload_target: str) -> None:
    """Create upload directory for local paths, tolerate remote schemes."""
    if "://" in upload_target:
        return

    try:
        Path(upload_target).mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise RuntimeError(
            f"Unable to create upload directory at '{upload_target}': {exc}"
        ) from exc


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.

    Handles startup and shutdown events for the FastAPI application.
    """
    # Startup
    print("[startup] Starting SyferStack Backend...")

    # Initialize database
    await init_db()
    print("[startup] Database initialized")

    # Prepare upload directory if applicable
    try:
        _prepare_upload_dir(settings.upload_dir)
    except RuntimeError as exc:
        print(f"[startup] {exc}")
        raise
    
    if settings.metrics_enabled:
        global instrumentator
        instrumentator = Instrumentator().instrument(app)
        instrumentator.expose(
            app,
            endpoint=settings.metrics_endpoint,
            include_in_schema=False,
        )

    yield

    # Shutdown
    print("[shutdown] Shutting down SyferStack Backend...")
    await close_db()
    print("[shutdown] Database connections closed")


# Create FastAPI application
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="A modern, secure backend API for SyferStack",
    openapi_url="/api/v1/openapi.json" if settings.debug else None,
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
    lifespan=lifespan,
)

# Security middleware
if not settings.debug:
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=settings.allowed_hosts,
    )

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=settings.allowed_methods,
    allow_headers=settings.allowed_headers,
)

async def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded):
    """Handle rate limit exceeded errors."""
    response = JSONResponse(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        content={
            "error": "Too Many Requests",
            "message": getattr(exc, "detail", "Rate limit exceeded"),
        },
    )
    reset_in = getattr(exc, "reset_in", None)
    if reset_in is not None:
        response.headers["Retry-After"] = str(int(reset_in))
    return response


limiter: Limiter | None = None
instrumentator: Instrumentator | None = None

if settings.rate_limit_enabled:
    limiter = Limiter(
        key_func=get_remote_address,
        default_limits=settings.rate_limit_default or None,
    )
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)
    app.add_middleware(SlowAPIMiddleware)


# Custom exception handlers
@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """Handle HTTP exceptions."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": "HTTP Exception",
            "message": exc.detail,
            "status_code": exc.status_code,
        },
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle request validation errors."""
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": "Validation Error",
            "message": "Invalid request data",
            "details": exc.errors(),
        },
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle general exceptions."""
    if settings.debug:
        import traceback
        error_detail = {
            "error": "Internal Server Error",
            "message": str(exc),
            "traceback": traceback.format_exc(),
        }
    else:
        error_detail = {
            "error": "Internal Server Error",
            "message": "An unexpected error occurred",
        }
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=error_detail,
    )


# Middleware for request logging (development only)
if settings.debug:
    @app.middleware("http")
    async def log_requests(request: Request, call_next):
        """Log all requests in debug mode."""
        import time
        
        start_time = time.time()
        response = await call_next(request)
        process_time = time.time() - start_time
        
        print(
            f"{request.method} {request.url} - "
            f"Status: {response.status_code} - "
            f"Time: {process_time:.4f}s"
        )
        
        return response


# Health check endpoint
@app.get("/health", tags=["Health"])
async def health_check():
    """
    Health check endpoint.
    
    Returns:
        dict: Application health status
    """
    return {
        "status": "healthy",
        "app_name": settings.app_name,
        "version": settings.app_version,
        "environment": "development" if settings.debug else "production",
    }


@app.get("/", tags=["Root"])
async def root():
    """
    Root endpoint.
    
    Returns:
        dict: Welcome message
    """
    return {
        "message": f"Welcome to {settings.app_name}",
        "version": settings.app_version,
        "docs_url": "/docs" if settings.debug else None,
    }


# Include routers
app.include_router(
    auth.router,
    prefix="/api/v1/auth",
    tags=["Authentication"],
)

app.include_router(
    users.router,
    prefix="/api/v1/users",
    tags=["Users"],
)

app.include_router(
    ai.router,
    prefix="/api/v1/ai",
    tags=["AI"],
)


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.reload,
        log_level="debug" if settings.debug else "info",
    )
