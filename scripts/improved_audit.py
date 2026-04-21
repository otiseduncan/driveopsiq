#!/usr/bin/env python3
"""
SyferStackV2 – Production Grade Audit System (Improved)
Performs static, security, and LLM-based audits using Ollama.
Generates both JSON and Markdown summaries.
"""

import asyncio
import json
import logging
import os
import shlex
import subprocess
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
import aiohttp
import aiofiles
from rich.console import Console
from rich.progress import Progress, TaskID

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class AuditConfig:
    """Configuration for audit system."""
    ollama_url: str = "http://localhost:11434/api/generate"
    model: str = "llama3:8b"
    max_file_size: int = 1024 * 1024  # 1MB
    max_content_chars: int = 4000
    timeout: int = 120
    reports_dir: Path = Path("reports")
    parallel_llm_requests: int = 5
    supported_extensions: Tuple[str, ...] = (".py", ".js", ".ts", ".tsx")


@dataclass
class FileAnalysis:
    """Result of analyzing a single file."""
    path: str
    llm_analysis: str
    error: Optional[str] = None
    skipped: bool = False
    size_bytes: int = 0


@dataclass
class AuditResults:
    """Complete audit results."""
    timestamp: str
    ruff: Dict[str, Any]
    bandit: Dict[str, Any]
    mypy: str
    files: List[FileAnalysis]
    config: AuditConfig
    errors: List[str]


class SecurityError(Exception):
    """Raised when security validation fails."""
    pass


class AuditToolRunner:
    """Handles running external audit tools safely."""
    
    def __init__(self, config: AuditConfig):
        self.config = config
        self.console = Console()
    
    async def run_command_safe(self, cmd: List[str], description: str) -> str:
        """Run command safely without shell injection."""
        try:
            self.console.log(f"[cyan]{description}...")
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()
            
            if process.returncode != 0:
                logger.warning(f"{description} failed with code {process.returncode}: {stderr.decode()}")
            
            return stdout.decode().strip()
        except Exception as e:
            logger.error(f"Failed to run {description}: {e}")
            return f"Error: {e}"
    
    async def run_ruff(self) -> Dict[str, Any]:
        """Run Ruff linter with dependency exclusions."""
        # Exclude common dependency directories
        exclude_dirs = [
            "node_modules", "venv", "env", ".env", "__pycache__", ".git",
            "site-packages", "dist", "build", ".pytest_cache", ".mypy_cache",
            "vendor", "third_party", "external", "libs", "packages",
            "alembic/versions", "migrations", "uploads", "static"
        ]
        exclude_arg = ",".join(exclude_dirs)
        
        output = await self.run_command_safe(
            ["ruff", "check", ".", "--output-format", "json", "--exclude", exclude_arg],
            "Running Ruff (lint + style)"
        )
        try:
            return json.loads(output) if output else {}
        except json.JSONDecodeError:
            return {"error": "Invalid Ruff output", "raw": output}
    
    async def run_bandit(self) -> Dict[str, Any]:
        """Run Bandit security scanner with dependency exclusions."""
        # Skip common dependency and generated directories
        skip_dirs = [
            "node_modules", "venv", "env", ".env", "__pycache__", ".git",
            "site-packages", "dist", "build", ".pytest_cache", ".mypy_cache",
            "vendor", "third_party", "external", "libs", "packages", "wheels",
            "alembic/versions", "migrations", "uploads", "static", "nginx", "redis"
        ]
        skip_args = []
        for skip_dir in skip_dirs:
            skip_args.extend(["-s", skip_dir])
            
        cmd = ["bandit", "-r", ".", "-f", "json"] + skip_args
        output = await self.run_command_safe(cmd, "Running Bandit (security scan)")
        
        try:
            return json.loads(output) if output else {"results": []}
        except json.JSONDecodeError:
            return {"results": [], "error": "Invalid Bandit output", "raw": output}
    
    async def run_mypy(self) -> str:
        """Run MyPy type checker with dependency exclusions."""
        # Exclude dependency directories from type checking
        exclude_patterns = [
            "venv/*", "env/*", "node_modules/*", "site-packages/*", 
            "dist/*", "build/*", "__pycache__/*", "vendor/*", "third_party/*",
            "alembic/versions/*", "migrations/*"
        ]
        
        cmd = ["mypy", "--show-error-codes", "--pretty", "."]
        for pattern in exclude_patterns:
            cmd.extend(["--exclude", pattern])
            
        return await self.run_command_safe(cmd, "Running MyPy (type check)")


class LLMAnalyzer:
    """Handles LLM-based code analysis with proper async handling."""
    
    def __init__(self, config: AuditConfig):
        self.config = config
        self.session: Optional[aiohttp.ClientSession] = None
    
    async def __aenter__(self):
        timeout = aiohttp.ClientTimeout(total=self.config.timeout)
        self.session = aiohttp.ClientSession(timeout=timeout)
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    def _validate_file_path(self, file_path: Path) -> None:
        """Validate file path for security."""
        if not file_path.exists():
            raise SecurityError(f"File does not exist: {file_path}")
        
        if file_path.stat().st_size > self.config.max_file_size:
            raise SecurityError(f"File too large: {file_path}")
        
        # Prevent directory traversal
        try:
            file_path.resolve().relative_to(Path.cwd().resolve())
        except ValueError:
            raise SecurityError(f"File outside working directory: {file_path}")
    
    async def analyze_file(self, file_path: Path) -> FileAnalysis:
        """Analyze a single file with the LLM."""
        try:
            self._validate_file_path(file_path)
            
            async with aiofiles.open(file_path, "r", encoding="utf-8") as f:
                content = await f.read()
            
            # Truncate content to prevent token limit issues
            if len(content) > self.config.max_content_chars:
                content = content[:self.config.max_content_chars] + "\n... [truncated]"
            
            prompt = self._build_analysis_prompt(str(file_path), content)
            
            if not self.session:
                raise RuntimeError("LLM session not initialized")
            
            async with self.session.post(
                self.config.ollama_url,
                json={"model": self.config.model, "prompt": prompt, "stream": False}
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise Exception(f"LLM API error {response.status}: {error_text}")
                
                result = await response.json()
                analysis = result.get("response", "").strip()
                
                return FileAnalysis(
                    path=str(file_path),
                    llm_analysis=analysis,
                    size_bytes=file_path.stat().st_size
                )
        
        except SecurityError as e:
            return FileAnalysis(
                path=str(file_path),
                llm_analysis="",
                error=str(e),
                skipped=True
            )
        except Exception as e:
            logger.error(f"Error analyzing {file_path}: {e}")
            return FileAnalysis(
                path=str(file_path),
                llm_analysis="",
                error=str(e)
            )
    
    def _build_analysis_prompt(self, file_path: str, content: str) -> str:
        """Build the analysis prompt for the LLM."""
        return f"""
You are a senior software engineer performing a **production readiness code audit**.

Analyze this file for:
🔒 **Security Issues** (OWASP Top 10, injection flaws, authentication issues)
⚡ **Performance Issues** (bottlenecks, inefficient algorithms, resource leaks)
🧩 **Code Quality** (smells, anti-patterns, complexity, maintainability)
📈 **Scalability Concerns** (concurrency issues, database queries, caching)
✅ **Best Practices** (naming conventions, error handling, documentation)

**IMPORTANT**: Format your response as structured markdown with clear sections:

## 🔍 Analysis Summary
Brief overview of file quality and main concerns.

## 🚨 Critical Issues (HIGH Priority)
List any high-severity issues that need immediate attention.

## ⚠️ Important Issues (MEDIUM Priority)  
List medium-priority issues that should be addressed soon.

## 💡 Suggestions (LOW Priority)
List minor improvements and best practice recommendations.

## 🎯 Recommended Actions
Prioritized list of specific actions to take:
1. [Action with estimated effort: 15 mins / 1 hour / 1 day]
2. [Next action...]

## ✨ Positive Aspects
What this code does well (if any).

---
**File**: `{file_path}`
**Analysis Date**: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

---
**CODE TO ANALYZE:**
```
{content}
```
"""


class AuditReporter:
    """Generates various report formats."""
    
    def __init__(self, config: AuditConfig):
        self.config = config
        self.console = Console()
    
    async def save_json_report(self, results: AuditResults) -> Path:
        """Save audit results as JSON."""
        self.config.reports_dir.mkdir(exist_ok=True)
        report_path = self.config.reports_dir / "production_audit.json"
        
        # Convert dataclasses to dict for JSON serialization
        results_dict = asdict(results)
        
        async with aiofiles.open(report_path, "w") as f:
            await f.write(json.dumps(results_dict, indent=2, default=str))
        
        return report_path
    
    def _calculate_grade(self, bandit_count: int, ruff_count: int) -> str:
        """Calculate overall grade based on findings."""
        # More sophisticated scoring
        critical_weight = 10
        medium_weight = 3
        low_weight = 1
        
        score = max(0, 100 - (bandit_count * critical_weight + ruff_count * medium_weight))
        
        if score >= 95: return "A+"
        if score >= 90: return "A"
        if score >= 85: return "B+"
        if score >= 80: return "B"
        if score >= 75: return "C+"
        if score >= 70: return "C"
        if score >= 60: return "D"
        return "F"
    
    async def generate_markdown_summary(self, results: AuditResults) -> Path:
        """Generate comprehensive Markdown report."""
        summary_path = self.config.reports_dir / "summary.md"
        
        bandit_issues = len(results.bandit.get("results", []))
        ruff_issues = len(results.ruff) if isinstance(results.ruff, list) else 0
        grade = self._calculate_grade(bandit_issues, ruff_issues)
        
        # Calculate statistics
        total_files = len(results.files)
        analyzed_files = len([f for f in results.files if not f.skipped])
        error_count = len([f for f in results.files if f.error])
        
        report_content = f"""# 🛡️ SyferStackV2 Production Audit Report

**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}  
**Overall Grade:** `{grade}`  
**Repository:** SyferStackV2  
**Branch:** staging  

## 📊 Executive Summary

| Metric | Value |
|--------|--------|
| Files Scanned | {total_files} |
| Files Analyzed | {analyzed_files} |
| Analysis Errors | {error_count} |
| Ruff Issues | {ruff_issues} |
| Bandit Issues | {bandit_issues} |

## 🔍 Static Analysis Results

### Security Issues (Bandit)
- **Total Findings:** {bandit_issues}
- **Status:** {"✅ Clean" if bandit_issues == 0 else "⚠️ Requires Attention"}

### Code Quality (Ruff)
- **Total Findings:** {ruff_issues}
- **Status:** {"✅ Clean" if ruff_issues == 0 else "⚠️ Requires Attention"}

### Type Safety (MyPy)
```
{results.mypy[:1500] if results.mypy else "No MyPy output available"}
```

## 🤖 LLM Analysis Results

"""
        
        for file_analysis in results.files:
            if file_analysis.skipped:
                continue
                
            status = "✅" if not file_analysis.error else "❌"
            report_content += f"\n### {status} `{file_analysis.path}`\n"
            
            if file_analysis.error:
                report_content += f"**Error:** {file_analysis.error}\n\n"
            else:
                report_content += f"{file_analysis.llm_analysis}\n\n"
        
        # Add consolidated recommendations section
        critical_issues, important_issues, suggestions = self._extract_recommendations(results.files)
        
        report_content += f"""
## 📋 Consolidated Recommendations

### 🚨 Critical Issues ({len(critical_issues)})
"""
        for issue in critical_issues:
            report_content += f"- {issue}\n"
            
        report_content += f"""
### ⚠️ Important Issues ({len(important_issues)})
"""
        for issue in important_issues:
            report_content += f"- {issue}\n"
            
        report_content += f"""
### 💡 Suggestions ({len(suggestions)})
"""
        for suggestion in suggestions:
            report_content += f"- {suggestion}\n"
        
        report_content += """
## 🎯 Action Plan

### Phase 1: Security & Critical Issues
1. **Security First:** Address all Bandit security findings immediately
2. **Type Safety:** Resolve MyPy type errors that could cause runtime failures
3. **Critical Fixes:** Implement high-priority recommendations from LLM analysis

### Phase 2: Code Quality & Maintainability  
1. **Code Quality:** Clean up Ruff linting issues
2. **Best Practices:** Implement medium-priority LLM recommendations
3. **Error Handling:** Add robust error handling where identified

### Phase 3: Optimization & Enhancement
1. **Performance:** Review and implement performance improvements
2. **Architecture:** Consider structural recommendations
3. **Documentation:** Update code documentation based on findings

## 🔄 Implementation Guidelines

- **Estimated Total Effort:** Review individual file analyses for time estimates
- **Priority Order:** Critical → Important → Suggestions
- **Testing:** Validate each fix with appropriate tests
- **Monitoring:** Set up automated checks to prevent regression

---
*Report generated by SyferStackV2 Production Audit System v2.0*  
*Analysis powered by {results.config.model} via Ollama*
"""
        
        async with aiofiles.open(summary_path, "w") as f:
            await f.write(report_content)
        
        return summary_path
    
    def _extract_recommendations(self, files: List[FileAnalysis]) -> Tuple[List[str], List[str], List[str]]:
        """Extract and categorize recommendations from LLM analyses."""
        critical_issues = []
        important_issues = []
        suggestions = []
        
        for file_analysis in files:
            if file_analysis.skipped or file_analysis.error:
                continue
                
            analysis = file_analysis.llm_analysis.lower()
            
            # Extract critical issues (HIGH priority)
            if "critical" in analysis or "high priority" in analysis or "🚨" in analysis:
                lines = file_analysis.llm_analysis.split('\n')
                for line in lines:
                    if any(keyword in line.lower() for keyword in ['critical', 'high priority', 'security', 'vulnerability']):
                        if line.strip() and not line.strip().startswith('#'):
                            clean_line = line.strip('- ').strip()
                            if clean_line and len(clean_line) > 10:
                                critical_issues.append(f"**{file_analysis.path}**: {clean_line}")
            
            # Extract important issues (MEDIUM priority)
            if "important" in analysis or "medium priority" in analysis or "⚠️" in analysis:
                lines = file_analysis.llm_analysis.split('\n')
                for line in lines:
                    if any(keyword in line.lower() for keyword in ['important', 'medium priority', 'should', 'consider']):
                        if line.strip() and not line.strip().startswith('#'):
                            clean_line = line.strip('- ').strip()
                            if clean_line and len(clean_line) > 10 and clean_line not in [item.split(': ', 1)[-1] for item in critical_issues]:
                                important_issues.append(f"**{file_analysis.path}**: {clean_line}")
            
            # Extract suggestions (LOW priority)  
            if "suggestion" in analysis or "low priority" in analysis or "💡" in analysis:
                lines = file_analysis.llm_analysis.split('\n')
                for line in lines:
                    if any(keyword in line.lower() for keyword in ['suggestion', 'low priority', 'could', 'might', 'optional']):
                        if line.strip() and not line.strip().startswith('#'):
                            clean_line = line.strip('- ').strip()
                            if clean_line and len(clean_line) > 10:
                                already_listed = any(clean_line in item for item in critical_issues + important_issues)
                                if not already_listed:
                                    suggestions.append(f"**{file_analysis.path}**: {clean_line}")
        
        # Limit to prevent overwhelming reports
        return critical_issues[:10], important_issues[:15], suggestions[:20]


class ProductionAuditor:
    """Main audit orchestrator with improved architecture."""
    
    def __init__(self, config: AuditConfig = None):
        self.config = config or AuditConfig()
        self.console = Console()
        self.custom_ignore_patterns = self._load_ignore_patterns()
        
    async def run_audit(self) -> AuditResults:
        """Run complete production audit."""
        self.console.rule("[bold green]🛡️ SyferStackV2 Production Audit Starting")
        
        # Initialize components
        tool_runner = AuditToolRunner(self.config)
        reporter = AuditReporter(self.config)
        
        # Run static analysis tools concurrently
        ruff_task = asyncio.create_task(tool_runner.run_ruff())
        bandit_task = asyncio.create_task(tool_runner.run_bandit())
        mypy_task = asyncio.create_task(tool_runner.run_mypy())
        
        # Collect files for LLM analysis
        files_to_analyze = self._collect_files()
        
        # Run LLM analysis with concurrency control
        file_analyses = await self._analyze_files_concurrently(files_to_analyze)
        
        # Wait for static analysis to complete
        ruff_results = await ruff_task
        bandit_results = await bandit_task
        mypy_results = await mypy_task
        
        # Compile results
        results = AuditResults(
            timestamp=datetime.now().isoformat(),
            ruff=ruff_results,
            bandit=bandit_results,
            mypy=mypy_results,
            files=file_analyses,
            config=self.config,
            errors=[]
        )
        
        # Generate reports
        json_path = await reporter.save_json_report(results)
        markdown_path = await reporter.generate_markdown_summary(results)
        
        self.console.print(f"[bold yellow]✅ JSON Report: {json_path}")
        self.console.print(f"[bold green]📄 Markdown Report: {markdown_path}")
        
        return results
    
    def _collect_files(self) -> List[Path]:
        """Collect all files for analysis, excluding dependencies and third-party code."""
        files = []
        
        # Directories to ignore (dependencies and third-party)
        ignore_dirs = {
            'node_modules', 'venv', 'env', '.env', '__pycache__', '.git',
            'site-packages', 'dist', 'build', '.pytest_cache', '.mypy_cache',
            'vendor', 'third_party', 'external', 'libs', 'lib64', 'packages',
            '.vscode', '.idea', 'coverage', '.coverage', '.tox', '.nox',
            'wheels', 'eggs', '*.egg-info', 'migrations', 'alembic/versions',
            '.docker', 'docker', 'nginx', 'redis', 'db', 'uploads', 'static',
            '.next', '.nuxt', '.cache', 'tmp', 'temp', 'logs', 'log'
        }
        
        # Files to ignore (generated, config, dependencies)
        ignore_files = {
            'package-lock.json', 'yarn.lock', 'poetry.lock', 'Pipfile.lock',
            'requirements.txt', 'pyproject.toml', 'setup.py', 'setup.cfg',
            'webpack.config.js', 'vite.config.ts', 'tsconfig.json', 'jsconfig.json',
            'babel.config.js', '.eslintrc.js', '.prettierrc', 'tailwind.config.js',
            'docker-compose.yml', 'docker-compose.prod.yml', 'Dockerfile',
            'alembic.ini', 'pytest.ini', 'tox.ini', '.coveragerc',
            'manifest.json', 'service-worker.js', 'sw.js'
        }
        
        # File patterns to ignore (minified, generated, test fixtures)
        ignore_patterns = {
            '*.min.js', '*.min.css', '*.bundle.js', '*.chunk.js',
            '*.d.ts', '*.map', '*.lock', '*.log', '*.tmp',
            '*test*', '*spec*', '*fixture*', '*mock*',
            '*.generated.*', '*.auto.*', '__init__.py'
        }
        
        for root, dirs, filenames in os.walk("."):
            root_path = Path(root)
            
            # Skip ignored directories
            dirs[:] = [d for d in dirs if not self._should_ignore_dir(d, ignore_dirs)]
            
            # Skip if current path contains ignored directories
            if any(part.lower() in ignore_dirs for part in root_path.parts):
                continue
                
            for filename in filenames:
                # Check file extension
                if not filename.endswith(self.config.supported_extensions):
                    continue
                    
                # Skip ignored files
                if filename.lower() in ignore_files:
                    continue
                    
                file_path = root_path / filename
                
                # Skip files matching ignore patterns (built-in + custom)
                all_ignore_patterns = ignore_patterns | self.custom_ignore_patterns
                if self._matches_ignore_pattern(filename, all_ignore_patterns):
                    continue
                    
                # Also check full path against custom patterns
                if self._matches_ignore_pattern(str(file_path), self.custom_ignore_patterns):
                    continue
                
                # Additional file-level checks
                if self._is_valid_source_file(file_path):
                    files.append(file_path)
                    
        return files
    
    def _load_ignore_patterns(self) -> set:
        """Load custom ignore patterns from .auditignore file."""
        ignore_patterns = set()
        auditignore_path = Path(".auditignore")
        
        if auditignore_path.exists():
            try:
                with open(auditignore_path, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        # Skip empty lines and comments
                        if line and not line.startswith('#'):
                            ignore_patterns.add(line.lower())
                            
                logger.info(f"Loaded {len(ignore_patterns)} custom ignore patterns from .auditignore")
            except Exception as e:
                logger.warning(f"Could not read .auditignore file: {e}")
                
        return ignore_patterns
    
    def _should_ignore_dir(self, dirname: str, ignore_dirs: set) -> bool:
        """Check if directory should be ignored."""
        dirname_lower = dirname.lower()
        return (dirname_lower in ignore_dirs or 
                dirname.startswith('.') or
                dirname.endswith('_cache') or
                dirname.endswith('.egg-info'))
    
    def _matches_ignore_pattern(self, filename: str, ignore_patterns: set) -> bool:
        """Check if filename matches any ignore pattern."""
        filename_lower = filename.lower()
        for pattern in ignore_patterns:
            if pattern.startswith('*') and pattern.endswith('*'):
                # Contains pattern
                if pattern[1:-1] in filename_lower:
                    return True
            elif pattern.startswith('*'):
                # Ends with pattern
                if filename_lower.endswith(pattern[1:]):
                    return True
            elif pattern.endswith('*'):
                # Starts with pattern
                if filename_lower.startswith(pattern[:-1]):
                    return True
            else:
                # Exact match
                if filename_lower == pattern:
                    return True
        return False
    
    def _is_valid_source_file(self, file_path: Path) -> bool:
        """Additional validation for source files."""
        try:
            # Skip very large files (likely generated)
            if file_path.stat().st_size > self.config.max_file_size * 2:
                return False
                
            # Skip empty files
            if file_path.stat().st_size == 0:
                return False
                
            # Try to read first few lines to check if it's a source file
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                first_lines = [f.readline().strip() for _ in range(3)]
                
            # Skip if it looks like generated/minified code
            first_content = ' '.join(first_lines).lower()
            if any(marker in first_content for marker in [
                'auto-generated', 'do not edit', 'generated by', 'minified',
                'webpack', 'rollup', 'parcel', 'compiled'
            ]):
                return False
                
            return True
            
        except (OSError, UnicodeDecodeError, PermissionError):
            return False
    
    async def _analyze_files_concurrently(self, files: List[Path]) -> List[FileAnalysis]:
        """Analyze files with controlled concurrency."""
        semaphore = asyncio.Semaphore(self.config.parallel_llm_requests)
        
        async def analyze_with_semaphore(file_path: Path, analyzer: LLMAnalyzer) -> FileAnalysis:
            async with semaphore:
                return await analyzer.analyze_file(file_path)
        
        async with LLMAnalyzer(self.config) as analyzer:
            with Progress() as progress:
                task = progress.add_task("Analyzing files with LLM...", total=len(files))
                
                tasks = [analyze_with_semaphore(file_path, analyzer) for file_path in files]
                results = []
                
                for coro in asyncio.as_completed(tasks):
                    result = await coro
                    results.append(result)
                    progress.advance(task)
                
                return results


async def main():
    """Entry point for the audit system."""
    config = AuditConfig()
    auditor = ProductionAuditor(config)
    
    try:
        results = await auditor.run_audit()
        
        # Print summary
        total_issues = len(results.bandit.get("results", [])) + len(results.ruff)
        print(f"\n🎯 Audit Complete! Found {total_issues} total issues.")
        
    except Exception as e:
        logger.error(f"Audit failed: {e}")
        raise


# --- Integrate with Recommendations System ---
from load_recommendations import RecommendationLoader

def merge_recommendations():
    loader = RecommendationLoader()
    recs = loader.load_from_audit_report(Path("reports/production_audit.json"))
    if not recs:
        print("⚠️  No structured recommendations found to merge.")
        return

    summary = loader.get_summary()
    loader.export_to_json(Path("reports/recommendations_merged.json"))

    print("\n📘 Merged Recommendations Summary:")
    print(f"  Total: {summary.total_recommendations}")
    print(f"  Auto-fixable: {summary.auto_fixable_count}")
    print(f"  Estimated total effort: {summary.estimated_total_effort}")
    print("  Most common issues:")
    for issue in summary.most_common_issues:
        print(f"   • {issue}")

if __name__ == "__main__":
    asyncio.run(main())
    # Also run recommendations merge after main audit
    merge_recommendations()