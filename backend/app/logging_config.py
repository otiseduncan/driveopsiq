"""
Secure logging configuration with enhanced security measures and error handling.
"""
import logging
import logging.handlers
import os
import re
import sys
import time
from pathlib import Path
from typing import Any, Dict, Optional, Union
import structlog
from pythonjsonlogger import jsonlogger

from app.core.config import settings


class SecureFormatter(jsonlogger.JsonFormatter):
    """
    Enhanced JSON formatter with security filtering and log injection prevention.
    """
    
    # Patterns that could indicate log injection attempts
    DANGEROUS_PATTERNS = [
        r'[\r\n]',  # CRLF injection
        r'%[0-9a-fA-F]{2}',  # URL encoding
        r'\\[ux][0-9a-fA-F]+',  # Unicode/hex escaping
        r'<script[^>]*>.*?</script>',  # Script tags
        r'javascript:',  # JavaScript protocol
        r'vbscript:',  # VBScript protocol
        r'onload=|onerror=|onclick=',  # Event handlers
    ]
    
    def __init__(self, *args, **kwargs):
        """Initialize the secure formatter."""
        super().__init__(*args, **kwargs)
        self._compiled_patterns = [re.compile(pattern, re.IGNORECASE | re.DOTALL) 
                                 for pattern in self.DANGEROUS_PATTERNS]
    
    def _sanitize_message(self, message: str) -> str:
        """
        Sanitize log message to prevent injection attacks.
        
        Args:
            message: Raw log message
            
        Returns:
            str: Sanitized message
        """
        if not isinstance(message, str):
            return str(message)
        
        # Remove dangerous patterns
        sanitized = message
        for pattern in self._compiled_patterns:
            sanitized = pattern.sub('[FILTERED]', sanitized)
        
        # Truncate extremely long messages to prevent log flooding
        if len(sanitized) > 4096:
            sanitized = sanitized[:4093] + "..."
            
        return sanitized
    
    def format(self, record: logging.LogRecord) -> str:
        """
        Format log record with security sanitization.
        
        Args:
            record: Log record to format
            
        Returns:
            str: Formatted and sanitized log entry
        """
        try:
            # Sanitize the main message
            if hasattr(record, 'msg') and record.msg:
                if isinstance(record.msg, str):
                    record.msg = self._sanitize_message(record.msg)
                
            # Sanitize additional fields
            if hasattr(record, 'args') and record.args:
                record.args = tuple(
                    self._sanitize_message(str(arg)) if isinstance(arg, str) else arg
                    for arg in record.args
                )
            
            # Add security context
            record.security_sanitized = True
            record.application = "SyferStack-API"
            
            return super().format(record)
            
        except Exception as e:
            # Fallback formatting if sanitization fails
            error_record = logging.LogRecord(
                name="logging.security",
                level=logging.ERROR,
                pathname="",
                lineno=0,
                msg=f"Log formatting error: {str(e)}",
                args=(),
                exc_info=None
            )
            return super().format(error_record)


class RotatingFileHandlerSecure(logging.handlers.RotatingFileHandler):
    """
    Enhanced rotating file handler with secure file permissions and error handling.
    """
    
    def __init__(self, filename: Union[str, Path], mode: str = 'a', 
                 maxBytes: int = 10 * 1024 * 1024,  # 10MB default
                 backupCount: int = 5, encoding: Optional[str] = 'utf-8',
                 delay: bool = False, errors: Optional[str] = None):
        """
        Initialize secure rotating file handler.
        
        Args:
            filename: Log file path
            mode: File open mode  
            maxBytes: Maximum file size before rotation
            backupCount: Number of backup files to keep
            encoding: File encoding
            delay: Whether to delay file opening
            errors: Error handling strategy
        """
        # Ensure log directory exists with secure permissions
        log_path = Path(filename)
        log_path.parent.mkdir(mode=0o755, parents=True, exist_ok=True)
        
        super().__init__(
            filename=str(log_path),
            mode=mode,
            maxBytes=maxBytes,
            backupCount=backupCount,
            encoding=encoding,
            delay=delay,
            errors=errors
        )
        
    def _open(self):
        """Open log file with secure permissions."""
        stream = super()._open()
        
        # Set secure file permissions (readable by owner and group only)
        try:
            os.chmod(self.baseFilename, 0o640)
        except (OSError, AttributeError):
            # Permissions may not be supported on all systems
            pass
            
        return stream
    
    def doRollover(self):
        """Perform log rotation with enhanced error handling."""
        try:
            super().doRollover()
            
            # Set secure permissions on rotated files
            try:
                for i in range(1, self.backupCount + 1):
                    backup_name = f"{self.baseFilename}.{i}"
                    if os.path.exists(backup_name):
                        os.chmod(backup_name, 0o640)
            except (OSError, AttributeError):
                pass
                
        except Exception as e:
            # Log rotation failure should not crash the application
            print(f"Log rotation failed: {e}", file=sys.stderr)


def _create_secure_handler(handler_type: str, **kwargs) -> logging.Handler:
    """
    Create a logging handler with security configurations.
    
    Args:
        handler_type: Type of handler ('console', 'file', 'syslog')
        **kwargs: Handler-specific arguments
        
    Returns:
        logging.Handler: Configured handler
        
    Raises:
        ValueError: If handler type is unsupported
    """
    handler: logging.Handler
    
    if handler_type == "console":
        handler = logging.StreamHandler(sys.stdout)
        
    elif handler_type == "file":
        log_dir = kwargs.get("log_dir", "logs")
        log_file = kwargs.get("log_file", "syferstack.log")
        max_bytes = kwargs.get("max_bytes", 10 * 1024 * 1024)  # 10MB
        backup_count = kwargs.get("backup_count", 5)
        
        log_path = Path(log_dir) / log_file
        handler = RotatingFileHandlerSecure(
            filename=log_path,
            maxBytes=max_bytes,
            backupCount=backup_count
        )
        
    elif handler_type == "syslog":
        # Syslog handler for production environments
        handler = logging.handlers.SysLogHandler(
            address=kwargs.get("syslog_address", "/dev/log"),
            facility=kwargs.get("syslog_facility", logging.handlers.SysLogHandler.LOG_LOCAL0)
        )
        
    else:
        raise ValueError(f"Unsupported handler type: {handler_type}")
    
    # Apply secure formatter
    formatter = SecureFormatter(
        "%(asctime)s %(levelname)s %(name)s %(message)s %(pathname)s %(lineno)d %(funcName)s"
    )
    handler.setFormatter(formatter)
    
    return handler


def setup_json_logging(
    level: Union[str, int] = "INFO",
    handlers: Optional[list] = None,
    enable_structlog: bool = True
) -> None:
    """
    Setup comprehensive JSON logging with security enhancements.
    
    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        handlers: List of handler configurations
        enable_structlog: Whether to enable structured logging
        
    Raises:
        ValueError: If configuration is invalid
    """
    try:
        # Validate log level
        if isinstance(level, str):
            numeric_level = getattr(logging, level.upper(), None)
            if numeric_level is None:
                raise ValueError(f"Invalid log level: {level}")
        else:
            numeric_level = level
        
        # Default handler configuration
        if handlers is None:
            handlers = [
                {"type": "console"},
                {
                    "type": "file", 
                    "log_dir": "logs",
                    "log_file": "syferstack.log",
                    "max_bytes": 10 * 1024 * 1024,
                    "backup_count": 5
                }
            ]
        
        # Configure root logger
        root = logging.getLogger()
        root.handlers.clear()
        root.setLevel(numeric_level)
        
        # Create and add handlers
        for handler_config in handlers:
            handler_type = handler_config.pop("type")
            try:
                handler = _create_secure_handler(handler_type, **handler_config)
                root.addHandler(handler)
            except Exception as e:
                print(f"Failed to create {handler_type} handler: {e}", file=sys.stderr)
                continue
        
        # Configure third-party loggers to prevent information leakage
        noisy_loggers = [
            "uvicorn.access",
            "sqlalchemy.engine",
            "httpx",
            "httpcore",
            "asyncio",
        ]
        
        for logger_name in noisy_loggers:
            logger = logging.getLogger(logger_name)
            # Set to WARNING to reduce noise but capture important events
            logger.setLevel(logging.WARNING)
        
        # Setup structured logging if enabled
        if enable_structlog:
            structlog.configure(
                processors=[
                    structlog.contextvars.merge_contextvars,
                    structlog.processors.add_log_level,
                    structlog.processors.TimeStamper(fmt="iso"),
                    structlog.processors.JSONRenderer()
                ],
                wrapper_class=structlog.make_filtering_bound_logger(numeric_level),
                logger_factory=structlog.PrintLoggerFactory(),
                cache_logger_on_first_use=True,
            )
        
        # Log successful configuration
        logger = logging.getLogger(__name__)
        logger.info("Secure logging configured successfully", extra={
            "log_level": logging.getLevelName(numeric_level),
            "handlers_count": len(root.handlers),
            "structured_logging": enable_structlog,
            "timestamp": time.time(),
        })
        
    except Exception as e:
        print(f"Failed to setup logging: {e}", file=sys.stderr)
        # Fallback to basic console logging
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            stream=sys.stdout
        )


def get_security_logger(name: str) -> logging.Logger:
    """
    Get a logger specifically configured for security events.
    
    Args:
        name: Logger name
        
    Returns:
        logging.Logger: Security-focused logger
    """
    logger = logging.getLogger(f"security.{name}")
    
    # Ensure security events are always logged
    if logger.level > logging.INFO:
        logger.setLevel(logging.INFO)
    
    return logger


# Security event logging helpers
def log_security_event(
    event_type: str,
    details: Dict[str, Any],
    level: str = "WARNING",
    logger_name: Optional[str] = None
) -> None:
    """
    Log a security event with standardized format.
    
    Args:
        event_type: Type of security event
        details: Event details
        level: Log level
        logger_name: Optional logger name
    """
    logger = get_security_logger(logger_name or "events")
    
    log_entry = {
        "event_type": event_type,
        "timestamp": time.time(),
        "details": details,
        "application": "SyferStack-API",
    }
    
    log_level = getattr(logging, level.upper(), logging.WARNING)
    logger.log(log_level, f"Security event: {event_type}", extra=log_entry)