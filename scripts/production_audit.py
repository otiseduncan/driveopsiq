#!/usr/bin/env python3
"""
SyferStackV2 - Production-Grade Audit System (Final Version)
Complete integration of all enterprise features:
- Configuration management
- Caching system  
- Metrics & monitoring
- Retry logic
- Plugin architecture
- Docker support
- CI/CD integration
"""

import asyncio
import logging
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List
import uuid

# Add all our modules to the path
sys.path.append(str(Path(__file__).parent))

from config_manager import ConfigManager, AuditConfig
from cache_system import AnalysisCache, CachedLLMAnalyzer
from metrics_system import MetricsCollector, AuditMetricsTracker
from retry_system import ReliableLLMAnalyzer, RetryConfig
from plugin_system import PluginManager, AnalysisResult
from improved_audit import (
    AuditToolRunner, LLMAnalyzer, AuditReporter, 
    FileAnalysis, AuditResults
)

logger = logging.getLogger(__name__)


class EnterpriseAuditSystem:
    """
    Enterprise-grade audit system with all advanced features integrated.
    """
    
    def __init__(self, config_path: Path = None):
        """Initialize the enterprise audit system."""
        # Load configuration
        self.config_manager = ConfigManager(config_path)
        self.config = self.config_manager.load_config()
        
        # Initialize core components
        self.metrics_collector = MetricsCollector(
            enable_prometheus=self.config.metrics.export_prometheus
        )
        self.metrics_tracker = AuditMetricsTracker(self.metrics_collector)
        
        # Initialize caching if enabled
        self.cache = None
        if self.config.performance.enable_caching:
            self.cache = AnalysisCache(
                max_age_hours=self.config.performance.cache_duration_hours
            )
        
        # Initialize plugin system
        self.plugin_manager = PluginManager()
        
        # Initialize retry configuration for external services
        self.retry_config = RetryConfig(
            max_attempts=self.config.ollama.max_retries,
            base_delay=self.config.ollama.retry_delay,
            backoff_factor=self.config.ollama.backoff_factor,
            max_delay=60.0,
            exceptions=(ConnectionError, TimeoutError, Exception)
        )
        
        # Session tracking
        self.session_id = f"audit_{uuid.uuid4().hex[:8]}"
        self.session_start = datetime.now()
        
        logger.info(f"Enterprise audit system initialized - Session: {self.session_id}")
    
    async def initialize(self) -> bool:
        """Initialize all system components."""
        try:
            # Validate environment
            if not self.config_manager.validate_environment():
                logger.warning("Environment validation failed, continuing with warnings")
            
            # Initialize plugins
            self.plugin_manager.load_plugin_config()
            await self.plugin_manager.discover_and_load_plugins()
            
            # Start metrics tracking
            await self.metrics_tracker.start_session({
                'config': self.config,
                'session_id': self.session_id
            })
            
            # Cleanup old cache entries if enabled
            if self.cache:
                await self.cache.cleanup_expired()
            
            logger.info("Enterprise audit system initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize audit system: {e}")
            return False
    
    async def run_comprehensive_audit(self) -> AuditResults:
        """Run a comprehensive audit with all enterprise features."""
        logger.info("🛡️ Starting comprehensive enterprise audit")
        
        try:
            # Initialize components
            if not await self.initialize():
                raise RuntimeError("System initialization failed")
            
            # Create tool runner and reporter
            tool_runner = AuditToolRunner(self.config)
            reporter = AuditReporter(self.config)
            
            # Run static analysis tools concurrently
            with self.metrics_collector.timer('static_analysis_duration'):
                static_results = await self._run_static_analysis_tools(tool_runner)
            
            # Collect files for analysis
            files_to_analyze = self._collect_files_for_analysis()
            logger.info(f"Found {len(files_to_analyze)} files for analysis")
            
            # Run comprehensive file analysis
            with self.metrics_collector.timer('file_analysis_duration'):
                file_analyses = await self._run_comprehensive_file_analysis(files_to_analyze)
            
            # Compile results
            results = AuditResults(
                timestamp=datetime.now().isoformat(),
                ruff=static_results['ruff'],
                bandit=static_results['bandit'],
                mypy=static_results['mypy'],
                files=file_analyses,
                config=self.config,
                errors=[]
            )
            
            # Calculate quality metrics and grade
            results = await self._calculate_audit_metrics(results)
            
            # Generate reports
            await self._generate_comprehensive_reports(results, reporter)
            
            # Send notifications
            await self._send_audit_notifications(results)
            
            # Record final metrics
            await self._finalize_metrics(results)
            
            logger.info("✅ Comprehensive enterprise audit completed successfully")
            return results
            
        except Exception as e:
            logger.error(f"❌ Enterprise audit failed: {e}")
            self.metrics_collector.record_error(
                'audit_system_failure',
                str(e),
                'enterprise_audit'
            )
            raise
        finally:
            await self.cleanup()
    
    async def _run_static_analysis_tools(self, tool_runner: AuditToolRunner) -> Dict[str, Any]:
        """Run all enabled static analysis tools."""
        results = {}
        
        # Run tools based on configuration
        tasks = []
        
        if self.config.tools.ruff.enabled:
            tasks.append(('ruff', tool_runner.run_ruff()))
        
        if self.config.tools.bandit.enabled:
            tasks.append(('bandit', tool_runner.run_bandit()))
        
        if self.config.tools.mypy.enabled:
            tasks.append(('mypy', tool_runner.run_mypy()))
        
        # Execute all tasks concurrently
        for tool_name, task in tasks:
            try:
                start_time = time.time()
                result = await task
                duration = time.time() - start_time
                
                results[tool_name] = result
                
                # Track metrics
                await self.metrics_tracker.track_tool_execution(
                    tool_name, duration, True, 
                    len(result) if isinstance(result, list) else 0
                )
                
                logger.info(f"✅ {tool_name.title()} completed in {duration:.2f}s")
                
            except Exception as e:
                logger.error(f"❌ {tool_name.title()} failed: {e}")
                results[tool_name] = {"error": str(e)}
                
                await self.metrics_tracker.track_tool_execution(
                    tool_name, 0, False
                )
        
        # Run plugin-based static analysis
        plugin_results = await self._run_plugin_static_analysis()
        if plugin_results:
            results['plugins'] = plugin_results
        
        return results
    
    async def _run_plugin_static_analysis(self) -> List[AnalysisResult]:
        """Run plugin-based static analysis tools."""
        results = []
        
        try:
            # Get all files that need static analysis
            files_for_static = self._collect_files_for_analysis()
            
            # Run plugin analysis on each supported file
            for file_path in files_for_static[:10]:  # Limit for demo
                plugin_results = await self.plugin_manager.run_static_analysis(file_path)
                results.extend(plugin_results)
            
        except Exception as e:
            logger.error(f"Plugin static analysis failed: {e}")
        
        return results
    
    def _collect_files_for_analysis(self) -> List[Path]:
        """Collect files for analysis based on configuration."""
        import fnmatch
        
        files = []
        
        for root, dirs, filenames in Path(".").walk():
            # Skip excluded directories
            dirs[:] = [
                d for d in dirs 
                if not any(fnmatch.fnmatch(str(root / d), pattern) 
                          for pattern in self.config.files.exclude_patterns)
            ]
            
            for filename in filenames:
                file_path = root / filename
                
                # Check if file type is supported
                if file_path.suffix in self.config.files.supported_extensions:
                    # Check file size
                    try:
                        if file_path.stat().st_size <= self.config.files.max_size_bytes:
                            files.append(file_path)
                        else:
                            logger.debug(f"Skipping large file: {file_path}")
                    except OSError:
                        logger.debug(f"Could not stat file: {file_path}")
        
        return files
    
    async def _run_comprehensive_file_analysis(self, files: List[Path]) -> List[FileAnalysis]:
        """Run comprehensive analysis on all files with caching and retry logic."""
        results = []
        
        # Create LLM analyzer with all enhancements
        base_analyzer = LLMAnalyzer(self.config)
        
        # Add caching if enabled
        if self.cache:
            analyzer = CachedLLMAnalyzer(base_analyzer, self.cache)
        else:
            analyzer = base_analyzer
        
        # Add retry logic
        reliable_analyzer = ReliableLLMAnalyzer(analyzer, self.retry_config)
        
        # Process files with controlled concurrency
        semaphore = asyncio.Semaphore(self.config.performance.parallel_llm_requests)
        
        async def analyze_single_file(file_path: Path) -> FileAnalysis:
            async with semaphore:
                start_time = time.time()
                cached = False
                
                try:
                    # Try cached analysis first if available
                    if self.cache:
                        cached_result = await self.cache.get_cached_analysis(file_path)
                        if cached_result:
                            cached = True
                            
                    # Run LLM analysis with retry logic
                    if not cached:
                        if hasattr(reliable_analyzer, 'analyze_file_with_retry'):
                            result = await reliable_analyzer.analyze_file_with_retry(file_path)
                        else:
                            # Fallback for compatibility
                            async with analyzer:
                                result = await analyzer.analyze_file(file_path)
                    else:
                        # Create result from cache
                        result = FileAnalysis(
                            path=str(file_path),
                            llm_analysis=cached_result,
                            size_bytes=file_path.stat().st_size
                        )
                    
                    # Run plugin analysis
                    plugin_results = await self.plugin_manager.run_llm_analysis(
                        file_path.read_text(encoding='utf-8', errors='ignore')[:2000],
                        file_path
                    )
                    
                    # Merge plugin results into main analysis
                    if plugin_results:
                        plugin_analysis = "\n".join([
                            f"Plugin {r.plugin_name}: {', '.join([issue['description'] for issue in r.issues])}"
                            for r in plugin_results if r.success
                        ])
                        result.llm_analysis += f"\n\nPlugin Analysis:\n{plugin_analysis}"
                    
                    duration = time.time() - start_time
                    
                    # Track metrics
                    await self.metrics_tracker.track_file_analysis(
                        str(file_path), duration, True, cached
                    )
                    
                    return result
                    
                except Exception as e:
                    duration = time.time() - start_time
                    logger.error(f"Failed to analyze {file_path}: {e}")
                    
                    await self.metrics_tracker.track_file_analysis(
                        str(file_path), duration, False, cached
                    )
                    
                    return FileAnalysis(
                        path=str(file_path),
                        llm_analysis="",
                        error=str(e)
                    )
        
        # Process all files
        tasks = [analyze_single_file(file_path) for file_path in files]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Filter out exceptions
        valid_results = [
            result for result in results 
            if isinstance(result, FileAnalysis)
        ]
        
        logger.info(f"Completed analysis of {len(valid_results)} files")
        return valid_results
    
    async def _calculate_audit_metrics(self, results: AuditResults) -> AuditResults:
        """Calculate comprehensive audit metrics and grade."""
        # Count issues
        ruff_issues = len(results.ruff) if isinstance(results.ruff, list) else 0
        bandit_issues = len(results.bandit.get('results', []))
        mypy_errors = results.mypy.count('error') if results.mypy else 0
        
        total_issues = ruff_issues + bandit_issues + mypy_errors
        
        # Calculate score using grading config
        weights = self.config.grading.weights
        score = 100
        
        # Deduct points based on issue types and weights
        score -= bandit_issues * weights.get('security_high', 10)
        score -= ruff_issues * weights.get('quality_warning', 3) 
        score -= mypy_errors * weights.get('quality_error', 8)
        
        score = max(0, score)
        
        # Determine grade
        thresholds = self.config.grading.thresholds
        if score >= thresholds['a_plus']:
            grade = 'A+'
        elif score >= thresholds['a']:
            grade = 'A'
        elif score >= thresholds['b_plus']:
            grade = 'B+'
        elif score >= thresholds['b']:
            grade = 'B'
        elif score >= thresholds['c_plus']:
            grade = 'C+'
        elif score >= thresholds['c']:
            grade = 'C'
        elif score >= thresholds['d']:
            grade = 'D'
        else:
            grade = 'F'
        
        # Add metrics to results
        results.audit_score = score
        results.audit_grade = grade
        results.total_issues = total_issues
        
        return results
    
    async def _generate_comprehensive_reports(self, results: AuditResults, reporter: AuditReporter) -> None:
        """Generate all configured report formats."""
        try:
            for format_type in self.config.output.formats:
                if format_type == 'json':
                    json_path = await reporter.save_json_report(results)
                    logger.info(f"📄 JSON report: {json_path}")
                
                elif format_type == 'markdown':
                    md_path = await reporter.generate_markdown_summary(results)
                    logger.info(f"📝 Markdown report: {md_path}")
                
                elif format_type == 'html':
                    # Generate HTML report (can be extended)
                    html_path = Path(self.config.output.reports_dir) / "audit_report.html"
                    await self._generate_html_report(results, html_path)
                    logger.info(f"🌐 HTML report: {html_path}")
                
                elif format_type == 'sarif':
                    # Generate SARIF for security tools integration
                    sarif_path = await self._generate_sarif_report(results)
                    logger.info(f"🔒 SARIF report: {sarif_path}")
        
        except Exception as e:
            logger.error(f"Failed to generate reports: {e}")
    
    async def _generate_html_report(self, results: AuditResults, output_path: Path) -> None:
        """Generate HTML report (basic implementation)."""
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>SyferStackV2 Audit Report</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 40px; }}
                .header {{ background: #2c3e50; color: white; padding: 20px; }}
                .grade-{results.audit_grade.lower().replace('+', 'plus')} {{ 
                    background: {'#27ae60' if results.audit_grade in ['A+', 'A'] else '#f39c12' if results.audit_grade in ['B+', 'B'] else '#e74c3c'};
                    color: white; padding: 10px; border-radius: 5px; 
                }}
                .metrics {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 20px; margin: 20px 0; }}
                .metric {{ background: #ecf0f1; padding: 15px; border-radius: 5px; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>🛡️ SyferStackV2 Security Audit Report</h1>
                <p>Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            </div>
            
            <div class="grade-{results.audit_grade.lower().replace('+', 'plus')}">
                <h2>Overall Grade: {results.audit_grade} ({results.audit_score:.1f}/100)</h2>
            </div>
            
            <div class="metrics">
                <div class="metric">
                    <h3>Files Analyzed</h3>
                    <p>{len(results.files)}</p>
                </div>
                <div class="metric">
                    <h3>Security Issues</h3>
                    <p>{len(results.bandit.get('results', []))}</p>
                </div>
                <div class="metric">
                    <h3>Code Quality Issues</h3>
                    <p>{len(results.ruff) if isinstance(results.ruff, list) else 0}</p>
                </div>
                <div class="metric">
                    <h3>Total Issues</h3>
                    <p>{getattr(results, 'total_issues', 0)}</p>
                </div>
            </div>
            
            <h2>Detailed Findings</h2>
            <div class="findings">
                <!-- Add detailed findings here -->
            </div>
        </body>
        </html>
        """
        
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(html_content)
    
    async def _generate_sarif_report(self, results: AuditResults) -> Path:
        """Generate SARIF format report for security tools integration."""
        import json
        
        sarif_report = {
            "version": "2.1.0",
            "schema": "https://schemastore.azurewebsites.net/schemas/json/sarif-2.1.0.json",
            "runs": [{
                "tool": {
                    "driver": {
                        "name": "SyferStackV2 Enterprise Audit",
                        "version": "2.0.0",
                        "informationUri": "https://github.com/otiseduncan/SyferStackV2"
                    }
                },
                "results": []
            }]
        }
        
        # Convert bandit results to SARIF
        for issue in results.bandit.get('results', []):
            sarif_result = {
                "ruleId": issue.get('test_id', 'unknown'),
                "message": {"text": issue.get('issue_text', 'Security issue detected')},
                "level": "error" if issue.get('issue_severity') == 'HIGH' else "warning",
                "locations": [{
                    "physicalLocation": {
                        "artifactLocation": {"uri": issue.get('filename', 'unknown')},
                        "region": {
                            "startLine": issue.get('line_number', 1),
                            "startColumn": 1
                        }
                    }
                }]
            }
            sarif_report["runs"][0]["results"].append(sarif_result)
        
        # Save SARIF report
        sarif_path = Path(self.config.output.reports_dir) / "audit_results.sarif"
        sarif_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(sarif_path, 'w') as f:
            json.dump(sarif_report, f, indent=2)
        
        return sarif_path
    
    async def _send_audit_notifications(self, results: AuditResults) -> None:
        """Send audit completion notifications."""
        try:
            notification_data = {
                'session_id': self.session_id,
                'total_files': len(results.files),
                'total_issues': getattr(results, 'total_issues', 0),
                'grade': results.audit_grade,
                'score': results.audit_score,
                'timestamp': results.timestamp
            }
            
            await self.plugin_manager.send_notifications('audit_complete', notification_data)
            
            # Send critical issue notifications
            critical_issues = [
                issue for issue in results.bandit.get('results', [])
                if issue.get('issue_severity') == 'HIGH'
            ]
            
            for issue in critical_issues:
                await self.plugin_manager.send_notifications('critical_issue_found', {
                    'file_path': issue.get('filename'),
                    'description': issue.get('issue_text'),
                    'severity': issue.get('issue_severity')
                })
        
        except Exception as e:
            logger.error(f"Failed to send notifications: {e}")
    
    async def _finalize_metrics(self, results: AuditResults) -> None:
        """Record final audit metrics."""
        try:
            # End the audit session
            final_data = {
                'audit_score': results.audit_score,
                'audit_grade': results.audit_grade,
                'total_issues': getattr(results, 'total_issues', 0),
                'config_hash': hash(str(self.config)),
                'git_branch': 'main',  # Could be detected from git
                'git_commit': 'HEAD'   # Could be detected from git
            }
            
            await self.metrics_tracker.end_session(final_data)
            
            logger.info(f"📊 Audit metrics recorded - Session: {self.session_id}")
        
        except Exception as e:
            logger.error(f"Failed to finalize metrics: {e}")
    
    async def cleanup(self) -> None:
        """Cleanup all system resources."""
        try:
            await self.plugin_manager.cleanup_all()
            logger.info("🧹 Enterprise audit system cleanup completed")
        except Exception as e:
            logger.error(f"Cleanup failed: {e}")


async def main():
    """Main entry point for enterprise audit system."""
    import argparse
    
    parser = argparse.ArgumentParser(description="SyferStackV2 Enterprise Audit System")
    parser.add_argument('--config', type=str, help='Configuration file path')
    parser.add_argument('--output-dir', type=str, help='Output directory for reports')
    parser.add_argument('--plugins-config', type=str, help='Plugins configuration file')
    
    args = parser.parse_args()
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    try:
        # Create enterprise audit system
        config_path = Path(args.config) if args.config else None
        audit_system = EnterpriseAuditSystem(config_path)
        
        # Override output directory if specified
        if args.output_dir:
            audit_system.config.output.reports_dir = args.output_dir
        
        # Run comprehensive audit
        results = await audit_system.run_comprehensive_audit()
        
        # Print summary
        print(f"\n🎯 Enterprise Audit Complete!")
        print(f"   Grade: {results.audit_grade} ({results.audit_score:.1f}/100)")
        print(f"   Files: {len(results.files)}")
        print(f"   Issues: {getattr(results, 'total_issues', 0)}")
        print(f"   Session: {audit_system.session_id}")
        
        # Exit with appropriate code
        if results.audit_grade in ['A+', 'A', 'B+']:
            sys.exit(0)  # Success
        elif results.audit_grade in ['B', 'C+', 'C']:
            sys.exit(1)  # Warning
        else:
            sys.exit(2)  # Failure
        
    except Exception as e:
        logger.error(f"Enterprise audit failed: {e}")
        sys.exit(3)  # System error


if __name__ == "__main__":
    asyncio.run(main())