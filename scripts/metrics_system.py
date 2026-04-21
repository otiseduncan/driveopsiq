#!/usr/bin/env python3
"""
Comprehensive metrics collection and monitoring system
Tracks performance, failures, and audit quality metrics
"""

import asyncio
import json
import logging
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Counter as CounterType
from collections import defaultdict, Counter
import threading
from contextlib import asynccontextmanager
import sqlite3

logger = logging.getLogger(__name__)


@dataclass
class PerformanceMetric:
    """Individual performance measurement."""
    name: str
    value: float
    unit: str
    timestamp: datetime
    labels: Dict[str, str] = field(default_factory=dict)


@dataclass
class ErrorMetric:
    """Error/failure tracking."""
    error_type: str
    error_message: str
    component: str
    timestamp: datetime
    count: int = 1
    context: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AuditQualityMetrics:
    """Quality metrics for audit results."""
    total_files_scanned: int
    files_analyzed: int
    files_skipped: int
    files_with_errors: int
    
    # Static analysis results
    ruff_issues: int
    bandit_issues: int
    mypy_errors: int
    
    # LLM analysis metrics
    llm_analysis_success_rate: float
    avg_analysis_time: float
    total_analysis_time: float
    
    # Cache metrics
    cache_hit_rate: float
    cache_size_mb: float
    
    # Overall score
    audit_score: float
    audit_grade: str


@dataclass
class SystemMetrics:
    """System resource usage metrics."""
    cpu_usage_percent: float
    memory_usage_mb: float
    disk_usage_mb: float
    network_requests: int
    concurrent_operations: int
    timestamp: datetime


class MetricsCollector:
    """Centralized metrics collection and storage."""
    
    def __init__(self, db_path: Path = None, enable_prometheus: bool = False):
        self.db_path = db_path or Path(".audit_cache/metrics.db")
        self.db_path.parent.mkdir(exist_ok=True)
        
        self.enable_prometheus = enable_prometheus
        self._init_database()
        
        # In-memory counters for fast access
        self._counters: Dict[str, int] = defaultdict(int)
        self._gauges: Dict[str, float] = defaultdict(float)
        self._histograms: Dict[str, List[float]] = defaultdict(list)
        self._errors: List[ErrorMetric] = []
        
        # Thread safety
        self._lock = threading.Lock()
        
        # Performance tracking
        self._operation_timers: Dict[str, float] = {}
        
        if enable_prometheus:
            self._setup_prometheus()
    
    def _init_database(self) -> None:
        """Initialize SQLite database for metrics storage."""
        with sqlite3.connect(self.db_path) as conn:
            # Performance metrics table
            conn.execute('''
                CREATE TABLE IF NOT EXISTS performance_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    value REAL NOT NULL,
                    unit TEXT,
                    timestamp TEXT NOT NULL,
                    labels TEXT
                )
            ''')
            
            # Error metrics table
            conn.execute('''
                CREATE TABLE IF NOT EXISTS error_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    error_type TEXT NOT NULL,
                    error_message TEXT,
                    component TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    count INTEGER DEFAULT 1,
                    context TEXT
                )
            ''')
            
            # Audit sessions table
            conn.execute('''
                CREATE TABLE IF NOT EXISTS audit_sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT UNIQUE NOT NULL,
                    start_time TEXT NOT NULL,
                    end_time TEXT,
                    total_files INTEGER,
                    files_analyzed INTEGER,
                    files_with_errors INTEGER,
                    total_issues INTEGER,
                    audit_score REAL,
                    audit_grade TEXT,
                    config_hash TEXT,
                    git_branch TEXT,
                    git_commit TEXT
                )
            ''')
            
            # Create indexes
            conn.execute('CREATE INDEX IF NOT EXISTS idx_perf_name_time ON performance_metrics(name, timestamp)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_error_type_time ON error_metrics(error_type, timestamp)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_session_time ON audit_sessions(start_time)')
    
    def _setup_prometheus(self) -> None:
        """Setup Prometheus metrics export (optional)."""
        try:
            from prometheus_client import Counter, Gauge, Histogram, start_http_server
            
            # Define Prometheus metrics
            self.prom_counters = {
                'audit_files_total': Counter('audit_files_total', 'Total files processed'),
                'audit_errors_total': Counter('audit_errors_total', 'Total errors encountered', ['error_type', 'component']),
                'audit_cache_hits_total': Counter('audit_cache_hits_total', 'Cache hits'),
                'audit_cache_misses_total': Counter('audit_cache_misses_total', 'Cache misses'),
            }
            
            self.prom_gauges = {
                'audit_session_duration': Gauge('audit_session_duration_seconds', 'Audit session duration'),
                'audit_files_current': Gauge('audit_files_current', 'Files currently being processed'),
                'audit_score': Gauge('audit_score', 'Latest audit score'),
                'llm_requests_active': Gauge('llm_requests_active', 'Active LLM requests'),
            }
            
            self.prom_histograms = {
                'llm_request_duration': Histogram('llm_request_duration_seconds', 'LLM request duration'),
                'file_analysis_duration': Histogram('file_analysis_duration_seconds', 'File analysis duration'),
                'static_tool_duration': Histogram('static_tool_duration_seconds', 'Static tool execution duration', ['tool']),
            }
            
            # Start Prometheus HTTP server
            start_http_server(9090)
            logger.info("Prometheus metrics server started on port 9090")
            
        except ImportError:
            logger.warning("prometheus_client not installed, Prometheus metrics disabled")
            self.enable_prometheus = False
    
    def increment_counter(self, name: str, value: int = 1, labels: Dict[str, str] = None) -> None:
        """Increment a counter metric."""
        with self._lock:
            self._counters[name] += value
            
            if self.enable_prometheus and name in self.prom_counters:
                if labels:
                    self.prom_counters[name].labels(**labels).inc(value)
                else:
                    self.prom_counters[name].inc(value)
    
    def set_gauge(self, name: str, value: float, labels: Dict[str, str] = None) -> None:
        """Set a gauge metric value."""
        with self._lock:
            self._gauges[name] = value
            
            if self.enable_prometheus and name in self.prom_gauges:
                if labels:
                    self.prom_gauges[name].labels(**labels).set(value)
                else:
                    self.prom_gauges[name].set(value)
    
    def record_histogram(self, name: str, value: float, labels: Dict[str, str] = None) -> None:
        """Record a histogram value."""
        with self._lock:
            self._histograms[name].append(value)
            
            if self.enable_prometheus and name in self.prom_histograms:
                if labels:
                    self.prom_histograms[name].labels(**labels).observe(value)
                else:
                    self.prom_histograms[name].observe(value)
    
    def record_error(self, error_type: str, error_message: str, component: str, 
                    context: Dict[str, Any] = None) -> None:
        """Record an error occurrence."""
        error = ErrorMetric(
            error_type=error_type,
            error_message=error_message,
            component=component,
            timestamp=datetime.now(),
            context=context or {}
        )
        
        with self._lock:
            self._errors.append(error)
            
            # Store in database
            asyncio.create_task(self._store_error_async(error))
            
            # Update Prometheus
            if self.enable_prometheus:
                self.prom_counters['audit_errors_total'].labels(
                    error_type=error_type, 
                    component=component
                ).inc()
    
    async def _store_error_async(self, error: ErrorMetric) -> None:
        """Store error in database asynchronously."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute('''
                    INSERT INTO error_metrics 
                    (error_type, error_message, component, timestamp, context)
                    VALUES (?, ?, ?, ?, ?)
                ''', (
                    error.error_type,
                    error.error_message,
                    error.component,
                    error.timestamp.isoformat(),
                    json.dumps(error.context)
                ))
        except Exception as e:
            logger.error(f"Failed to store error metric: {e}")
    
    @asynccontextmanager
    async def timer(self, name: str, labels: Dict[str, str] = None):
        """Context manager for timing operations."""
        start_time = time.time()
        try:
            yield
        finally:
            duration = time.time() - start_time
            self.record_histogram(name, duration, labels)
            
            # Store performance metric
            metric = PerformanceMetric(
                name=name,
                value=duration,
                unit="seconds",
                timestamp=datetime.now(),
                labels=labels or {}
            )
            await self._store_performance_metric(metric)
    
    async def _store_performance_metric(self, metric: PerformanceMetric) -> None:
        """Store performance metric in database."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute('''
                    INSERT INTO performance_metrics 
                    (name, value, unit, timestamp, labels)
                    VALUES (?, ?, ?, ?, ?)
                ''', (
                    metric.name,
                    metric.value,
                    metric.unit,
                    metric.timestamp.isoformat(),
                    json.dumps(metric.labels)
                ))
        except Exception as e:
            logger.error(f"Failed to store performance metric: {e}")
    
    async def record_audit_session(self, session_data: Dict[str, Any]) -> None:
        """Record complete audit session metrics."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute('''
                    INSERT INTO audit_sessions 
                    (session_id, start_time, end_time, total_files, files_analyzed,
                     files_with_errors, total_issues, audit_score, audit_grade,
                     config_hash, git_branch, git_commit)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    session_data.get('session_id'),
                    session_data.get('start_time'),
                    session_data.get('end_time'),
                    session_data.get('total_files', 0),
                    session_data.get('files_analyzed', 0),
                    session_data.get('files_with_errors', 0),
                    session_data.get('total_issues', 0),
                    session_data.get('audit_score', 0.0),
                    session_data.get('audit_grade', 'F'),
                    session_data.get('config_hash'),
                    session_data.get('git_branch'),
                    session_data.get('git_commit')
                ))
        except Exception as e:
            logger.error(f"Failed to record audit session: {e}")
    
    def get_current_metrics(self) -> Dict[str, Any]:
        """Get current metrics snapshot."""
        with self._lock:
            return {
                'counters': dict(self._counters),
                'gauges': dict(self._gauges),
                'histograms': {name: {
                    'count': len(values),
                    'min': min(values) if values else 0,
                    'max': max(values) if values else 0,
                    'avg': sum(values) / len(values) if values else 0
                } for name, values in self._histograms.items()},
                'errors': len(self._errors),
                'timestamp': datetime.now().isoformat()
            }
    
    async def get_metrics_summary(self, hours: int = 24) -> Dict[str, Any]:
        """Get metrics summary for the last N hours."""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                # Performance metrics summary
                cursor.execute('''
                    SELECT name, COUNT(*) as count, AVG(value) as avg, MIN(value) as min, MAX(value) as max
                    FROM performance_metrics 
                    WHERE timestamp > ?
                    GROUP BY name
                ''', (cutoff_time.isoformat(),))
                
                performance_summary = {}
                for row in cursor.fetchall():
                    performance_summary[row['name']] = {
                        'count': row['count'],
                        'avg': row['avg'],
                        'min': row['min'],
                        'max': row['max']
                    }
                
                # Error summary
                cursor.execute('''
                    SELECT error_type, component, COUNT(*) as count
                    FROM error_metrics 
                    WHERE timestamp > ?
                    GROUP BY error_type, component
                ''', (cutoff_time.isoformat(),))
                
                error_summary = {}
                for row in cursor.fetchall():
                    key = f"{row['error_type']}.{row['component']}"
                    error_summary[key] = row['count']
                
                # Audit sessions summary
                cursor.execute('''
                    SELECT COUNT(*) as sessions, AVG(audit_score) as avg_score,
                           AVG(total_files) as avg_files, AVG(total_issues) as avg_issues
                    FROM audit_sessions 
                    WHERE start_time > ?
                ''', (cutoff_time.isoformat(),))
                
                session_row = cursor.fetchone()
                session_summary = {
                    'total_sessions': session_row['sessions'],
                    'avg_score': session_row['avg_score'] or 0,
                    'avg_files': session_row['avg_files'] or 0,
                    'avg_issues': session_row['avg_issues'] or 0
                }
                
                return {
                    'time_range_hours': hours,
                    'performance': performance_summary,
                    'errors': error_summary,
                    'sessions': session_summary,
                    'generated_at': datetime.now().isoformat()
                }
                
        except Exception as e:
            logger.error(f"Failed to get metrics summary: {e}")
            return {'error': str(e)}
    
    async def export_metrics(self, format_type: str = 'json') -> str:
        """Export metrics in various formats."""
        if format_type == 'json':
            current = self.get_current_metrics()
            summary = await self.get_metrics_summary()
            
            return json.dumps({
                'current': current,
                'summary': summary,
                'export_time': datetime.now().isoformat()
            }, indent=2)
        
        elif format_type == 'prometheus':
            # Export Prometheus format
            lines = []
            with self._lock:
                for name, value in self._counters.items():
                    lines.append(f"# TYPE {name} counter")
                    lines.append(f"{name} {value}")
                
                for name, value in self._gauges.items():
                    lines.append(f"# TYPE {name} gauge")
                    lines.append(f"{name} {value}")
            
            return '\n'.join(lines)
        
        else:
            raise ValueError(f"Unsupported format: {format_type}")


class AuditMetricsTracker:
    """High-level metrics tracking for audit operations."""
    
    def __init__(self, collector: MetricsCollector):
        self.collector = collector
        self.session_id = f"audit_{int(time.time())}"
        self.session_start = datetime.now()
        
        # Session tracking
        self.total_files = 0
        self.files_analyzed = 0
        self.files_with_errors = 0
        self.analysis_times: List[float] = []
        self.cache_hits = 0
        self.cache_misses = 0
    
    async def start_session(self, config_info: Dict[str, Any] = None) -> str:
        """Start a new audit session."""
        self.collector.set_gauge('audit_session_active', 1)
        
        logger.info(f"Started audit session: {self.session_id}")
        return self.session_id
    
    async def track_file_analysis(self, file_path: str, duration: float, 
                                success: bool, cached: bool = False) -> None:
        """Track individual file analysis."""
        self.total_files += 1
        
        if success:
            self.files_analyzed += 1
            self.analysis_times.append(duration)
        else:
            self.files_with_errors += 1
        
        if cached:
            self.cache_hits += 1
        else:
            self.cache_misses += 1
        
        # Update real-time metrics
        self.collector.increment_counter('audit_files_total')
        self.collector.record_histogram('file_analysis_duration', duration)
        
        if cached:
            self.collector.increment_counter('audit_cache_hits_total')
        else:
            self.collector.increment_counter('audit_cache_misses_total')
    
    async def track_tool_execution(self, tool_name: str, duration: float, 
                                 success: bool, issues_found: int = 0) -> None:
        """Track static analysis tool execution."""
        self.collector.record_histogram(
            'static_tool_duration', 
            duration, 
            {'tool': tool_name}
        )
        
        if not success:
            self.collector.record_error(
                'tool_execution_failed',
                f'{tool_name} execution failed',
                'static_analysis'
            )
    
    async def track_llm_request(self, duration: float, success: bool, 
                              model: str, tokens: int = 0) -> None:
        """Track LLM API requests."""
        self.collector.record_histogram('llm_request_duration', duration)
        
        if success:
            self.collector.increment_counter('llm_requests_success_total')
        else:
            self.collector.increment_counter('llm_requests_failed_total')
            self.collector.record_error(
                'llm_request_failed',
                'LLM API request failed',
                'llm_analyzer',
                {'model': model, 'duration': duration}
            )
    
    async def end_session(self, final_results: Dict[str, Any]) -> None:
        """End audit session and record final metrics."""
        session_duration = (datetime.now() - self.session_start).total_seconds()
        
        # Calculate quality metrics
        audit_score = final_results.get('audit_score', 0)
        audit_grade = final_results.get('audit_grade', 'F')
        total_issues = final_results.get('total_issues', 0)
        
        # Calculate rates
        cache_hit_rate = (self.cache_hits / (self.cache_hits + self.cache_misses) * 100) if (self.cache_hits + self.cache_misses) > 0 else 0
        success_rate = (self.files_analyzed / self.total_files * 100) if self.total_files > 0 else 0
        avg_analysis_time = sum(self.analysis_times) / len(self.analysis_times) if self.analysis_times else 0
        
        # Update final gauges
        self.collector.set_gauge('audit_session_active', 0)
        self.collector.set_gauge('audit_session_duration', session_duration)
        self.collector.set_gauge('audit_score', audit_score)
        self.collector.set_gauge('audit_success_rate', success_rate)
        self.collector.set_gauge('audit_cache_hit_rate', cache_hit_rate)
        
        # Record session in database
        session_data = {
            'session_id': self.session_id,
            'start_time': self.session_start.isoformat(),
            'end_time': datetime.now().isoformat(),
            'total_files': self.total_files,
            'files_analyzed': self.files_analyzed,
            'files_with_errors': self.files_with_errors,
            'total_issues': total_issues,
            'audit_score': audit_score,
            'audit_grade': audit_grade,
            'config_hash': final_results.get('config_hash'),
            'git_branch': final_results.get('git_branch'),
            'git_commit': final_results.get('git_commit')
        }
        
        await self.collector.record_audit_session(session_data)
        
        logger.info(f"Audit session completed: {self.session_id}")
        logger.info(f"Duration: {session_duration:.2f}s, Files: {self.total_files}, "
                   f"Success Rate: {success_rate:.1f}%, Score: {audit_score:.1f}")


# CLI for metrics management
async def main():
    """Command line interface for metrics."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Audit metrics management")
    parser.add_argument('--current', action='store_true', help='Show current metrics')
    parser.add_argument('--summary', type=int, default=24, help='Show summary for last N hours')
    parser.add_argument('--export', type=str, choices=['json', 'prometheus'], help='Export metrics format')
    parser.add_argument('--clear', action='store_true', help='Clear all metrics')
    parser.add_argument('--db-path', type=str, help='Database path')
    
    args = parser.parse_args()
    
    db_path = Path(args.db_path) if args.db_path else None
    collector = MetricsCollector(db_path)
    
    if args.current:
        metrics = collector.get_current_metrics()
        print("📊 Current Metrics:")
        print(json.dumps(metrics, indent=2))
    
    if args.summary:
        summary = await collector.get_metrics_summary(args.summary)
        print(f"📈 Metrics Summary (last {args.summary} hours):")
        print(json.dumps(summary, indent=2))
    
    if args.export:
        output = await collector.export_metrics(args.export)
        print(output)
    
    if args.clear:
        # Clear database tables
        with sqlite3.connect(collector.db_path) as conn:
            conn.execute('DELETE FROM performance_metrics')
            conn.execute('DELETE FROM error_metrics')
            conn.execute('DELETE FROM audit_sessions')
        print("🗑️ Cleared all metrics")


if __name__ == "__main__":
    asyncio.run(main())