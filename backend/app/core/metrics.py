"""
Enhanced monitoring and metrics system with custom Prometheus metrics.
"""

import time
import logging
from typing import Dict, Any, Optional, Callable
from functools import wraps
from contextlib import asynccontextmanager

from prometheus_client import (
    Counter, Histogram, Gauge, Summary, Info,
    CollectorRegistry, generate_latest, CONTENT_TYPE_LATEST
)
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import settings

logger = logging.getLogger(__name__)

# Create custom registry for application metrics
app_registry = CollectorRegistry()

# Core application metrics
request_count = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status_code'],
    registry=app_registry
)

request_duration = Histogram(
    'http_request_duration_seconds',
    'HTTP request duration in seconds',
    ['method', 'endpoint'],
    buckets=(0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
    registry=app_registry
)

request_size = Summary(
    'http_request_size_bytes',
    'HTTP request size in bytes',
    ['method', 'endpoint'],
    registry=app_registry
)

response_size = Summary(
    'http_response_size_bytes',
    'HTTP response size in bytes',
    ['method', 'endpoint'],
    registry=app_registry
)

# Business metrics
active_users = Gauge(
    'active_users_total',
    'Number of active users',
    registry=app_registry
)

cache_operations = Counter(
    'cache_operations_total',
    'Total cache operations',
    ['operation', 'status'],
    registry=app_registry
)

database_operations = Counter(
    'database_operations_total',
    'Total database operations',
    ['operation', 'table', 'status'],
    registry=app_registry
)

database_connection_pool = Gauge(
    'database_connections_active',
    'Active database connections',
    registry=app_registry
)

# System metrics
memory_usage = Gauge(
    'memory_usage_bytes',
    'Memory usage in bytes',
    ['type'],
    registry=app_registry
)

cpu_usage = Gauge(
    'cpu_usage_percent',
    'CPU usage percentage',
    registry=app_registry
)

# Error tracking
error_count = Counter(
    'errors_total',
    'Total application errors',
    ['error_type', 'component'],
    registry=app_registry
)

# Security metrics
security_events = Counter(
    'security_events_total',
    'Security-related events',
    ['event_type', 'severity'],
    registry=app_registry
)

# Performance metrics
slow_queries = Counter(
    'slow_queries_total',
    'Number of slow database queries',
    ['query_type'],
    registry=app_registry
)

# API-specific metrics
api_rate_limit_hits = Counter(
    'api_rate_limit_hits_total',
    'API rate limit hits',
    ['endpoint', 'client_type'],
    registry=app_registry
)

# Application info
app_info = Info(
    'application_info',
    'Application information',
    registry=app_registry
)


class MetricsMiddleware(BaseHTTPMiddleware):
    """
    Enhanced middleware for collecting detailed HTTP metrics.
    """
    
    def __init__(self, app, enable_detailed_metrics: bool = True):
        super().__init__(app)
        self.enable_detailed_metrics = enable_detailed_metrics
    
    async def dispatch(self, request: Request, call_next):
        # Skip metrics collection for metrics endpoint itself
        if request.url.path == settings.metrics_endpoint:
            return await call_next(request)
        
        start_time = time.time()
        
        # Get request info
        method = request.method
        endpoint = self._get_endpoint_name(request)
        
        # Measure request size
        request_body_size = 0
        if hasattr(request, 'body'):
            try:
                body = await request.body()
                request_body_size = len(body) if body else 0
            except:
                pass
        
        try:
            # Process request
            response = await call_next(request)
            
            # Measure response time
            duration = time.time() - start_time
            
            # Get response size
            response_body_size = 0
            if hasattr(response, 'body') and response.body:
                response_body_size = len(response.body)
            
            # Record metrics
            request_count.labels(
                method=method, 
                endpoint=endpoint, 
                status_code=response.status_code
            ).inc()
            
            request_duration.labels(
                method=method, 
                endpoint=endpoint
            ).observe(duration)
            
            if self.enable_detailed_metrics:
                request_size.labels(
                    method=method, 
                    endpoint=endpoint
                ).observe(request_body_size)
                
                response_size.labels(
                    method=method, 
                    endpoint=endpoint
                ).observe(response_body_size)
            
            # Log slow requests
            if duration > 2.0:  # Requests taking more than 2 seconds
                logger.warning(
                    f"Slow request detected: {method} {endpoint} - {duration:.2f}s",
                    extra={
                        "method": method,
                        "endpoint": endpoint,
                        "duration": duration,
                        "status_code": response.status_code,
                    }
                )
            
            return response
            
        except Exception as e:
            # Record error
            error_count.labels(
                error_type=type(e).__name__,
                component="http_middleware"
            ).inc()
            
            # Record failed request
            request_count.labels(
                method=method, 
                endpoint=endpoint, 
                status_code=500
            ).inc()
            
            duration = time.time() - start_time
            request_duration.labels(
                method=method, 
                endpoint=endpoint
            ).observe(duration)
            
            raise
    
    def _get_endpoint_name(self, request: Request) -> str:
        """Extract endpoint name for metrics labeling."""
        path = request.url.path
        
        # Group similar endpoints to avoid high cardinality
        if path.startswith('/api/v1/users/'):
            if path.endswith('/me'):
                return '/api/v1/users/me'
            elif path.split('/')[-1].isdigit():
                return '/api/v1/users/{id}'
        
        # Health endpoints
        if path.startswith('/health'):
            return '/health'
        
        # API documentation
        if path in ['/docs', '/redoc', '/openapi.json']:
            return path
        
        # Default grouping for other endpoints
        path_parts = path.split('/')
        if len(path_parts) > 3:
            return '/'.join(path_parts[:4])  # Group by first 3 levels
        
        return path or '/'


class SystemMetricsCollector:
    """
    Collector for system-level metrics.
    """
    
    def __init__(self):
        self._last_collection = 0
        self._collection_interval = 30  # seconds
    
    async def collect_system_metrics(self) -> None:
        """Collect and update system metrics."""
        current_time = time.time()
        
        # Only collect system metrics every 30 seconds to reduce overhead
        if current_time - self._last_collection < self._collection_interval:
            return
        
        try:
            import psutil
            
            # Memory metrics
            memory = psutil.virtual_memory()
            memory_usage.labels(type='total').set(memory.total)
            memory_usage.labels(type='used').set(memory.used)
            memory_usage.labels(type='available').set(memory.available)
            
            # CPU metrics
            cpu_percent = psutil.cpu_percent(interval=None)  # Non-blocking
            cpu_usage.set(cpu_percent)
            
            # Process-specific metrics
            process = psutil.Process()
            process_memory = process.memory_info()
            memory_usage.labels(type='process_rss').set(process_memory.rss)
            memory_usage.labels(type='process_vms').set(process_memory.vms)
            
            self._last_collection = current_time
            
        except ImportError:
            logger.warning("psutil not available for system metrics")
        except Exception as e:
            logger.error(f"Failed to collect system metrics: {e}")
            error_count.labels(
                error_type=type(e).__name__,
                component="system_metrics"
            ).inc()


class BusinessMetricsCollector:
    """
    Collector for business-specific metrics.
    """
    
    @staticmethod
    async def update_database_metrics():
        """Update database-related metrics."""
        try:
            from app.core.database import engine
            
            # Get connection pool status
            pool = engine.pool
            if pool:
                database_connection_pool.set(pool.checkedout())
            
        except Exception as e:
            logger.error(f"Failed to collect database metrics: {e}")
            error_count.labels(
                error_type=type(e).__name__,
                component="database_metrics"
            ).inc()
    
    @staticmethod
    async def update_cache_metrics():
        """Update cache-related metrics."""
        try:
            from app.core.cache import cache_manager
            
            if cache_manager._initialized:
                stats = await cache_manager.get_stats()
                
                # Update cache operation counters
                cache_operations.labels(operation='hit', status='success')._value._value = stats.get('hits', 0)
                cache_operations.labels(operation='miss', status='success')._value._value = stats.get('misses', 0)
                cache_operations.labels(operation='set', status='success')._value._value = stats.get('sets', 0)
                cache_operations.labels(operation='delete', status='success')._value._value = stats.get('deletes', 0)
                cache_operations.labels(operation='error', status='failed')._value._value = stats.get('errors', 0)
            
        except Exception as e:
            logger.error(f"Failed to collect cache metrics: {e}")
            error_count.labels(
                error_type=type(e).__name__,
                component="cache_metrics"
            ).inc()


# Global collectors
system_collector = SystemMetricsCollector()
business_collector = BusinessMetricsCollector()


def track_database_operation(operation: str, table: str):
    """Decorator to track database operations."""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            status = 'success'
            
            try:
                result = await func(*args, **kwargs)
                return result
            except Exception as e:
                status = 'failed'
                error_count.labels(
                    error_type=type(e).__name__,
                    component="database"
                ).inc()
                raise
            finally:
                # Record operation
                database_operations.labels(
                    operation=operation,
                    table=table,
                    status=status
                ).inc()
                
                # Check for slow queries
                duration = time.time() - start_time
                if duration > 1.0:  # Queries taking more than 1 second
                    slow_queries.labels(query_type=operation).inc()
        
        return wrapper
    return decorator


def track_security_event(event_type: str, severity: str = 'info'):
    """Record security-related events."""
    security_events.labels(
        event_type=event_type,
        severity=severity
    ).inc()
    
    logger.info(
        f"Security event: {event_type}",
        extra={
            "event_type": event_type,
            "severity": severity,
            "component": "security"
        }
    )


async def collect_all_metrics():
    """Collect all application metrics."""
    await system_collector.collect_system_metrics()
    await business_collector.update_database_metrics()
    await business_collector.update_cache_metrics()


def setup_application_info():
    """Set up application information metric."""
    from app.core.config import settings
    
    app_info.info({
        'version': getattr(settings, 'app_version', '2.0.0'),
        'environment': getattr(settings, 'environment', 'development'),
        'python_version': f"{__import__('sys').version_info.major}.{__import__('sys').version_info.minor}",
        'build_time': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
    })


async def get_metrics() -> str:
    """
    Get Prometheus metrics in text format.
    
    Returns:
        str: Prometheus metrics
    """
    try:
        # Collect fresh metrics before export
        await collect_all_metrics()
        
        # Generate metrics output
        return generate_latest(app_registry).decode('utf-8')
        
    except Exception as e:
        logger.error(f"Failed to generate metrics: {e}")
        error_count.labels(
            error_type=type(e).__name__,
            component="metrics_export"
        ).inc()
        raise


def get_metrics_summary() -> Dict[str, Any]:
    """
    Get a summary of key metrics for health checks.
    
    Returns:
        Dict[str, Any]: Metrics summary
    """
    try:
        # Get sample values from metrics
        return {
            "total_requests": request_count._value.sum(),
            "error_rate": error_count._value.sum() / max(request_count._value.sum(), 1) * 100,
            "active_connections": database_connection_pool._value._value,
            "cache_hit_rate": (
                cache_operations.labels(operation='hit', status='success')._value._value / 
                max(
                    cache_operations.labels(operation='hit', status='success')._value._value + 
                    cache_operations.labels(operation='miss', status='success')._value._value,
                    1
                ) * 100
            ),
            "slow_queries": slow_queries._value.sum(),
        }
    except Exception as e:
        logger.error(f"Failed to get metrics summary: {e}")
        return {"error": "Failed to collect metrics summary"}


# Initialize application info on import
setup_application_info()