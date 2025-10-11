#!/usr/bin/env python3
"""
Production server configuration with performance optimizations.
Supports uvicorn with multiple workers, uvloop, and h11 for maximum performance.
"""

import multiprocessing
import os
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional

import uvicorn
from uvicorn.config import LOGGING_CONFIG

# Performance imports
try:
    import uvloop
    UVLOOP_AVAILABLE = True
except ImportError:
    UVLOOP_AVAILABLE = False

try:
    import httptools
    HTTPTOOLS_AVAILABLE = True
except ImportError:
    HTTPTOOLS_AVAILABLE = False


class ProductionConfig:
    """
    Production configuration class with performance optimizations.
    """
    
    def __init__(self):
        self.workers = self._calculate_workers()
        self.host = os.getenv("HOST", "0.0.0.0")
        self.port = int(os.getenv("PORT", 8000))
        self.log_level = os.getenv("LOG_LEVEL", "info").lower()
        self.access_log = os.getenv("ACCESS_LOG", "true").lower() == "true"
        self.reload = os.getenv("RELOAD", "false").lower() == "true"
        self.debug = os.getenv("DEBUG", "false").lower() == "true"
    
    def _calculate_workers(self) -> int:
        """
        Calculate optimal number of workers based on CPU count and memory.
        
        Returns:
            int: Optimal worker count
        """
        # Get environment override
        workers_env = os.getenv("WORKERS")
        if workers_env:
            try:
                return max(1, int(workers_env))
            except ValueError:
                pass
        
        # Calculate based on system resources
        cpu_count = multiprocessing.cpu_count()
        
        # For I/O bound applications (typical for APIs), use more workers
        # Formula: (2 x CPU cores) + 1, capped at reasonable limits
        workers = min(max(1, (2 * cpu_count) + 1), 16)
        
        # Reduce workers if in development or limited memory environments
        if self.debug or os.getenv("ENVIRONMENT") == "development":
            workers = min(workers, 4)
        
        return workers
    
    def get_uvicorn_config(self) -> Dict[str, Any]:
        """
        Get optimized uvicorn configuration.
        
        Returns:
            Dict[str, Any]: Uvicorn configuration
        """
        config = {
            "app": "app.main:app",
            "host": self.host,
            "port": self.port,
            "workers": self.workers,
            "log_level": self.log_level,
            "access_log": self.access_log,
            "reload": self.reload,
            "reload_dirs": ["app"] if self.reload else None,
            "reload_excludes": ["*.pyc", "__pycache__", "*.log", "reports/*"] if self.reload else None,
        }
        
        # Performance optimizations
        if UVLOOP_AVAILABLE:
            config["loop"] = "uvloop"
            print("✓ Using uvloop for enhanced performance")
        else:
            print("⚠ uvloop not available, using asyncio default loop")
        
        if HTTPTOOLS_AVAILABLE:
            config["http"] = "httptools"
            print("✓ Using httptools for faster HTTP parsing")
        else:
            config["http"] = "h11"
            print("⚠ httptools not available, using h11")
        
        # Production-specific settings
        if not self.debug:
            config.update({
                "interface": "asgi3",
                "lifespan": "on",
                "timeout_keep_alive": 5,
                "timeout_graceful_shutdown": 10,
                "limit_concurrency": 1000,
                "limit_max_requests": 10000,
                "backlog": 2048,
            })
        
        # SSL/TLS configuration (if certificates are available)
        ssl_cert = os.getenv("SSL_CERT_PATH")
        ssl_key = os.getenv("SSL_KEY_PATH")
        
        if ssl_cert and ssl_key:
            cert_path = Path(ssl_cert)
            key_path = Path(ssl_key)
            
            if cert_path.exists() and key_path.exists():
                config.update({
                    "ssl_certfile": str(cert_path),
                    "ssl_keyfile": str(key_path),
                    "ssl_version": 2,  # TLS 1.2+
                    "ssl_cert_reqs": 0,  # No client certificate required
                })
                print(f"✓ SSL/TLS enabled with certificate: {cert_path}")
            else:
                print(f"⚠ SSL certificate files not found: {ssl_cert}, {ssl_key}")
        
        return config
    
    def get_gunicorn_config(self) -> Dict[str, Any]:
        """
        Alternative: Get Gunicorn configuration for deployment.
        
        Returns:
            Dict[str, Any]: Gunicorn configuration
        """
        return {
            "bind": f"{self.host}:{self.port}",
            "workers": self.workers,
            "worker_class": "uvicorn.workers.UvicornWorker",
            "worker_connections": 1000,
            "max_requests": 10000,
            "max_requests_jitter": 1000,
            "timeout": 30,
            "keepalive": 5,
            "preload_app": True,
            "access_logfile": "-" if self.access_log else None,
            "error_logfile": "-",
            "log_level": self.log_level,
            "capture_output": True,
            "enable_stdio_inheritance": True,
        }
    
    def setup_logging(self) -> None:
        """Configure optimized logging for production."""
        # Enhanced logging configuration
        log_config = LOGGING_CONFIG.copy()
        
        # Add performance-focused formatters
        log_config["formatters"]["access_performance"] = {
            "format": "%(asctime)s %(levelprefix)s %(client_addr)s - \"%(request_line)s\" %(status_code)s %(response_time)s",
            "class": "uvicorn.logging.AccessFormatter",
        }
        
        # Configure file logging for production
        if not self.debug:
            log_config["handlers"]["file"] = {
                "class": "logging.handlers.RotatingFileHandler",
                "filename": "logs/access.log",
                "maxBytes": 10 * 1024 * 1024,  # 10MB
                "backupCount": 5,
                "formatter": "access_performance",
            }
            
            log_config["loggers"]["uvicorn.access"]["handlers"].append("file")
        
        # Set log levels based on environment
        if self.log_level == "debug":
            log_config["loggers"]["uvicorn"]["level"] = "DEBUG"
            log_config["loggers"]["uvicorn.error"]["level"] = "DEBUG"
        
        return log_config
    
    def print_startup_info(self) -> None:
        """Print startup information and performance tips."""
        print("\n" + "="*60)
        print("🚀 SyferStack Production Server Starting")
        print("="*60)
        print(f"Host: {self.host}")
        print(f"Port: {self.port}")
        print(f"Workers: {self.workers}")
        print(f"Log Level: {self.log_level}")
        
        # Performance status
        print(f"\nPerformance Features:")
        print(f"  uvloop: {'✓ Enabled' if UVLOOP_AVAILABLE else '✗ Not Available'}")
        print(f"  httptools: {'✓ Enabled' if HTTPTOOLS_AVAILABLE else '✗ Using h11'}")
        print(f"  Multi-worker: {'✓ Enabled' if self.workers > 1 else '✗ Single worker'}")
        
        # Recommendations
        print(f"\nOptimization Tips:")
        if not UVLOOP_AVAILABLE:
            print("  • Install uvloop: pip install uvloop")
        if not HTTPTOOLS_AVAILABLE:
            print("  • Install httptools: pip install httptools")
        if self.workers == 1:
            print("  • Set WORKERS env var for multi-worker setup")
        
        print("="*60 + "\n")


def run_production_server() -> None:
    """
    Run the production server with optimal configuration.
    """
    config = ProductionConfig()
    config.print_startup_info()
    
    # Setup logging
    log_config = config.setup_logging()
    
    # Create logs directory
    Path("logs").mkdir(exist_ok=True)
    
    # Get uvicorn configuration
    uvicorn_config = config.get_uvicorn_config()
    
    # Update log config
    uvicorn_config["log_config"] = log_config
    
    # Run server
    try:
        uvicorn.run(**uvicorn_config)
    except KeyboardInterrupt:
        print("\n🛑 Server shutdown requested")
    except Exception as e:
        print(f"\n❌ Server failed to start: {e}")
        raise


def run_with_gunicorn() -> None:
    """
    Alternative: Run with Gunicorn for advanced process management.
    """
    config = ProductionConfig()
    gunicorn_config = config.get_gunicorn_config()
    
    print("Starting with Gunicorn configuration:")
    for key, value in gunicorn_config.items():
        if value is not None:
            print(f"  {key}: {value}")
    
    # Note: This would typically be used in a separate deployment script
    # or with gunicorn command line: gunicorn -c gunicorn.conf.py app.main:app
    print("\nTo use Gunicorn, run:")
    print("gunicorn -c gunicorn.conf.py app.main:app")


def create_systemd_service() -> str:
    """
    Create systemd service configuration for production deployment.
    
    Returns:
        str: Systemd service configuration
    """
    config = ProductionConfig()
    
    service_config = f"""[Unit]
Description=SyferStack FastAPI Application
After=network.target

[Service]
Type=exec
User=www-data
Group=www-data
WorkingDirectory=/opt/syferstack
Environment="PATH=/opt/syferstack/venv/bin"
Environment="PYTHONPATH=/opt/syferstack"
Environment="WORKERS={config.workers}"
Environment="HOST={config.host}"
Environment="PORT={config.port}"
Environment="LOG_LEVEL={config.log_level}"
ExecStart=/opt/syferstack/venv/bin/python -m app.production
ExecReload=/bin/kill -HUP $MAINPID
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal
SyslogIdentifier=syferstack

[Install]
WantedBy=multi-user.target
"""
    
    return service_config


def create_docker_config() -> str:
    """
    Create Docker configuration for production deployment.
    
    Returns:
        str: Docker configuration optimizations
    """
    config = ProductionConfig()
    
    dockerfile_additions = f"""
# Production optimizations
RUN pip install uvloop httptools

# Set optimal worker count
ENV WORKERS={config.workers}
ENV LOG_LEVEL=info
ENV PYTHONUNBUFFERED=1
ENV PYTHONIOENCODING=utf-8

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \\
    CMD curl -f http://localhost:8000/health || exit 1

# Use production command
CMD ["python", "-m", "app.production"]
"""
    
    return dockerfile_additions


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == "systemd":
            print(create_systemd_service())
        elif command == "docker":
            print(create_docker_config())
        elif command == "gunicorn":
            run_with_gunicorn()
        else:
            print(f"Unknown command: {command}")
            print("Available commands: systemd, docker, gunicorn")
    else:
        # Default: run with uvicorn
        run_production_server()