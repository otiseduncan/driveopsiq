#!/usr/bin/env python3
"""
Git-based caching system for audit results
Tracks file changes using git hashes and caches analysis results
"""

import hashlib
import json
import logging
import os
import sqlite3
import subprocess
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple, Any
import asyncio

logger = logging.getLogger(__name__)


@dataclass
class CacheEntry:
    """Represents a cached analysis result."""
    file_path: str
    git_hash: str
    file_hash: str
    analysis_result: str
    created_at: datetime
    accessed_at: datetime
    file_size: int
    analysis_duration: float


@dataclass
class CacheStats:
    """Cache performance statistics."""
    total_files: int
    cache_hits: int
    cache_misses: int
    cache_invalidations: int
    total_cache_size_mb: float
    oldest_entry: Optional[datetime]
    newest_entry: Optional[datetime]
    
    @property
    def hit_rate(self) -> float:
        """Calculate cache hit rate as percentage."""
        total_requests = self.cache_hits + self.cache_misses
        return (self.cache_hits / total_requests * 100) if total_requests > 0 else 0.0


class GitHashProvider:
    """Provides git hash information for files."""
    
    def __init__(self):
        self._is_git_repo = self._check_git_repo()
    
    def _check_git_repo(self) -> bool:
        """Check if current directory is a git repository."""
        try:
            subprocess.run(
                ['git', 'rev-parse', '--git-dir'],
                capture_output=True,
                check=True
            )
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False
    
    def get_file_git_hash(self, file_path: Path) -> Optional[str]:
        """Get the git hash for a specific file."""
        if not self._is_git_repo:
            return None
        
        try:
            # Get the git hash of the file content
            result = subprocess.run(
                ['git', 'hash-object', str(file_path)],
                capture_output=True,
                text=True,
                check=True
            )
            return result.stdout.strip()
        except (subprocess.CalledProcessError, FileNotFoundError):
            logger.debug(f"Could not get git hash for {file_path}")
            return None
    
    def get_file_last_commit_hash(self, file_path: Path) -> Optional[str]:
        """Get the hash of the last commit that modified this file."""
        if not self._is_git_repo:
            return None
        
        try:
            result = subprocess.run(
                ['git', 'log', '-n', '1', '--pretty=format:%H', '--', str(file_path)],
                capture_output=True,
                text=True,
                check=True
            )
            commit_hash = result.stdout.strip()
            return commit_hash if commit_hash else None
        except (subprocess.CalledProcessError, FileNotFoundError):
            logger.debug(f"Could not get last commit hash for {file_path}")
            return None
    
    def get_changed_files_since_commit(self, commit_hash: str) -> Set[Path]:
        """Get files changed since a specific commit."""
        if not self._is_git_repo:
            return set()
        
        try:
            result = subprocess.run(
                ['git', 'diff', '--name-only', commit_hash, 'HEAD'],
                capture_output=True,
                text=True,
                check=True
            )
            changed_files = set()
            for line in result.stdout.strip().split('\n'):
                if line:
                    changed_files.add(Path(line))
            return changed_files
        except (subprocess.CalledProcessError, FileNotFoundError):
            logger.warning(f"Could not get changed files since {commit_hash}")
            return set()
    
    def get_current_branch(self) -> Optional[str]:
        """Get the current git branch name."""
        if not self._is_git_repo:
            return None
        
        try:
            result = subprocess.run(
                ['git', 'rev-parse', '--abbrev-ref', 'HEAD'],
                capture_output=True,
                text=True,
                check=True
            )
            return result.stdout.strip()
        except (subprocess.CalledProcessError, FileNotFoundError):
            return None


class AnalysisCache:
    """SQLite-based cache for analysis results with git integration."""
    
    def __init__(self, cache_dir: Path = None, max_age_hours: int = 24):
        self.cache_dir = cache_dir or Path(".audit_cache")
        self.cache_dir.mkdir(exist_ok=True)
        self.db_path = self.cache_dir / "analysis_cache.db"
        self.max_age = timedelta(hours=max_age_hours)
        self.git_provider = GitHashProvider()
        
        self._init_database()
    
    def _init_database(self) -> None:
        """Initialize SQLite database schema."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS cache_entries (
                    file_path TEXT PRIMARY KEY,
                    git_hash TEXT,
                    file_hash TEXT,
                    analysis_result TEXT,
                    created_at TEXT,
                    accessed_at TEXT,
                    file_size INTEGER,
                    analysis_duration REAL
                )
            ''')
            
            conn.execute('''
                CREATE INDEX IF NOT EXISTS idx_git_hash ON cache_entries(git_hash)
            ''')
            
            conn.execute('''
                CREATE INDEX IF NOT EXISTS idx_accessed_at ON cache_entries(accessed_at)
            ''')
            
            # Add metadata table for cache statistics
            conn.execute('''
                CREATE TABLE IF NOT EXISTS cache_metadata (
                    key TEXT PRIMARY KEY,
                    value TEXT,
                    updated_at TEXT
                )
            ''')
    
    def _calculate_file_hash(self, file_path: Path) -> str:
        """Calculate SHA-256 hash of file content."""
        hasher = hashlib.sha256()
        try:
            with open(file_path, 'rb') as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hasher.update(chunk)
            return hasher.hexdigest()
        except (IOError, OSError) as e:
            logger.warning(f"Could not hash file {file_path}: {e}")
            return ""
    
    def _is_cache_valid(self, entry: CacheEntry, current_git_hash: Optional[str], 
                       current_file_hash: str) -> bool:
        """Check if a cache entry is still valid."""
        # Check age
        if datetime.now() - entry.created_at > self.max_age:
            logger.debug(f"Cache entry expired for {entry.file_path}")
            return False
        
        # Check git hash (if available)
        if current_git_hash and entry.git_hash:
            if entry.git_hash != current_git_hash:
                logger.debug(f"Git hash changed for {entry.file_path}")
                return False
        
        # Check file content hash
        if entry.file_hash != current_file_hash:
            logger.debug(f"File content changed for {entry.file_path}")
            return False
        
        return True
    
    async def get_cached_analysis(self, file_path: Path) -> Optional[str]:
        """Get cached analysis result if valid."""
        try:
            # Calculate current hashes
            current_file_hash = self._calculate_file_hash(file_path)
            current_git_hash = self.git_provider.get_file_git_hash(file_path)
            
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                cursor.execute(
                    'SELECT * FROM cache_entries WHERE file_path = ?',
                    (str(file_path),)
                )
                row = cursor.fetchone()
                
                if not row:
                    logger.debug(f"No cache entry found for {file_path}")
                    return None
                
                # Convert row to CacheEntry
                entry = CacheEntry(
                    file_path=row['file_path'],
                    git_hash=row['git_hash'],
                    file_hash=row['file_hash'],
                    analysis_result=row['analysis_result'],
                    created_at=datetime.fromisoformat(row['created_at']),
                    accessed_at=datetime.fromisoformat(row['accessed_at']),
                    file_size=row['file_size'],
                    analysis_duration=row['analysis_duration']
                )
                
                # Validate cache entry
                if self._is_cache_valid(entry, current_git_hash, current_file_hash):
                    # Update access time
                    cursor.execute(
                        'UPDATE cache_entries SET accessed_at = ? WHERE file_path = ?',
                        (datetime.now().isoformat(), str(file_path))
                    )
                    conn.commit()
                    
                    logger.debug(f"Cache hit for {file_path}")
                    return entry.analysis_result
                else:
                    # Remove invalid entry
                    await self.invalidate_file(file_path)
                    return None
                    
        except Exception as e:
            logger.error(f"Error retrieving cache for {file_path}: {e}")
            return None
    
    async def store_analysis(self, file_path: Path, analysis_result: str, 
                           analysis_duration: float) -> None:
        """Store analysis result in cache."""
        try:
            current_file_hash = self._calculate_file_hash(file_path)
            current_git_hash = self.git_provider.get_file_git_hash(file_path)
            file_size = file_path.stat().st_size if file_path.exists() else 0
            
            now = datetime.now()
            
            with sqlite3.connect(self.db_path) as conn:
                conn.execute('''
                    INSERT OR REPLACE INTO cache_entries 
                    (file_path, git_hash, file_hash, analysis_result, 
                     created_at, accessed_at, file_size, analysis_duration)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    str(file_path),
                    current_git_hash,
                    current_file_hash,
                    analysis_result,
                    now.isoformat(),
                    now.isoformat(),
                    file_size,
                    analysis_duration
                ))
                
                logger.debug(f"Cached analysis for {file_path}")
                
        except Exception as e:
            logger.error(f"Error storing cache for {file_path}: {e}")
    
    async def invalidate_file(self, file_path: Path) -> None:
        """Remove a specific file from cache."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('DELETE FROM cache_entries WHERE file_path = ?', (str(file_path),))
                if cursor.rowcount > 0:
                    logger.debug(f"Invalidated cache for {file_path}")
        except Exception as e:
            logger.error(f"Error invalidating cache for {file_path}: {e}")
    
    async def invalidate_by_pattern(self, pattern: str) -> int:
        """Invalidate cache entries matching a pattern."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('DELETE FROM cache_entries WHERE file_path LIKE ?', (pattern,))
                count = cursor.rowcount
                logger.info(f"Invalidated {count} cache entries matching pattern: {pattern}")
                return count
        except Exception as e:
            logger.error(f"Error invalidating cache by pattern {pattern}: {e}")
            return 0
    
    async def cleanup_expired(self) -> int:
        """Remove expired cache entries."""
        try:
            cutoff_time = datetime.now() - self.max_age
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    'DELETE FROM cache_entries WHERE created_at < ?',
                    (cutoff_time.isoformat(),)
                )
                count = cursor.rowcount
                
                if count > 0:
                    logger.info(f"Cleaned up {count} expired cache entries")
                
                return count
        except Exception as e:
            logger.error(f"Error cleaning up expired cache: {e}")
            return 0
    
    async def get_stats(self) -> CacheStats:
        """Get cache performance statistics."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                # Basic counts
                cursor.execute('SELECT COUNT(*) as count FROM cache_entries')
                total_files = cursor.fetchone()['count']
                
                # File sizes for total cache size
                cursor.execute('SELECT SUM(file_size) as total_size FROM cache_entries')
                total_size_bytes = cursor.fetchone()['total_size'] or 0
                total_size_mb = total_size_bytes / (1024 * 1024)
                
                # Date ranges
                cursor.execute('''
                    SELECT MIN(created_at) as oldest, MAX(created_at) as newest 
                    FROM cache_entries
                ''')
                date_info = cursor.fetchone()
                
                oldest_entry = None
                newest_entry = None
                if date_info['oldest']:
                    oldest_entry = datetime.fromisoformat(date_info['oldest'])
                if date_info['newest']:
                    newest_entry = datetime.fromisoformat(date_info['newest'])
                
                return CacheStats(
                    total_files=total_files,
                    cache_hits=0,  # These would be tracked separately in production
                    cache_misses=0,
                    cache_invalidations=0,
                    total_cache_size_mb=total_size_mb,
                    oldest_entry=oldest_entry,
                    newest_entry=newest_entry
                )
        except Exception as e:
            logger.error(f"Error getting cache stats: {e}")
            return CacheStats(0, 0, 0, 0, 0.0, None, None)
    
    async def clear_cache(self) -> int:
        """Clear all cache entries."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('DELETE FROM cache_entries')
                count = cursor.rowcount
                logger.info(f"Cleared {count} cache entries")
                return count
        except Exception as e:
            logger.error(f"Error clearing cache: {e}")
            return 0
    
    def export_cache_data(self) -> Dict[str, Any]:
        """Export cache data for debugging/analysis."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute('SELECT * FROM cache_entries ORDER BY created_at DESC')
                
                entries = []
                for row in cursor.fetchall():
                    entries.append(dict(row))
                
                return {
                    "entries": entries,
                    "export_time": datetime.now().isoformat(),
                    "total_entries": len(entries)
                }
        except Exception as e:
            logger.error(f"Error exporting cache data: {e}")
            return {"entries": [], "error": str(e)}


class CachedLLMAnalyzer:
    """LLM Analyzer with caching support."""
    
    def __init__(self, base_analyzer, cache: AnalysisCache):
        self.base_analyzer = base_analyzer
        self.cache = cache
        self.cache_hits = 0
        self.cache_misses = 0
    
    async def analyze_file(self, file_path: Path) -> Any:
        """Analyze file with caching support."""
        # Try to get cached result first
        start_time = asyncio.get_event_loop().time()
        cached_result = await self.cache.get_cached_analysis(file_path)
        
        if cached_result:
            self.cache_hits += 1
            logger.debug(f"Using cached analysis for {file_path}")
            
            # Return cached result in the same format as base analyzer
            from improved_audit import FileAnalysis
            return FileAnalysis(
                path=str(file_path),
                llm_analysis=cached_result,
                size_bytes=file_path.stat().st_size if file_path.exists() else 0
            )
        
        # Cache miss - run actual analysis
        self.cache_misses += 1
        logger.debug(f"Cache miss for {file_path}, running analysis")
        
        analysis_result = await self.base_analyzer.analyze_file(file_path)
        analysis_duration = asyncio.get_event_loop().time() - start_time
        
        # Store in cache if analysis was successful
        if analysis_result and not analysis_result.error:
            await self.cache.store_analysis(
                file_path, 
                analysis_result.llm_analysis,
                analysis_duration
            )
        
        return analysis_result
    
    @property
    def hit_rate(self) -> float:
        """Get cache hit rate percentage."""
        total = self.cache_hits + self.cache_misses
        return (self.cache_hits / total * 100) if total > 0 else 0.0


# CLI utility for cache management
async def main():
    """Command line interface for cache management."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Audit cache management")
    parser.add_argument('--stats', action='store_true', help='Show cache statistics')
    parser.add_argument('--clear', action='store_true', help='Clear all cache')
    parser.add_argument('--cleanup', action='store_true', help='Clean up expired entries')
    parser.add_argument('--invalidate', type=str, help='Invalidate files matching pattern')
    parser.add_argument('--export', type=str, help='Export cache data to JSON file')
    parser.add_argument('--cache-dir', type=str, help='Cache directory path')
    
    args = parser.parse_args()
    
    cache_dir = Path(args.cache_dir) if args.cache_dir else None
    cache = AnalysisCache(cache_dir)
    
    if args.stats:
        stats = await cache.get_stats()
        print("📊 Cache Statistics:")
        print(f"  Total files: {stats.total_files}")
        print(f"  Cache size: {stats.total_cache_size_mb:.2f} MB")
        print(f"  Hit rate: {stats.hit_rate:.1f}%")
        if stats.oldest_entry:
            print(f"  Oldest entry: {stats.oldest_entry}")
        if stats.newest_entry:
            print(f"  Newest entry: {stats.newest_entry}")
    
    if args.clear:
        count = await cache.clear_cache()
        print(f"🗑️  Cleared {count} cache entries")
    
    if args.cleanup:
        count = await cache.cleanup_expired()
        print(f"🧹 Cleaned up {count} expired entries")
    
    if args.invalidate:
        count = await cache.invalidate_by_pattern(args.invalidate)
        print(f"❌ Invalidated {count} entries matching '{args.invalidate}'")
    
    if args.export:
        data = cache.export_cache_data()
        with open(args.export, 'w') as f:
            json.dump(data, f, indent=2)
        print(f"💾 Exported cache data to {args.export}")


if __name__ == "__main__":
    asyncio.run(main())