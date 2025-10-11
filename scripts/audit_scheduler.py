#!/usr/bin/env python3
"""
SyferStackV2 – Secure Audit Scheduler
Schedules and manages automated security audits with proper authentication and logging.
"""

import os
import sys
import time
import signal
import hashlib
import hmac
import json
import logging
import threading
import subprocess
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any
import argparse

# Configure secure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("audit_scheduler.log", mode="a")
    ]
)
logger = logging.getLogger(__name__)


class SecureAuditScheduler:
    """
    Secure audit scheduler with authentication and comprehensive logging.
    """
    
    def __init__(self, config_file: str = "audit_config.json"):
        """
        Initialize the secure audit scheduler.
        
        Args:
            config_file: Path to configuration file
        """
        self.config_file = config_file
        self.config = self._load_config()
        self.running = False
        self.audit_thread = None
        self.last_audit_time = None
        
        # Validate configuration
        self._validate_config()
        
        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
    def _load_config(self) -> Dict[str, Any]:
        """
        Load and validate scheduler configuration.
        
        Returns:
            Dict[str, Any]: Configuration dictionary
            
        Raises:
            ValueError: If configuration is invalid
        """
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
            else:
                # Default configuration
                config = {
                    "audit_interval_hours": 24,
                    "max_audit_duration_minutes": 60,
                    "audit_script_path": "./local_audit.py",
                    "reports_retention_days": 30,
                    "enable_authentication": True,
                    "api_key_hash": None,  # To be set by admin
                    "allowed_networks": ["127.0.0.1", "::1"],
                    "enable_notifications": False,
                    "notification_webhook": None,
                }
                
                # Save default config
                self._save_config(config)
                
            return config
            
        except Exception as e:
            logger.error(f"Failed to load configuration: {e}")
            raise ValueError(f"Configuration loading failed: {e}")
    
    def _save_config(self, config: Dict[str, Any]) -> None:
        """
        Save configuration to file with secure permissions.
        
        Args:
            config: Configuration to save
        """
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2)
            
            # Set secure file permissions (readable by owner only)
            os.chmod(self.config_file, 0o600)
            
        except Exception as e:
            logger.error(f"Failed to save configuration: {e}")
    
    def _validate_config(self) -> None:
        """
        Validate configuration parameters for security.
        
        Raises:
            ValueError: If configuration is invalid
        """
        required_keys = [
            "audit_interval_hours", "max_audit_duration_minutes", 
            "audit_script_path", "reports_retention_days"
        ]
        
        for key in required_keys:
            if key not in self.config:
                raise ValueError(f"Missing required configuration: {key}")
        
        # Validate numeric values
        if not isinstance(self.config["audit_interval_hours"], (int, float)) or self.config["audit_interval_hours"] <= 0:
            raise ValueError("audit_interval_hours must be a positive number")
        
        if not isinstance(self.config["max_audit_duration_minutes"], int) or self.config["max_audit_duration_minutes"] <= 0:
            raise ValueError("max_audit_duration_minutes must be a positive integer")
        
        # Validate audit script path
        script_path = Path(self.config["audit_script_path"])
        if not script_path.exists() or not script_path.is_file():
            logger.warning(f"Audit script not found: {script_path}")
        
        logger.info("Configuration validation completed successfully")
    
    def set_api_key(self, api_key: str) -> None:
        """
        Set API key for authentication.
        
        Args:
            api_key: API key string
        """
        if not api_key or len(api_key) < 32:
            raise ValueError("API key must be at least 32 characters long")
        
        # Hash the API key for secure storage
        key_hash = hashlib.sha256(api_key.encode()).hexdigest()
        self.config["api_key_hash"] = key_hash
        
        # Save updated configuration
        self._save_config(self.config)
        
        logger.info("API key has been set successfully")
    
    def validate_api_key(self, provided_key: str) -> bool:
        """
        Validate provided API key against stored hash.
        
        Args:
            provided_key: API key to validate
            
        Returns:
            bool: True if key is valid
        """
        if not self.config.get("enable_authentication", True):
            return True
        
        if not self.config.get("api_key_hash"):
            logger.error("No API key configured")
            return False
        
        if not provided_key:
            return False
        
        # Hash provided key and compare
        provided_hash = hashlib.sha256(provided_key.encode()).hexdigest()
        stored_hash = self.config["api_key_hash"]
        
        # Use constant-time comparison to prevent timing attacks
        return hmac.compare_digest(provided_hash, stored_hash)
    
    def start_scheduler(self) -> None:
        """
        Start the audit scheduler in a separate thread.
        """
        if self.running:
            logger.warning("Scheduler is already running")
            return
        
        self.running = True
        self.audit_thread = threading.Thread(target=self._scheduler_loop, daemon=True)
        self.audit_thread.start()
        
        logger.info(f"Audit scheduler started (interval: {self.config['audit_interval_hours']} hours)")
    
    def stop_scheduler(self) -> None:
        """
        Stop the audit scheduler gracefully.
        """
        self.running = False
        
        if self.audit_thread and self.audit_thread.is_alive():
            logger.info("Stopping audit scheduler...")
            self.audit_thread.join(timeout=30)
            
        logger.info("Audit scheduler stopped")
    
    def _scheduler_loop(self) -> None:
        """
        Main scheduler loop that runs audits at configured intervals.
        """
        while self.running:
            try:
                current_time = datetime.now()
                
                # Check if it's time for next audit
                if self._should_run_audit(current_time):
                    logger.info("Starting scheduled audit")
                    self._run_audit()
                    self.last_audit_time = current_time
                
                # Clean up old reports
                self._cleanup_old_reports()
                
                # Sleep for 1 hour before next check
                time.sleep(3600)
                
            except Exception as e:
                logger.error(f"Error in scheduler loop: {e}")
                time.sleep(300)  # Sleep 5 minutes on error
    
    def _should_run_audit(self, current_time: datetime) -> bool:
        """
        Determine if an audit should be run now.
        
        Args:
            current_time: Current timestamp
            
        Returns:
            bool: True if audit should run
        """
        if self.last_audit_time is None:
            return True
        
        interval = timedelta(hours=self.config["audit_interval_hours"])
        return current_time >= (self.last_audit_time + interval)
    
    def _run_audit(self) -> bool:
        """
        Execute the audit script with proper monitoring.
        
        Returns:
            bool: True if audit completed successfully
        """
        try:
            script_path = self.config["audit_script_path"]
            timeout = self.config["max_audit_duration_minutes"] * 60
            
            logger.info(f"Executing audit script: {script_path}")
            
            # Run audit script with timeout
            result = subprocess.run(
                [sys.executable, script_path],
                timeout=timeout,
                capture_output=True,
                text=True,
                cwd=os.path.dirname(os.path.abspath(script_path))
            )
            
            # Log results
            if result.returncode == 0:
                logger.info("Audit completed successfully")
                if result.stdout:
                    logger.debug(f"Audit output: {result.stdout[:1000]}")
                return True
            else:
                logger.error(f"Audit failed with return code: {result.returncode}")
                if result.stderr:
                    logger.error(f"Audit error: {result.stderr[:1000]}")
                return False
                
        except subprocess.TimeoutExpired:
            logger.error(f"Audit timed out after {timeout} seconds")
            return False
        except Exception as e:
            logger.error(f"Failed to run audit: {e}")
            return False
    
    def _cleanup_old_reports(self) -> None:
        """
        Clean up old audit reports based on retention policy.
        """
        try:
            reports_dir = Path("reports")
            if not reports_dir.exists():
                return
            
            retention_days = self.config["reports_retention_days"]
            cutoff_time = datetime.now() - timedelta(days=retention_days)
            
            cleaned_count = 0
            for report_file in reports_dir.glob("*.json"):
                if report_file.stat().st_mtime < cutoff_time.timestamp():
                    try:
                        report_file.unlink()
                        cleaned_count += 1
                    except Exception as e:
                        logger.warning(f"Failed to delete old report {report_file}: {e}")
            
            if cleaned_count > 0:
                logger.info(f"Cleaned up {cleaned_count} old audit reports")
                
        except Exception as e:
            logger.error(f"Failed to cleanup old reports: {e}")
    
    def _signal_handler(self, signum: int, frame) -> None:
        """
        Handle shutdown signals gracefully.
        
        Args:
            signum: Signal number
            frame: Current stack frame
        """
        logger.info(f"Received signal {signum}, shutting down gracefully")
        self.stop_scheduler()
        sys.exit(0)
    
    def get_status(self) -> Dict[str, Any]:
        """
        Get current scheduler status.
        
        Returns:
            Dict[str, Any]: Status information
        """
        return {
            "running": self.running,
            "last_audit_time": self.last_audit_time.isoformat() if self.last_audit_time else None,
            "next_audit_time": (
                self.last_audit_time + timedelta(hours=self.config["audit_interval_hours"])
            ).isoformat() if self.last_audit_time else "immediate",
            "audit_interval_hours": self.config["audit_interval_hours"],
            "config_file": self.config_file,
        }


def main():
    """
    Main entry point for the audit scheduler.
    """
    parser = argparse.ArgumentParser(description="SyferStackV2 Secure Audit Scheduler")
    parser.add_argument("--config", default="audit_config.json", help="Configuration file path")
    parser.add_argument("--set-api-key", help="Set API key for authentication")
    parser.add_argument("--run-once", action="store_true", help="Run audit once and exit")
    parser.add_argument("--status", action="store_true", help="Show scheduler status")
    
    args = parser.parse_args()
    
    try:
        scheduler = SecureAuditScheduler(args.config)
        
        if args.set_api_key:
            scheduler.set_api_key(args.set_api_key)
            print("API key has been set successfully")
            return
        
        if args.status:
            status = scheduler.get_status()
            print(json.dumps(status, indent=2))
            return
        
        if args.run_once:
            logger.info("Running single audit")
            success = scheduler._run_audit()
            sys.exit(0 if success else 1)
        
        # Start continuous scheduler
        logger.info("Starting audit scheduler in continuous mode")
        scheduler.start_scheduler()
        
        # Keep main thread alive
        try:
            while scheduler.running:
                time.sleep(60)
        except KeyboardInterrupt:
            logger.info("Received interrupt, shutting down")
        finally:
            scheduler.stop_scheduler()
            
    except Exception as e:
        logger.error(f"Scheduler failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()