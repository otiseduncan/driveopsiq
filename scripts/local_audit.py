#!/usr/bin/env python3
"""
SyferStackV2 – Production Grade Audit System with Enhanced Security
Performs static, security, and LLM-based audits using Ollama.
Generates both JSON and Markdown summaries with comprehensive validation.
"""

import os
import json
import subprocess
import sys
import re
import hashlib
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any
import fnmatch
import logging
from urllib.parse import urlparse

import requests
from rich.console import Console
from rich.progress import track

# Configure secure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("audit.log", mode="a")
    ]
)
logger = logging.getLogger(__name__)

console = Console()

# Security Configuration
class AuditConfig:
    """Secure audit configuration with validation."""
    
    def __init__(self):
        self.ollama_url = self._validate_ollama_url()
        self.model = self._validate_model()
        self.reports_dir = self._validate_reports_dir()
        self.max_file_size = self._validate_max_file_size()
        self.request_timeout = 120
        self.max_files_per_batch = 100
        self.auditignore_file = ".auditignore"
        
    def _validate_ollama_url(self) -> str:
        """Validate and sanitize Ollama URL."""
        url = os.getenv("OLLAMA_URL", "http://localhost:11434/api/generate")
        
        # Parse URL to validate format
        try:
            parsed = urlparse(url)
            if parsed.scheme not in ["http", "https"]:
                raise ValueError("Invalid URL scheme")
            if not parsed.netloc:
                raise ValueError("Invalid URL format")
        except Exception as e:
            logger.error(f"Invalid Ollama URL configuration: {e}")
            # Fallback to safe default
            url = "http://localhost:11434/api/generate"
            
        logger.info(f"Using Ollama URL: {url}")
        return url
    
    def _validate_model(self) -> str:
        """Validate model name."""
        model = os.getenv("AUDIT_MODEL", "llama3:8b")
        
        # Sanitize model name to prevent injection
        if not re.match(r'^[a-zA-Z0-9:._-]+$', model):
            logger.warning("Invalid model name format, using default")
            model = "llama3:8b"
            
        return model
    
    def _validate_reports_dir(self) -> str:
        """Validate and create reports directory."""
        reports_dir = os.getenv("AUDIT_REPORTS_DIR", "reports")
        
        # Sanitize directory name
        if not re.match(r'^[a-zA-Z0-9._-]+$', reports_dir):
            logger.warning("Invalid reports directory name, using default")
            reports_dir = "reports"
        
        # Create directory with secure permissions
        try:
            os.makedirs(reports_dir, mode=0o750, exist_ok=True)
        except OSError as e:
            logger.error(f"Failed to create reports directory: {e}")
            raise
            
        return reports_dir
    
    def _validate_max_file_size(self) -> int:
        """Validate maximum file size limit."""
        try:
            max_size = int(os.getenv("AUDIT_MAX_FILE_SIZE", "20480"))  # 20KB default
            if max_size <= 0 or max_size > 1048576:  # Max 1MB
                raise ValueError("File size out of acceptable range")
            return max_size
        except ValueError:
            logger.warning("Invalid max file size, using default 20KB")
            return 20 * 1024

# Initialize secure configuration
config = AuditConfig()

# Load audit ignore patterns
EXCLUDE_PATTERNS = set()

# Security patterns that should never be analyzed
SECURITY_EXCLUDE_PATTERNS = {
    "*.key", "*.pem", "*.crt", "*.p12", "*.pfx",  # Certificates/keys
    "*.env", ".env.*",  # Environment files
    "*.secret", "*.secrets",  # Secret files
    "id_rsa*", "id_dsa*", "id_ecdsa*",  # SSH keys
    "*.password", "*.passwd",  # Password files
}

def load_audit_ignore():
    """
    Load patterns from .auditignore file with security validation.
    
    Raises:
        ValueError: If ignore patterns contain security risks
    """
    global EXCLUDE_PATTERNS
    
    try:
        if os.path.exists(config.auditignore_file):
            with open(config.auditignore_file, "r", encoding="utf-8") as f:
                patterns_loaded = 0
                
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    
                    # Skip empty lines and comments
                    if not line or line.startswith("#"):
                        continue
                    
                    # Validate pattern for security
                    if not _validate_ignore_pattern(line, line_num):
                        continue
                        
                    # Normalize patterns
                    pattern = line.rstrip("/")
                    EXCLUDE_PATTERNS.add(pattern)
                    
                    # Also add with trailing slash for directory matching
                    if not line.endswith("/"):
                        EXCLUDE_PATTERNS.add(pattern + "/")
                    
                    patterns_loaded += 1
                    
                    # Prevent excessive patterns (DoS protection)
                    if patterns_loaded > 1000:
                        logger.warning("Too many ignore patterns, truncating")
                        break
                        
            logger.info(f"Loaded {len(EXCLUDE_PATTERNS)} ignore patterns from {config.auditignore_file}")
        else:
            # Default exclusions if no .auditignore file
            EXCLUDE_PATTERNS = {
                "venv", "__pycache__", ".git", "node_modules", "reports", 
                ".audit_cache", "audit_reports", ".pytest_cache", ".mypy_cache",
                ".ruff_cache", "htmlcov", "dist", "build", ".eggs", "*.egg-info"
            }
            logger.info("No .auditignore found, using default exclusions")
            
        # Always add security patterns
        EXCLUDE_PATTERNS.update(SECURITY_EXCLUDE_PATTERNS)
        
    except Exception as e:
        logger.error(f"Error loading audit ignore patterns: {e}")
        # Use secure defaults
        EXCLUDE_PATTERNS = SECURITY_EXCLUDE_PATTERNS.copy()


def _validate_ignore_pattern(pattern: str, line_num: int) -> bool:
    """
    Validate ignore pattern for security issues.
    
    Args:
        pattern: Pattern to validate
        line_num: Line number for error reporting
        
    Returns:
        bool: True if pattern is safe
    """
    # Check for dangerous patterns
    dangerous_patterns = [
        "..", "/", "\\", "~", "$", "`", ";", "|", "&", "(", ")", "<", ">",
        "rm -", "del ", "format ", "exec", "eval"
    ]
    
    for dangerous in dangerous_patterns:
        if dangerous in pattern:
            logger.warning(f"Suspicious pattern on line {line_num}: {pattern}")
            return False
    
    # Check pattern length
    if len(pattern) > 200:
        logger.warning(f"Pattern too long on line {line_num}")
        return False
    
    # Validate as regex to prevent ReDoS
    try:
        re.compile(pattern)
    except re.error:
        logger.warning(f"Invalid regex pattern on line {line_num}: {pattern}")
        return False
    
    return True

def should_exclude_path(path_str):
    """Check if a path should be excluded based on ignore patterns."""
    path_obj = Path(path_str)
    
    # Check each part of the path
    for part in path_obj.parts:
        for pattern in EXCLUDE_PATTERNS:
            if fnmatch.fnmatch(part, pattern.rstrip("/")):
                return True
    
    # Check full relative path
    for pattern in EXCLUDE_PATTERNS:
        if fnmatch.fnmatch(path_str, pattern):
            return True
    
    return False

def is_safe_to_analyze(file_path: str) -> Tuple[bool, Optional[str]]:
    """
    Check if file is safe to analyze with comprehensive security checks.
    
    Args:
        file_path: Path to file
        
    Returns:
        Tuple[bool, Optional[str]]: (is_safe, error_reason)
    """
    try:
        # Security: Validate file path
        if not _validate_file_path(file_path):
            return False, "Invalid or suspicious file path"
        
        # Check file size
        file_size = os.path.getsize(file_path)
        if file_size > config.max_file_size:
            return False, f"File too large (>{config.max_file_size/1024:.1f}KB)"
        
        # Check if file contains binary data
        if _is_binary_file(file_path):
            return False, "Binary file detected"
        
        # Try to read file to check encoding and content safety
        with open(file_path, "r", encoding="utf-8") as f:
            # Read small sample to test encoding and check for suspicious content
            sample = f.read(2048)
            
            # Basic content validation
            if not _validate_file_content(sample):
                return False, "Suspicious file content detected"
        
        return True, None
        
    except UnicodeDecodeError:
        return False, "Non-UTF-8 encoding detected"
    except PermissionError:
        return False, "Permission denied"
    except FileNotFoundError:
        return False, "File not found"
    except Exception as e:
        logger.warning(f"Error checking file safety: {e}")
        return False, f"File access error: {str(e)}"


def _validate_file_path(file_path: str) -> bool:
    """
    Validate file path for security issues.
    
    Args:
        file_path: File path to validate
        
    Returns:
        bool: True if path is safe
    """
    # Check for path traversal attempts
    if ".." in file_path or file_path.startswith("/"):
        return False
    
    # Check for dangerous characters
    dangerous_chars = ["|", ";", "&", "`", "$", "(", ")", "<", ">"]
    if any(char in file_path for char in dangerous_chars):
        return False
    
    # Check path length
    if len(file_path) > 500:
        return False
    
    return True


def _is_binary_file(file_path: str) -> bool:
    """
    Check if file is binary by reading first chunk.
    
    Args:
        file_path: File path to check
        
    Returns:
        bool: True if file appears to be binary
    """
    try:
        with open(file_path, "rb") as f:
            chunk = f.read(1024)
            # Check for null bytes (common in binary files)
            return b'\x00' in chunk
    except Exception:
        return True  # Assume binary if we can't read it


def _validate_file_content(content: str) -> bool:
    """
    Validate file content for suspicious patterns.
    
    Args:
        content: File content sample
        
    Returns:
        bool: True if content appears safe
    """
    # Check for obvious credential patterns
    credential_patterns = [
        r'password\s*=\s*["\'][^"\']+["\']',
        r'api_key\s*=\s*["\'][^"\']+["\']',
        r'secret\s*=\s*["\'][^"\']+["\']',
        r'token\s*=\s*["\'][^"\']+["\']',
    ]
    
    for pattern in credential_patterns:
        if re.search(pattern, content, re.IGNORECASE):
            logger.warning("Potential credential detected in file content")
            return False
    
    return True


# --- Secure Helper Functions -----------------------------------------------------

def run_command_secure(cmd: List[str], cwd: Optional[str] = None, timeout: int = 300) -> str:
    """
    Run a command securely without shell injection vulnerabilities.
    
    Args:
        cmd: Command as list of arguments
        cwd: Working directory
        timeout: Command timeout in seconds
        
    Returns:
        str: Command output
        
    Raises:
        subprocess.TimeoutExpired: If command times out
        subprocess.CalledProcessError: If command fails
    """
    try:
        # Validate command arguments
        if not cmd or not isinstance(cmd, list):
            raise ValueError("Command must be a non-empty list")
        
        # Sanitize command arguments
        sanitized_cmd = []
        for arg in cmd:
            if not isinstance(arg, str):
                raise ValueError("All command arguments must be strings")
            # Basic validation - no shell metacharacters
            if any(char in arg for char in [';', '|', '&', '$', '`', '(', ')']):
                logger.warning(f"Potentially dangerous command argument: {arg}")
                continue
            sanitized_cmd.append(arg)
        
        if not sanitized_cmd:
            raise ValueError("No valid command arguments after sanitization")
        
        logger.debug(f"Executing command: {' '.join(sanitized_cmd)}")
        
        result = subprocess.run(
            sanitized_cmd,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,  # Don't raise on non-zero exit
        )
        
        # Log command execution results
        if result.returncode != 0:
            logger.warning(f"Command exited with code {result.returncode}: {' '.join(sanitized_cmd)}")
            if result.stderr:
                logger.debug(f"Command stderr: {result.stderr[:500]}")
        
        return result.stdout.strip()
        
    except subprocess.TimeoutExpired:
        logger.error(f"Command timed out after {timeout}s: {' '.join(cmd)}")
        return f"Command timed out after {timeout} seconds"
    except Exception as e:
        logger.error(f"Command execution failed: {e}")
        return f"Command execution error: {str(e)}"


def run_ruff() -> str:
    """Run Ruff linter with secure command execution."""
    logger.info("Running Ruff (lint + style)...")
    return run_command_secure(["ruff", "check", ".", "--output-format", "json"])


def run_bandit() -> str:
    """Run Bandit security scanner with secure command execution."""
    logger.info("Running Bandit (security scan)...")
    return run_command_secure(["bandit", "-r", ".", "-f", "json"])


def run_mypy() -> str:
    """Run MyPy type checker with secure command execution."""
    logger.info("Running MyPy (type check)...")
    return run_command_secure(["mypy", "--show-error-codes", "--pretty", "."])


def analyze_with_llm(file_path: str) -> str:
    """
    Send code to Ollama for intelligent analysis with comprehensive safety checks.
    
    Args:
        file_path: Path to file to analyze
        
    Returns:
        str: Analysis result or skip reason
    """
    # First check if file should be excluded
    if should_exclude_path(file_path):
        logger.debug(f"Skipping excluded file: {file_path}")
        return f"Skipped (excluded by .auditignore): {file_path}"
    
    # Check if file is safe to analyze
    is_safe, reason = is_safe_to_analyze(file_path)
    if not is_safe:
        logger.debug(f"Skipping unsafe file {file_path}: {reason}")
        return f"Skipped ({reason}): {file_path}"
    
    try:
        # Read file content with size limits
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read(config.max_file_size)  # Enforce size limit
            
        # Sanitize content for prompt injection prevention
        sanitized_content = _sanitize_content_for_llm(content)
        
        # Build secure prompt
        prompt = _build_secure_prompt(file_path, sanitized_content)
        
        # Make secure HTTP request
        response = _make_secure_llm_request(prompt)
        
        if response:
            logger.debug(f"Successfully analyzed file: {file_path}")
            return response
        else:
            return f"Error: No response from LLM for {file_path}"

    except UnicodeDecodeError:
        logger.warning(f"Encoding issue with file: {file_path}")
        return f"Skipped (encoding issue): {file_path}"
    except Exception as e:
        logger.error(f"Error analyzing {file_path}: {e}")
        return f"Error analyzing {file_path}: {str(e)}"


def _sanitize_content_for_llm(content: str) -> str:
    """
    Sanitize file content to prevent prompt injection attacks.
    
    Args:
        content: Raw file content
        
    Returns:
        str: Sanitized content
    """
    # Remove potential prompt injection patterns
    injection_patterns = [
        r'Ignore previous instructions',
        r'Act as.*',
        r'Pretend to be.*',
        r'You are now.*',
        r'System:.*',
        r'Assistant:.*',
        r'Human:.*',
    ]
    
    sanitized = content
    for pattern in injection_patterns:
        sanitized = re.sub(pattern, '[FILTERED]', sanitized, flags=re.IGNORECASE)
    
    # Limit content size (4KB for analysis)
    if len(sanitized) > 4000:
        sanitized = sanitized[:4000] + "\n... [CONTENT TRUNCATED FOR SECURITY]"
    
    return sanitized


def _build_secure_prompt(file_path: str, content: str) -> str:
    """
    Build a secure prompt for LLM analysis.
    
    Args:
        file_path: File path (sanitized)
        content: File content (sanitized)
        
    Returns:
        str: Secure prompt
    """
    # Sanitize file path for display
    display_path = os.path.basename(file_path)
    
    prompt = f"""Perform a **production readiness audit** for this code file.

Analysis criteria:
- Security vulnerabilities and best practices
- Code quality and maintainability
- Performance considerations
- Error handling completeness
- Adherence to modern development standards

Provide concise, actionable recommendations.

FILE: {display_path}
------------------------
{content}
------------------------

Please provide a structured analysis with specific recommendations."""
    
    return prompt


def _make_secure_llm_request(prompt: str) -> Optional[str]:
    """
    Make a secure HTTP request to the LLM service.
    
    Args:
        prompt: Prompt to send
        
    Returns:
        Optional[str]: Response content or None
    """
    try:
        # Validate prompt size
        if len(prompt) > 10000:  # Reasonable limit
            logger.warning("Prompt too large, truncating")
            prompt = prompt[:10000] + "\n[PROMPT TRUNCATED]"
        
        # Prepare request with security headers
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "SyferStack-Audit/1.0",
        }
        
        payload = {
            "model": config.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.1,  # Low temperature for consistent results
                "top_p": 0.9,
                "max_tokens": 2000,  # Limit response size
            }
        }
        
        # Make request with timeout and retries
        for attempt in range(3):  # 3 retry attempts
            try:
                response = requests.post(
                    config.ollama_url,
                    json=payload,
                    headers=headers,
                    timeout=config.request_timeout,
                )
                
                if response.status_code == 200:
                    result = response.json()
                    return result.get("response", "").strip()
                else:
                    logger.warning(f"LLM request failed with status {response.status_code}")
                    
            except requests.exceptions.Timeout:
                logger.warning(f"LLM request timeout on attempt {attempt + 1}")
                time.sleep(2 ** attempt)  # Exponential backoff
            except requests.exceptions.RequestException as e:
                logger.error(f"LLM request error on attempt {attempt + 1}: {e}")
                time.sleep(2 ** attempt)
        
        return None
        
    except Exception as e:
        logger.error(f"Unexpected error in LLM request: {e}")
        return None


# --- Main Audit -----------------------------------------------------------

def run_full_audit():
    console.rule("[bold green]🧩 SyferStackV2 Production Audit Starting")
    
    # Load ignore patterns first
    load_audit_ignore()

    bandit_output = run_bandit()
    try:
        bandit_data = json.loads(bandit_output)
    except json.JSONDecodeError:
        bandit_data = {"results": [], "error": "Invalid Bandit output", "raw": bandit_output}

    results = {
        "timestamp": datetime.now().isoformat(),
        "ruff": json.loads(run_ruff() or "{}"),
        "bandit": bandit_data,
        "mypy": run_mypy(),
        "files": [],
        "audit_stats": {
            "files_scanned": 0,
            "files_analyzed": 0,
            "files_skipped": 0,
            "skip_reasons": {}
        }
    }

    # Collect files with smart filtering
    files_to_analyze = []
    
    for root, dirs, files in os.walk("."):
        # Filter directories in-place to avoid traversing excluded paths
        dirs[:] = [d for d in dirs if not should_exclude_path(os.path.join(root, d))]
        
        for file in files:
            if file.endswith((".py", ".js", ".ts", ".tsx")):
                path = os.path.join(root, file)
                
                # Skip if path should be excluded
                if should_exclude_path(path):
                    results["audit_stats"]["files_skipped"] += 1
                    reason = "excluded_by_auditignore"
                    results["audit_stats"]["skip_reasons"][reason] = results["audit_stats"]["skip_reasons"].get(reason, 0) + 1
                    continue
                
                # Check if file is safe to analyze
                is_safe, reason = is_safe_to_analyze(path)
                if not is_safe:
                    results["audit_stats"]["files_skipped"] += 1
                    safe_reason = reason.split("(")[0].strip().replace(" ", "_").lower()
                    results["audit_stats"]["skip_reasons"][safe_reason] = results["audit_stats"]["skip_reasons"].get(safe_reason, 0) + 1
                    continue
                
                files_to_analyze.append(path)
    
    results["audit_stats"]["files_scanned"] = len(files_to_analyze) + results["audit_stats"]["files_skipped"]
    
    console.log(f"[cyan]Found {len(files_to_analyze)} files to analyze")
    console.log(f"[yellow]Skipped {results['audit_stats']['files_skipped']} files")
    
    # Analyze collected files
    for path in track(files_to_analyze, description="Analyzing code with LLM..."):
        llm_analysis = analyze_with_llm(path)
        
        # Track if analysis was successful
        if llm_analysis.startswith("Skipped"):
            results["audit_stats"]["files_skipped"] += 1
        else:
            results["audit_stats"]["files_analyzed"] += 1
            
        results["files"].append({
            "path": path,
            "llm_analysis": llm_analysis
        })

    out_json = os.path.join(config.reports_dir, "production_audit.json")
    with open(out_json, "w") as f:
        json.dump(results, f, indent=2)

    console.print(f"[bold yellow]✅ JSON Report saved to {out_json}")
    console.print("[cyan]Generating Markdown summary...")
    generate_markdown_summary(results)


# --- Markdown Summary -----------------------------------------------------

def generate_markdown_summary(data):
    """Generate a clean human-readable summary.md report."""
    summary_file = os.path.join(config.reports_dir, "summary.md")

    def grade_risk(bandit_count, ruff_count):
        """Simple weighted scoring system."""
        score = max(0, 100 - (bandit_count * 4 + ruff_count * 2))
        if score >= 90: return "A"
        if score >= 80: return "B"
        if score >= 70: return "C"
        if score >= 60: return "D"
        return "F"

    bandit_issues = len(data.get("bandit", {}).get("results", []))
    ruff_issues = len(data.get("ruff", []))
    grade = grade_risk(bandit_issues, ruff_issues)

    with open(summary_file, "w") as md:
        md.write(f"# 🧩 SyferStackV2 Production Audit Summary\n")
        md.write(f"**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        md.write(f"**Overall Grade:** `{grade}`\n\n")
        md.write(f"### Static Analysis\n")
        md.write(f"- **Ruff Findings:** {ruff_issues}\n")
        md.write(f"- **Bandit Findings:** {bandit_issues}\n\n")
        
        # Add audit statistics
        stats = data.get('audit_stats', {})
        md.write(f"### Audit Statistics\n")
        md.write(f"- **Files Scanned:** {stats.get('files_scanned', 0)}\n")
        md.write(f"- **Files Analyzed:** {stats.get('files_analyzed', 0)}\n")
        md.write(f"- **Files Skipped:** {stats.get('files_skipped', 0)}\n")
        
        skip_reasons = stats.get('skip_reasons', {})
        if skip_reasons:
            md.write(f"- **Skip Reasons:**\n")
            for reason, count in skip_reasons.items():
                md.write(f"  - {reason.replace('_', ' ').title()}: {count}\n")
        md.write(f"\n")
        
        md.write(f"### Type Check (MyPy)\n```\n{data.get('mypy', '')[:1000]}\n```\n")
        md.write(f"### LLM Insights\n")

        for file_entry in data["files"]:
            md.write(f"\n#### {file_entry['path']}\n")
            md.write(f"{file_entry['llm_analysis']}\n\n")

        md.write("\n---\n")
        md.write("### 📋 Recommendations\n")
        md.write("- Fix critical Bandit security issues before deployment.\n")
        md.write("- Resolve Ruff warnings for cleaner CI/CD pipelines.\n")
        md.write("- Use strict MyPy typing for large-scale reliability.\n")
        md.write("- Review LLM notes for deeper refactoring guidance.\n")
        md.write(f"\n✅ Report automatically generated by SyferStackV2 Local Audit\n")

    console.print(f"[bold green]📄 Markdown summary generated → {summary_file}")


# --- Entry ---------------------------------------------------------------

if __name__ == "__main__":
    run_full_audit()

