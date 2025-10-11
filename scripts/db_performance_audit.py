#!/usr/bin/env python3
"""
Database Performance Audit Script
Analyzes database performance, identifies slow queries, and suggests optimizations.
"""

import asyncio
import json
import logging
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional
import argparse

from sqlalchemy import text, inspect
from sqlalchemy.engine import Row
from sqlalchemy.exc import SQLAlchemyError

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import database components
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'backend'))

from app.core.database import engine, get_db_session
from app.core.config import settings


class DatabasePerformanceAuditor:
    """
    Comprehensive database performance auditor with analysis and recommendations.
    """
    
    def __init__(self):
        self.results = {
            "timestamp": datetime.now().isoformat(),
            "database_type": self._detect_database_type(),
            "connection_info": {},
            "performance_metrics": {},
            "slow_queries": [],
            "index_analysis": {},
            "table_stats": {},
            "recommendations": [],
        }
    
    def _detect_database_type(self) -> str:
        """Detect the database type from connection URL."""
        url = str(engine.url)
        if "postgresql" in url:
            return "postgresql"
        elif "mysql" in url:
            return "mysql"
        elif "sqlite" in url:
            return "sqlite"
        else:
            return "unknown"
    
    async def run_full_audit(self) -> Dict[str, Any]:
        """
        Run comprehensive database performance audit.
        
        Returns:
            Dict[str, Any]: Complete audit results
        """
        logger.info("Starting database performance audit")
        
        try:
            async with get_db_session() as session:
                # Basic connection and pool info
                await self._audit_connection_info(session)
                
                # Performance metrics
                await self._audit_performance_metrics(session)
                
                # Query analysis
                await self._audit_query_performance(session)
                
                # Index analysis
                await self._audit_indexes(session)
                
                # Table statistics
                await self._audit_table_stats(session)
                
                # Generate recommendations
                self._generate_recommendations()
                
            logger.info("Database audit completed successfully")
            return self.results
            
        except Exception as e:
            logger.error(f"Database audit failed: {e}")
            self.results["error"] = str(e)
            return self.results
    
    async def _audit_connection_info(self, session) -> None:
        """Audit database connection and pool information."""
        try:
            # Pool statistics
            pool = engine.pool
            self.results["connection_info"] = {
                "pool_size": pool.size(),
                "checked_in": pool.checkedin(),
                "checked_out": pool.checkedout(),
                "overflow": pool.overflow(),
                "invalid": pool.invalid(),
            }
            
            # Database version and settings
            if self.results["database_type"] == "postgresql":
                result = await session.execute(text("SELECT version()"))
                version = result.scalar()
                self.results["connection_info"]["version"] = version
                
                # PostgreSQL specific settings
                settings_query = """
                SELECT name, setting, unit, category 
                FROM pg_settings 
                WHERE name IN (
                    'shared_buffers', 'effective_cache_size', 'work_mem',
                    'maintenance_work_mem', 'max_connections', 'random_page_cost',
                    'effective_io_concurrency', 'checkpoint_completion_target',
                    'wal_buffers', 'default_statistics_target'
                )
                ORDER BY category, name
                """
                result = await session.execute(text(settings_query))
                self.results["connection_info"]["settings"] = [
                    dict(row._mapping) for row in result
                ]
                
            elif self.results["database_type"] == "sqlite":
                # SQLite version and pragmas
                result = await session.execute(text("SELECT sqlite_version()"))
                self.results["connection_info"]["version"] = result.scalar()
                
                pragmas = [
                    "cache_size", "page_size", "journal_mode", "synchronous",
                    "temp_store", "mmap_size", "foreign_keys"
                ]
                pragma_values = {}
                for pragma in pragmas:
                    try:
                        result = await session.execute(text(f"PRAGMA {pragma}"))
                        pragma_values[pragma] = result.scalar()
                    except:
                        pass
                self.results["connection_info"]["pragmas"] = pragma_values
                
        except Exception as e:
            logger.warning(f"Failed to audit connection info: {e}")
    
    async def _audit_performance_metrics(self, session) -> None:
        """Audit database performance metrics."""
        try:
            start_time = time.time()
            
            # Basic connectivity test
            await session.execute(text("SELECT 1"))
            connection_time = (time.time() - start_time) * 1000
            
            self.results["performance_metrics"]["connection_time_ms"] = round(connection_time, 2)
            
            if self.results["database_type"] == "postgresql":
                # PostgreSQL statistics
                stats_query = """
                SELECT 
                    schemaname,
                    tablename,
                    attname,
                    n_distinct,
                    correlation
                FROM pg_stats 
                WHERE schemaname = 'public'
                LIMIT 20
                """
                result = await session.execute(text(stats_query))
                self.results["performance_metrics"]["table_statistics"] = [
                    dict(row._mapping) for row in result
                ]
                
                # Database size
                db_size_query = """
                SELECT pg_size_pretty(pg_database_size(current_database())) as database_size
                """
                result = await session.execute(text(db_size_query))
                self.results["performance_metrics"]["database_size"] = result.scalar()
                
            elif self.results["database_type"] == "sqlite":
                # SQLite statistics
                result = await session.execute(text("PRAGMA page_count"))
                page_count = result.scalar()
                result = await session.execute(text("PRAGMA page_size"))
                page_size = result.scalar()
                
                self.results["performance_metrics"]["database_size_bytes"] = page_count * page_size
                self.results["performance_metrics"]["page_count"] = page_count
                self.results["performance_metrics"]["page_size"] = page_size
                
        except Exception as e:
            logger.warning(f"Failed to audit performance metrics: {e}")
    
    async def _audit_query_performance(self, session) -> None:
        """Audit query performance and identify slow queries."""
        try:
            if self.results["database_type"] == "postgresql":
                # Check if pg_stat_statements is available
                check_query = """
                SELECT EXISTS (
                    SELECT 1 FROM pg_extension WHERE extname = 'pg_stat_statements'
                ) as has_pg_stat_statements
                """
                result = await session.execute(text(check_query))
                has_pg_stat_statements = result.scalar()
                
                if has_pg_stat_statements:
                    # Get slow queries from pg_stat_statements
                    slow_queries_query = """
                    SELECT 
                        query,
                        calls,
                        total_exec_time,
                        mean_exec_time,
                        stddev_exec_time,
                        rows,
                        100.0 * shared_blks_hit / nullif(shared_blks_hit + shared_blks_read, 0) AS hit_percent
                    FROM pg_stat_statements 
                    WHERE mean_exec_time > 100  -- queries taking more than 100ms on average
                    ORDER BY mean_exec_time DESC
                    LIMIT 10
                    """
                    result = await session.execute(text(slow_queries_query))
                    self.results["slow_queries"] = [
                        dict(row._mapping) for row in result
                    ]
                else:
                    logger.info("pg_stat_statements extension not available")
                    
            # Test query performance with sample operations
            await self._test_query_performance(session)
            
        except Exception as e:
            logger.warning(f"Failed to audit query performance: {e}")
    
    async def _test_query_performance(self, session) -> None:
        """Test performance of common query patterns."""
        test_queries = []
        
        try:
            # Test simple select performance
            start_time = time.time()
            await session.execute(text("SELECT 1"))
            simple_query_time = (time.time() - start_time) * 1000
            
            test_queries.append({
                "query": "SELECT 1",
                "execution_time_ms": round(simple_query_time, 2),
                "type": "simple_select"
            })
            
            # Test table existence and basic operations
            if self.results["database_type"] == "postgresql":
                # Check if users table exists
                table_exists_query = """
                SELECT EXISTS (
                    SELECT 1 FROM information_schema.tables 
                    WHERE table_schema = 'public' AND table_name = 'users'
                )
                """
                start_time = time.time()
                result = await session.execute(text(table_exists_query))
                table_exists = result.scalar()
                table_check_time = (time.time() - start_time) * 1000
                
                test_queries.append({
                    "query": "Table existence check",
                    "execution_time_ms": round(table_check_time, 2),
                    "type": "metadata_query",
                    "table_exists": table_exists
                })
                
                if table_exists:
                    # Test count query performance
                    start_time = time.time()
                    result = await session.execute(text("SELECT COUNT(*) FROM users"))
                    count = result.scalar()
                    count_time = (time.time() - start_time) * 1000
                    
                    test_queries.append({
                        "query": "SELECT COUNT(*) FROM users",
                        "execution_time_ms": round(count_time, 2),
                        "type": "count_query",
                        "result": count
                    })
            
            self.results["performance_metrics"]["test_queries"] = test_queries
            
        except Exception as e:
            logger.warning(f"Failed to test query performance: {e}")
    
    async def _audit_indexes(self, session) -> None:
        """Audit database indexes and suggest optimizations."""
        try:
            if self.results["database_type"] == "postgresql":
                # Get index information
                index_query = """
                SELECT 
                    schemaname,
                    tablename,
                    indexname,
                    indexdef,
                    pg_size_pretty(pg_relation_size(indexrelid)) as index_size
                FROM pg_indexes 
                WHERE schemaname = 'public'
                ORDER BY tablename, indexname
                """
                result = await session.execute(text(index_query))
                indexes = [dict(row._mapping) for row in result]
                
                # Get index usage statistics
                index_usage_query = """
                SELECT 
                    schemaname,
                    tablename,
                    indexrelname,
                    idx_tup_read,
                    idx_tup_fetch,
                    idx_scan
                FROM pg_stat_user_indexes
                WHERE schemaname = 'public'
                ORDER BY idx_scan DESC
                """
                result = await session.execute(text(index_usage_query))
                index_usage = [dict(row._mapping) for row in result]
                
                self.results["index_analysis"] = {
                    "indexes": indexes,
                    "usage_stats": index_usage,
                    "total_indexes": len(indexes)
                }
                
            elif self.results["database_type"] == "sqlite":
                # SQLite index information
                result = await session.execute(text("""
                    SELECT name, sql, type 
                    FROM sqlite_master 
                    WHERE type = 'index' AND name NOT LIKE 'sqlite_%'
                """))
                indexes = [dict(row._mapping) for row in result]
                
                self.results["index_analysis"] = {
                    "indexes": indexes,
                    "total_indexes": len(indexes)
                }
                
        except Exception as e:
            logger.warning(f"Failed to audit indexes: {e}")
    
    async def _audit_table_stats(self, session) -> None:
        """Audit table statistics and storage information."""
        try:
            if self.results["database_type"] == "postgresql":
                # Table size and statistics
                table_stats_query = """
                SELECT 
                    schemaname,
                    tablename,
                    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as total_size,
                    pg_size_pretty(pg_relation_size(schemaname||'.'||tablename)) as table_size,
                    n_tup_ins,
                    n_tup_upd,
                    n_tup_del,
                    n_live_tup,
                    n_dead_tup,
                    last_vacuum,
                    last_autovacuum,
                    last_analyze,
                    last_autoanalyze
                FROM pg_stat_user_tables
                WHERE schemaname = 'public'
                ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC
                """
                result = await session.execute(text(table_stats_query))
                self.results["table_stats"] = [dict(row._mapping) for row in result]
                
            elif self.results["database_type"] == "sqlite":
                # SQLite table information
                result = await session.execute(text("""
                    SELECT name, sql 
                    FROM sqlite_master 
                    WHERE type = 'table' AND name NOT LIKE 'sqlite_%'
                """))
                tables = [dict(row._mapping) for row in result]
                
                # Get row counts for each table
                table_stats = []
                for table in tables:
                    try:
                        count_result = await session.execute(
                            text(f"SELECT COUNT(*) as row_count FROM {table['name']}")
                        )
                        row_count = count_result.scalar()
                        table_stats.append({
                            "tablename": table["name"],
                            "row_count": row_count,
                            "definition": table["sql"]
                        })
                    except Exception as e:
                        logger.warning(f"Failed to get count for table {table['name']}: {e}")
                
                self.results["table_stats"] = table_stats
                
        except Exception as e:
            logger.warning(f"Failed to audit table stats: {e}")
    
    def _generate_recommendations(self) -> None:
        """Generate performance optimization recommendations."""
        recommendations = []
        
        # Connection pool recommendations
        pool_info = self.results.get("connection_info", {})
        if pool_info.get("checked_out", 0) > pool_info.get("pool_size", 10) * 0.8:
            recommendations.append({
                "category": "connection_pool",
                "priority": "high",
                "issue": "High connection pool utilization",
                "recommendation": "Consider increasing pool_size or max_overflow settings",
                "details": f"Current utilization: {pool_info.get('checked_out', 0)}/{pool_info.get('pool_size', 0)}"
            })
        
        # Query performance recommendations
        slow_queries = self.results.get("slow_queries", [])
        if slow_queries:
            for query in slow_queries[:3]:  # Top 3 slow queries
                recommendations.append({
                    "category": "query_performance",
                    "priority": "medium",
                    "issue": f"Slow query detected: avg {query.get('mean_exec_time', 0):.2f}ms",
                    "recommendation": "Consider adding indexes or optimizing query structure",
                    "details": query.get("query", "")[:100] + "..."
                })
        
        # Index recommendations
        index_analysis = self.results.get("index_analysis", {})
        indexes = index_analysis.get("indexes", [])
        usage_stats = index_analysis.get("usage_stats", [])
        
        # Find unused indexes
        used_indexes = {stat["indexrelname"] for stat in usage_stats if stat.get("idx_scan", 0) > 0}
        all_indexes = {idx["indexname"] for idx in indexes if not idx["indexname"].endswith("_pkey")}
        unused_indexes = all_indexes - used_indexes
        
        if unused_indexes:
            recommendations.append({
                "category": "index_optimization",
                "priority": "low",
                "issue": f"Found {len(unused_indexes)} potentially unused indexes",
                "recommendation": "Review and consider dropping unused indexes to improve write performance",
                "details": list(unused_indexes)[:5]
            })
        
        # Table maintenance recommendations
        if self.results["database_type"] == "postgresql":
            table_stats = self.results.get("table_stats", [])
            for table in table_stats:
                dead_tuples = table.get("n_dead_tup", 0)
                live_tuples = table.get("n_live_tup", 1)
                
                if dead_tuples > live_tuples * 0.1:  # More than 10% dead tuples
                    recommendations.append({
                        "category": "maintenance",
                        "priority": "medium",
                        "issue": f"Table {table['tablename']} has high dead tuple ratio",
                        "recommendation": "Run VACUUM ANALYZE to reclaim space and update statistics",
                        "details": f"Dead tuples: {dead_tuples}, Live tuples: {live_tuples}"
                    })
        
        # Performance test recommendations
        test_queries = self.results.get("performance_metrics", {}).get("test_queries", [])
        for test in test_queries:
            if test.get("execution_time_ms", 0) > 100:
                recommendations.append({
                    "category": "query_performance",
                    "priority": "medium",
                    "issue": f"Slow {test['type']}: {test['execution_time_ms']}ms",
                    "recommendation": "Investigate network latency or database configuration",
                    "details": test.get("query", "")
                })
        
        # Database-specific recommendations
        if self.results["database_type"] == "postgresql":
            settings = self.results.get("connection_info", {}).get("settings", [])
            for setting in settings:
                if setting["name"] == "shared_buffers":
                    # Parse shared_buffers value (could be in MB, GB, etc.)
                    value = setting["setting"]
                    if value.endswith("MB") and int(value[:-2]) < 256:
                        recommendations.append({
                            "category": "configuration",
                            "priority": "medium",
                            "issue": "shared_buffers may be too low",
                            "recommendation": "Consider increasing shared_buffers to 25% of available RAM",
                            "details": f"Current value: {value}"
                        })
        
        self.results["recommendations"] = sorted(
            recommendations, 
            key=lambda x: {"high": 3, "medium": 2, "low": 1}[x["priority"]], 
            reverse=True
        )
    
    def save_report(self, output_file: str) -> None:
        """Save audit report to file."""
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w') as f:
            json.dump(self.results, f, indent=2, default=str)
        
        logger.info(f"Audit report saved to {output_path}")
    
    def print_summary(self) -> None:
        """Print audit summary to console."""
        print(f"\n{'='*60}")
        print(f"DATABASE PERFORMANCE AUDIT SUMMARY")
        print(f"{'='*60}")
        print(f"Database Type: {self.results['database_type']}")
        print(f"Audit Time: {self.results['timestamp']}")
        
        # Connection info
        pool_info = self.results.get("connection_info", {})
        print(f"\nConnection Pool Status:")
        print(f"  Pool Size: {pool_info.get('pool_size', 'N/A')}")
        print(f"  Checked Out: {pool_info.get('checked_out', 'N/A')}")
        print(f"  Overflow: {pool_info.get('overflow', 'N/A')}")
        
        # Performance metrics
        perf_metrics = self.results.get("performance_metrics", {})
        print(f"\nPerformance Metrics:")
        print(f"  Connection Time: {perf_metrics.get('connection_time_ms', 'N/A')} ms")
        if "database_size" in perf_metrics:
            print(f"  Database Size: {perf_metrics['database_size']}")
        
        # Recommendations
        recommendations = self.results.get("recommendations", [])
        if recommendations:
            print(f"\nTop Recommendations:")
            for i, rec in enumerate(recommendations[:3], 1):
                print(f"  {i}. [{rec['priority'].upper()}] {rec['issue']}")
                print(f"     → {rec['recommendation']}")
        else:
            print(f"\nNo specific recommendations - database appears to be performing well!")
        
        print(f"\n{'='*60}")


async def main():
    """Main entry point for database audit."""
    parser = argparse.ArgumentParser(description="Database Performance Audit")
    parser.add_argument("--output", "-o", default="reports/db_performance_audit.json",
                       help="Output file for audit report")
    parser.add_argument("--summary", action="store_true",
                       help="Print summary to console")
    
    args = parser.parse_args()
    
    try:
        auditor = DatabasePerformanceAuditor()
        results = await auditor.run_full_audit()
        
        # Save report
        auditor.save_report(args.output)
        
        # Print summary if requested
        if args.summary:
            auditor.print_summary()
        
        # Return appropriate exit code
        error_count = len([r for r in results.get("recommendations", []) 
                          if r["priority"] == "high"])
        return 1 if error_count > 0 else 0
        
    except Exception as e:
        logger.error(f"Audit failed: {e}")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)