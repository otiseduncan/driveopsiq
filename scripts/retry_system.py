#!/usr/bin/env python3
"""
Robust retry system with exponential backoff, circuit breaker, and rate limiting
Handles transient failures in external service calls (Ollama, network, etc.)
"""

import asyncio
import logging
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Awaitable, Callable, Dict, Optional, Type, Union
import random
import functools

logger = logging.getLogger(__name__)


class RetryError(Exception):
    """Raised when all retry attempts are exhausted."""
    def __init__(self, message: str, last_exception: Exception, attempt_count: int):
        super().__init__(message)
        self.last_exception = last_exception
        self.attempt_count = attempt_count


class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing if service recovered


@dataclass
class RetryConfig:
    """Configuration for retry behavior."""
    max_attempts: int = 3
    base_delay: float = 1.0
    max_delay: float = 60.0
    backoff_factor: float = 2.0
    jitter: bool = True
    exceptions: tuple = (Exception,)
    
    # Circuit breaker settings
    failure_threshold: int = 5
    recovery_timeout: float = 60.0
    
    # Rate limiting
    max_calls_per_minute: Optional[int] = None
    
    def __post_init__(self):
        """Validate configuration."""
        if self.max_attempts < 1:
            raise ValueError("max_attempts must be >= 1")
        if self.base_delay < 0:
            raise ValueError("base_delay must be >= 0")
        if self.backoff_factor < 1:
            raise ValueError("backoff_factor must be >= 1")


@dataclass
class RetryStats:
    """Statistics for retry operations."""
    total_attempts: int = 0
    successful_attempts: int = 0
    failed_attempts: int = 0
    total_delay: float = 0.0
    last_attempt_time: Optional[datetime] = None
    last_success_time: Optional[datetime] = None
    last_failure_time: Optional[datetime] = None
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate percentage."""
        if self.total_attempts == 0:
            return 0.0
        return (self.successful_attempts / self.total_attempts) * 100


class CircuitBreaker:
    """Circuit breaker pattern implementation."""
    
    def __init__(self, config: RetryConfig):
        self.config = config
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.last_failure_time: Optional[datetime] = None
        self.stats = RetryStats()
    
    async def call(self, func: Callable[..., Awaitable[Any]], *args, **kwargs) -> Any:
        """Execute function through circuit breaker."""
        if self.state == CircuitState.OPEN:
            if self._should_attempt_reset():
                self.state = CircuitState.HALF_OPEN
                logger.info("Circuit breaker transitioning to HALF_OPEN")
            else:
                raise RetryError(
                    "Circuit breaker is OPEN",
                    Exception("Circuit breaker open"),
                    0
                )
        
        try:
            result = await func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise e
    
    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt reset."""
        if not self.last_failure_time:
            return True
        
        elapsed = datetime.now() - self.last_failure_time
        return elapsed.total_seconds() >= self.config.recovery_timeout
    
    def _on_success(self) -> None:
        """Handle successful operation."""
        self.failure_count = 0
        self.stats.successful_attempts += 1
        self.stats.last_success_time = datetime.now()
        
        if self.state == CircuitState.HALF_OPEN:
            self.state = CircuitState.CLOSED
            logger.info("Circuit breaker reset to CLOSED")
    
    def _on_failure(self) -> None:
        """Handle failed operation."""
        self.failure_count += 1
        self.stats.failed_attempts += 1
        self.last_failure_time = datetime.now()
        self.stats.last_failure_time = self.last_failure_time
        
        if self.failure_count >= self.config.failure_threshold:
            self.state = CircuitState.OPEN
            logger.warning(f"Circuit breaker opened after {self.failure_count} failures")


class RateLimiter:
    """Token bucket rate limiter."""
    
    def __init__(self, max_calls_per_minute: int):
        self.max_calls = max_calls_per_minute
        self.calls = []
        self.lock = asyncio.Lock()
    
    async def acquire(self) -> None:
        """Acquire permission to make a call."""
        async with self.lock:
            now = datetime.now()
            cutoff = now - timedelta(minutes=1)
            
            # Remove old calls
            self.calls = [call_time for call_time in self.calls if call_time > cutoff]
            
            if len(self.calls) >= self.max_calls:
                # Calculate wait time until oldest call expires
                oldest_call = min(self.calls)
                wait_until = oldest_call + timedelta(minutes=1)
                wait_seconds = (wait_until - now).total_seconds()
                
                if wait_seconds > 0:
                    logger.debug(f"Rate limit reached, waiting {wait_seconds:.2f}s")
                    await asyncio.sleep(wait_seconds)
            
            self.calls.append(now)


class RetryManager:
    """Advanced retry manager with circuit breaker and rate limiting."""
    
    def __init__(self, config: RetryConfig = None):
        self.config = config or RetryConfig()
        self.circuit_breaker = CircuitBreaker(self.config)
        self.rate_limiter = None
        self.stats = RetryStats()
        
        if self.config.max_calls_per_minute:
            self.rate_limiter = RateLimiter(self.config.max_calls_per_minute)
    
    async def execute_with_retry(
        self, 
        func: Callable[..., Awaitable[Any]], 
        *args, 
        **kwargs
    ) -> Any:
        """Execute function with retry, circuit breaker, and rate limiting."""
        last_exception = None
        
        for attempt in range(self.config.max_attempts):
            self.stats.total_attempts += 1
            self.stats.last_attempt_time = datetime.now()
            
            try:
                # Rate limiting
                if self.rate_limiter:
                    await self.rate_limiter.acquire()
                
                # Circuit breaker
                result = await self.circuit_breaker.call(func, *args, **kwargs)
                
                # Success
                self.stats.successful_attempts += 1
                self.stats.last_success_time = datetime.now()
                
                if attempt > 0:
                    logger.info(f"Retry succeeded on attempt {attempt + 1}")
                
                return result
                
            except self.config.exceptions as e:
                last_exception = e
                self.stats.failed_attempts += 1
                self.stats.last_failure_time = datetime.now()
                
                logger.warning(f"Attempt {attempt + 1}/{self.config.max_attempts} failed: {e}")
                
                # Don't delay after the last attempt
                if attempt < self.config.max_attempts - 1:
                    delay = self._calculate_delay(attempt)
                    self.stats.total_delay += delay
                    
                    logger.debug(f"Waiting {delay:.2f}s before retry")
                    await asyncio.sleep(delay)
            
            except Exception as e:
                # Non-retryable exception
                logger.error(f"Non-retryable exception: {e}")
                raise e
        
        # All attempts failed
        raise RetryError(
            f"All {self.config.max_attempts} retry attempts failed",
            last_exception,
            self.config.max_attempts
        )
    
    def _calculate_delay(self, attempt: int) -> float:
        """Calculate delay for exponential backoff with jitter."""
        delay = min(
            self.config.base_delay * (self.config.backoff_factor ** attempt),
            self.config.max_delay
        )
        
        if self.config.jitter:
            # Add random jitter (±25% of delay)
            jitter_range = delay * 0.25
            delay += random.uniform(-jitter_range, jitter_range)
        
        return max(0.0, delay)
    
    def get_stats(self) -> RetryStats:
        """Get retry statistics."""
        return self.stats
    
    def reset_stats(self) -> None:
        """Reset statistics."""
        self.stats = RetryStats()
        self.circuit_breaker.stats = RetryStats()


def retry(
    max_attempts: int = 3,
    base_delay: float = 1.0,
    backoff_factor: float = 2.0,
    max_delay: float = 60.0,
    jitter: bool = True,
    exceptions: tuple = (Exception,),
    failure_threshold: int = 5,
    recovery_timeout: float = 60.0,
    max_calls_per_minute: Optional[int] = None
):
    """Decorator for adding retry behavior to async functions."""
    def decorator(func: Callable[..., Awaitable[Any]]) -> Callable[..., Awaitable[Any]]:
        config = RetryConfig(
            max_attempts=max_attempts,
            base_delay=base_delay,
            backoff_factor=backoff_factor,
            max_delay=max_delay,
            jitter=jitter,
            exceptions=exceptions,
            failure_threshold=failure_threshold,
            recovery_timeout=recovery_timeout,
            max_calls_per_minute=max_calls_per_minute
        )
        
        retry_manager = RetryManager(config)
        
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            return await retry_manager.execute_with_retry(func, *args, **kwargs)
        
        # Expose retry manager for stats
        wrapper.retry_manager = retry_manager
        return wrapper
    
    return decorator


# Enhanced LLM analyzer with retry logic
class ReliableLLMAnalyzer:
    """LLM analyzer with built-in retry and resilience patterns."""
    
    def __init__(self, base_analyzer, config: RetryConfig = None):
        self.base_analyzer = base_analyzer
        self.retry_config = config or RetryConfig(
            max_attempts=3,
            base_delay=2.0,
            backoff_factor=2.0,
            max_delay=30.0,
            exceptions=(ConnectionError, TimeoutError, Exception),
            failure_threshold=5,
            recovery_timeout=300.0,  # 5 minutes
            max_calls_per_minute=30  # Rate limit for LLM API
        )
        self.retry_manager = RetryManager(self.retry_config)
    
    @retry(
        max_attempts=3,
        base_delay=2.0,
        backoff_factor=2.0,
        max_delay=30.0,
        exceptions=(ConnectionError, TimeoutError),
        max_calls_per_minute=30
    )
    async def analyze_file_with_retry(self, file_path, timeout: float = 120.0):
        """Analyze file with automatic retry on failures."""
        try:
            # Use asyncio.wait_for for timeout
            return await asyncio.wait_for(
                self.base_analyzer.analyze_file(file_path),
                timeout=timeout
            )
        except asyncio.TimeoutError:
            raise TimeoutError(f"Analysis timeout after {timeout}s for {file_path}")
        except Exception as e:
            logger.error(f"LLM analysis failed for {file_path}: {e}")
            raise
    
    async def batch_analyze_with_retry(self, file_paths: list, max_concurrent: int = 5):
        """Analyze multiple files with retry and concurrency control."""
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def analyze_single(file_path):
            async with semaphore:
                return await self.analyze_file_with_retry(file_path)
        
        # Create tasks with error handling
        tasks = []
        for file_path in file_paths:
            task = asyncio.create_task(analyze_single(file_path))
            tasks.append((file_path, task))
        
        results = []
        for file_path, task in tasks:
            try:
                result = await task
                results.append((file_path, result, None))
            except Exception as e:
                logger.error(f"Failed to analyze {file_path} after retries: {e}")
                results.append((file_path, None, str(e)))
        
        return results
    
    def get_stats(self) -> Dict[str, Any]:
        """Get retry statistics."""
        retry_stats = self.retry_manager.get_stats()
        circuit_stats = self.retry_manager.circuit_breaker.stats
        
        return {
            "retry_stats": {
                "total_attempts": retry_stats.total_attempts,
                "success_rate": retry_stats.success_rate,
                "total_delay": retry_stats.total_delay,
                "last_success": retry_stats.last_success_time.isoformat() if retry_stats.last_success_time else None
            },
            "circuit_breaker": {
                "state": self.retry_manager.circuit_breaker.state.value,
                "failure_count": self.retry_manager.circuit_breaker.failure_count,
                "success_rate": circuit_stats.success_rate
            }
        }


# Example usage and testing
async def unreliable_function(success_rate: float = 0.7):
    """Simulate an unreliable function for testing."""
    await asyncio.sleep(0.1)  # Simulate work
    
    if random.random() > success_rate:
        raise ConnectionError("Simulated network failure")
    
    return "Success!"


async def test_retry_system():
    """Test the retry system."""
    print("🧪 Testing Retry System")
    
    @retry(max_attempts=5, base_delay=0.1, backoff_factor=1.5)
    async def test_function():
        return await unreliable_function(success_rate=0.3)  # 30% success rate
    
    # Test multiple calls
    successes = 0
    failures = 0
    
    for i in range(10):
        try:
            result = await test_function()
            print(f"  ✅ Call {i+1}: {result}")
            successes += 1
        except RetryError as e:
            print(f"  ❌ Call {i+1}: Failed after {e.attempt_count} attempts")
            failures += 1
    
    print(f"\n📊 Results: {successes} successes, {failures} failures")
    
    # Show stats
    if hasattr(test_function, 'retry_manager'):
        stats = test_function.retry_manager.get_stats()
        print(f"📈 Success Rate: {stats.success_rate:.1f}%")
        print(f"⏱️  Total Delay: {stats.total_delay:.2f}s")


if __name__ == "__main__":
    asyncio.run(test_retry_system())