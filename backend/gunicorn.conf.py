"""
Gunicorn configuration for production deployment.
Optimized for high-performance FastAPI applications.
"""

import multiprocessing
import os

# Server socket
bind = f"0.0.0.0:{os.getenv('PORT', 8000)}"
backlog = 2048

# Worker processes
workers = int(os.getenv('WORKERS', multiprocessing.cpu_count() * 2 + 1))
worker_class = "uvicorn.workers.UvicornWorker"
worker_connections = 1000
max_requests = 10000
max_requests_jitter = 1000

# Timeout settings
timeout = 30
keepalive = 5
graceful_timeout = 30

# Preload application for better memory usage
preload_app = True

# Logging
access_logfile = "-"
error_logfile = "-" 
log_level = os.getenv('LOG_LEVEL', 'info')
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# Process naming
proc_name = 'syferstack-api'

# Security
limit_request_line = 4094
limit_request_fields = 100
limit_request_field_size = 8190

# SSL (if certificates are provided)
keyfile = os.getenv('SSL_KEYFILE')
certfile = os.getenv('SSL_CERTFILE')
ssl_version = 2  # TLS 1.2+
ciphers = 'TLSv1.2'

# Performance tuning
worker_tmp_dir = '/dev/shm'  # Use RAM for worker temporary files
enable_stdio_inheritance = True

# Monitoring
capture_output = True
enable_stdio_inheritance = True

# Hooks for lifecycle management
def on_starting(server):
    """Called just before the master process is initialized."""
    server.log.info("🚀 SyferStack API starting with Gunicorn")
    server.log.info(f"Workers: {workers}")
    server.log.info(f"Worker class: {worker_class}")
    server.log.info(f"Bind: {bind}")

def when_ready(server):
    """Called just after the server is started."""
    server.log.info("✅ SyferStack API is ready to serve requests")

def worker_int(worker):
    """Called just after a worker exited on SIGINT or SIGQUIT."""
    worker.log.info(f"Worker {worker.pid} received INT/QUIT signal")

def on_exit(server):
    """Called just before exiting."""
    server.log.info("🛑 SyferStack API shutting down")

def post_fork(server, worker):
    """Called just after a worker has been forked."""
    server.log.info(f"Worker {worker.pid} spawned")

def pre_fork(server, worker):
    """Called just prior to forking the worker subprocess."""
    pass

def worker_abort(worker):
    """Called when a worker received the SIGABRT signal."""
    worker.log.info(f"Worker {worker.pid} received SIGABRT signal")