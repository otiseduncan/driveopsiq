#!/usr/bin/env python3
"""
Enhanced Configuration Management System
Supports YAML config, environment variables, and validation
"""

import os
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
import yaml
from pydantic import BaseModel, Field, validator, ValidationError

logger = logging.getLogger(__name__)


class OllamaConfig(BaseModel):
    """Ollama LLM configuration."""
    url: str = "http://localhost:11434/api/generate"
    model: str = "llama3:8b"
    timeout: int = 120
    max_retries: int = 3
    retry_delay: float = 1.0
    backoff_factor: float = 2.0
    
    @validator('url')
    def validate_url(cls, v):
        if not (v.startswith('http://') or v.startswith('https://')):
            raise ValueError('URL must start with http:// or https://')
        return v
    
    @validator('timeout', 'max_retries')
    def validate_positive(cls, v):
        if v <= 0:
            raise ValueError('Must be positive')
        return v


class FilesConfig(BaseModel):
    """File processing configuration."""
    max_size_mb: int = 1
    max_content_chars: int = 4000
    supported_extensions: List[str] = [".py", ".js", ".ts", ".tsx"]
    exclude_patterns: List[str] = ["node_modules/**", "venv/**", "__pycache__/**"]
    
    @validator('max_size_mb', 'max_content_chars')
    def validate_positive(cls, v):
        if v <= 0:
            raise ValueError('Must be positive')
        return v
    
    @property
    def max_size_bytes(self) -> int:
        return self.max_size_mb * 1024 * 1024


class PerformanceConfig(BaseModel):
    """Performance and concurrency configuration."""
    parallel_llm_requests: int = 5
    parallel_static_tools: int = 3
    enable_caching: bool = True
    cache_duration_hours: int = 24
    
    @validator('parallel_llm_requests', 'parallel_static_tools')
    def validate_concurrency(cls, v):
        if v < 1 or v > 20:
            raise ValueError('Concurrency must be between 1 and 20')
        return v


class OutputConfig(BaseModel):
    """Output and reporting configuration."""
    reports_dir: str = "reports"
    formats: List[str] = ["json", "markdown"]
    include_metrics: bool = True
    include_git_info: bool = True
    
    @validator('formats')
    def validate_formats(cls, v):
        valid_formats = {"json", "markdown", "html", "junit", "sarif"}
        invalid = set(v) - valid_formats
        if invalid:
            raise ValueError(f'Invalid formats: {invalid}. Valid: {valid_formats}')
        return v


class SecurityConfig(BaseModel):
    """Security validation configuration."""
    validate_paths: bool = True
    prevent_traversal: bool = True
    sanitize_output: bool = True
    max_analysis_time: int = 300
    
    @validator('max_analysis_time')
    def validate_time(cls, v):
        if v < 30 or v > 1800:  # 30 seconds to 30 minutes
            raise ValueError('Analysis time must be between 30 and 1800 seconds')
        return v


class ToolConfig(BaseModel):
    """Individual tool configuration."""
    enabled: bool = True
    config_file: Optional[str] = None
    extra_args: List[str] = []


class BanditConfig(ToolConfig):
    """Bandit-specific configuration."""
    severity_level: str = "medium"
    confidence_level: str = "medium"
    
    @validator('severity_level', 'confidence_level')
    def validate_levels(cls, v):
        valid_levels = {"low", "medium", "high"}
        if v not in valid_levels:
            raise ValueError(f'Must be one of: {valid_levels}')
        return v


class ToolsConfig(BaseModel):
    """Static analysis tools configuration."""
    ruff: ToolConfig = ToolConfig()
    bandit: BanditConfig = BanditConfig()
    mypy: ToolConfig = ToolConfig()
    pylint: ToolConfig = ToolConfig(enabled=False)
    black: ToolConfig = ToolConfig(enabled=False)
    safety: ToolConfig = ToolConfig(enabled=False)


class GradingConfig(BaseModel):
    """Grading and scoring configuration."""
    weights: Dict[str, int] = {
        "security_critical": 15,
        "security_high": 10,
        "security_medium": 5,
        "security_low": 2,
        "quality_error": 8,
        "quality_warning": 3,
        "quality_info": 1
    }
    thresholds: Dict[str, int] = {
        "a_plus": 98,
        "a": 95,
        "b_plus": 90,
        "b": 85,
        "c_plus": 80,
        "c": 75,
        "d": 65
    }


class MetricsConfig(BaseModel):
    """Metrics collection configuration."""
    enabled: bool = True
    track_performance: bool = True
    track_failures: bool = True
    export_prometheus: bool = False


class LoggingConfig(BaseModel):
    """Logging configuration."""
    level: str = "INFO"
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    file: Optional[str] = None
    max_size_mb: int = 10
    backup_count: int = 5
    
    @validator('level')
    def validate_level(cls, v):
        valid_levels = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        if v.upper() not in valid_levels:
            raise ValueError(f'Must be one of: {valid_levels}')
        return v.upper()


class AuditConfig(BaseModel):
    """Main audit configuration."""
    environment: str = "development"
    ollama: OllamaConfig = OllamaConfig()
    files: FilesConfig = FilesConfig()
    performance: PerformanceConfig = PerformanceConfig()
    output: OutputConfig = OutputConfig()
    security: SecurityConfig = SecurityConfig()
    tools: ToolsConfig = ToolsConfig()
    grading: GradingConfig = GradingConfig()
    metrics: MetricsConfig = MetricsConfig()
    logging: LoggingConfig = LoggingConfig()
    
    @validator('environment')
    def validate_environment(cls, v):
        valid_envs = {"development", "testing", "production"}
        if v not in valid_envs:
            raise ValueError(f'Must be one of: {valid_envs}')
        return v
    
    class Config:
        """Pydantic configuration."""
        extra = "forbid"  # Prevent extra fields
        validate_assignment = True  # Validate on assignment


class ConfigManager:
    """Manages configuration loading and environment variable integration."""
    
    def __init__(self, config_path: Optional[Path] = None):
        self.config_path = config_path or Path("scripts/audit_config.yaml")
        self._config: Optional[AuditConfig] = None
    
    def load_config(self) -> AuditConfig:
        """Load configuration from YAML file with environment variable overrides."""
        try:
            # Load base configuration from YAML
            config_data = {}
            if self.config_path.exists():
                with open(self.config_path, 'r') as f:
                    config_data = yaml.safe_load(f) or {}
                logger.info(f"Loaded configuration from {self.config_path}")
            else:
                logger.warning(f"Configuration file not found: {self.config_path}, using defaults")
            
            # Apply environment variable overrides
            self._apply_env_overrides(config_data)
            
            # Validate and create configuration object
            self._config = AuditConfig(**config_data)
            
            # Configure logging based on config
            self._configure_logging()
            
            return self._config
            
        except ValidationError as e:
            logger.error(f"Configuration validation failed: {e}")
            raise
        except Exception as e:
            logger.error(f"Failed to load configuration: {e}")
            raise
    
    def _apply_env_overrides(self, config_data: Dict[str, Any]) -> None:
        """Apply environment variable overrides using dot notation."""
        env_mappings = {
            # Ollama configuration
            "AUDIT_OLLAMA_URL": ("ollama", "url"),
            "AUDIT_OLLAMA_MODEL": ("ollama", "model"),
            "AUDIT_OLLAMA_TIMEOUT": ("ollama", "timeout"),
            
            # Performance configuration
            "AUDIT_PARALLEL_REQUESTS": ("performance", "parallel_llm_requests"),
            "AUDIT_ENABLE_CACHE": ("performance", "enable_caching"),
            
            # Security configuration
            "AUDIT_MAX_FILE_SIZE": ("files", "max_size_mb"),
            "AUDIT_MAX_ANALYSIS_TIME": ("security", "max_analysis_time"),
            
            # Output configuration
            "AUDIT_REPORTS_DIR": ("output", "reports_dir"),
            "AUDIT_OUTPUT_FORMATS": ("output", "formats"),
            
            # Environment
            "AUDIT_ENVIRONMENT": ("environment",),
            
            # Logging
            "AUDIT_LOG_LEVEL": ("logging", "level"),
            "AUDIT_LOG_FILE": ("logging", "file"),
        }
        
        for env_var, config_path in env_mappings.items():
            value = os.getenv(env_var)
            if value is not None:
                self._set_nested_value(config_data, config_path, self._convert_env_value(value))
                logger.debug(f"Applied environment override: {env_var}={value}")
    
    def _set_nested_value(self, data: Dict[str, Any], path: tuple, value: Any) -> None:
        """Set a nested dictionary value using a path tuple."""
        current = data
        for key in path[:-1]:
            current = current.setdefault(key, {})
        current[path[-1]] = value
    
    def _convert_env_value(self, value: str) -> Union[str, int, bool, List[str]]:
        """Convert environment variable string to appropriate type."""
        # Boolean conversion
        if value.lower() in ('true', 'false'):
            return value.lower() == 'true'
        
        # Integer conversion
        if value.isdigit():
            return int(value)
        
        # List conversion (comma-separated)
        if ',' in value:
            return [item.strip() for item in value.split(',')]
        
        # String (default)
        return value
    
    def _configure_logging(self) -> None:
        """Configure logging based on configuration."""
        if not self._config:
            return
        
        log_config = self._config.logging
        
        # Configure root logger
        logging.basicConfig(
            level=getattr(logging, log_config.level),
            format=log_config.format,
            force=True
        )
        
        # Add file handler if specified
        if log_config.file:
            from logging.handlers import RotatingFileHandler
            
            log_path = Path(log_config.file)
            log_path.parent.mkdir(parents=True, exist_ok=True)
            
            handler = RotatingFileHandler(
                log_path,
                maxBytes=log_config.max_size_mb * 1024 * 1024,
                backupCount=log_config.backup_count
            )
            handler.setFormatter(logging.Formatter(log_config.format))
            logging.getLogger().addHandler(handler)
    
    @property
    def config(self) -> AuditConfig:
        """Get the loaded configuration."""
        if self._config is None:
            raise RuntimeError("Configuration not loaded. Call load_config() first.")
        return self._config
    
    def validate_environment(self) -> None:
        """Validate that the current environment is properly configured."""
        config = self.config
        
        checks = []
        
        # Check Ollama connectivity
        import requests
        try:
            response = requests.get(
                config.ollama.url.replace('/api/generate', '/api/tags'),
                timeout=5
            )
            if response.status_code == 200:
                checks.append("✅ Ollama service reachable")
            else:
                checks.append(f"❌ Ollama service returned {response.status_code}")
        except Exception as e:
            checks.append(f"❌ Ollama service unreachable: {e}")
        
        # Check reports directory
        reports_path = Path(config.output.reports_dir)
        try:
            reports_path.mkdir(parents=True, exist_ok=True)
            test_file = reports_path / ".test"
            test_file.touch()
            test_file.unlink()
            checks.append("✅ Reports directory writable")
        except Exception as e:
            checks.append(f"❌ Reports directory not writable: {e}")
        
        # Check required tools
        tools_to_check = []
        if config.tools.ruff.enabled:
            tools_to_check.append("ruff")
        if config.tools.bandit.enabled:
            tools_to_check.append("bandit")
        if config.tools.mypy.enabled:
            tools_to_check.append("mypy")
        
        for tool in tools_to_check:
            import shutil
            if shutil.which(tool):
                checks.append(f"✅ {tool} available")
            else:
                checks.append(f"❌ {tool} not found in PATH")
        
        logger.info("Environment validation results:")
        for check in checks:
            logger.info(f"  {check}")
        
        # Return validation status
        failed_checks = [check for check in checks if check.startswith("❌")]
        if failed_checks:
            logger.warning(f"Environment validation failed: {len(failed_checks)} issues found")
            return False
        else:
            logger.info("Environment validation passed")
            return True


# Example usage and testing
if __name__ == "__main__":
    config_manager = ConfigManager()
    config = config_manager.load_config()
    
    print("📋 Configuration loaded successfully!")
    print(f"Environment: {config.environment}")
    print(f"Ollama URL: {config.ollama.url}")
    print(f"Model: {config.ollama.model}")
    print(f"Reports directory: {config.output.reports_dir}")
    
    # Validate environment
    config_manager.validate_environment()