"""
Resilience and fault tolerance mechanisms for Flavor.

This module provides retry logic, circuit breakers, and recovery mechanisms.
"""

import os
import time
import psutil
import threading
import functools
import logging
from pathlib import Path
from typing import Any, Callable, Optional, TypeVar, Generic
from dataclasses import dataclass
from enum import Enum
from contextlib import contextmanager

logger = logging.getLogger(__name__)

T = TypeVar('T')


class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"  # Normal operation
    OPEN = "open"      # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing recovery


@dataclass
class RetryConfig:
    """Configuration for retry mechanisms."""
    max_attempts: int = 3
    base_delay: float = 1.0
    max_delay: float = 60.0
    exponential_base: float = 2.0
    jitter: bool = True
    retryable_exceptions: tuple = (IOError, OSError, ConnectionError)


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker."""
    failure_threshold: int = 5
    recovery_timeout: float = 60.0
    expected_exception: type = Exception
    success_threshold: int = 2


@dataclass
class ResourceLimits:
    """Resource limits for operations."""
    max_memory_mb: int = 1024
    max_disk_mb: int = 10240
    max_open_files: int = 1024
    max_threads: int = 100
    max_cpu_percent: float = 80.0


class RetryError(Exception):
    """Raised when all retry attempts fail."""
    def __init__(self, message: str, attempts: int, last_error: Exception):
        super().__init__(message)
        self.attempts = attempts
        self.last_error = last_error


class ResourceExhaustedError(Exception):
    """Raised when resources are exhausted."""
    pass


class LockError(Exception):
    """Raised when unable to acquire lock."""
    pass


class ExponentialBackoffRetrier:
    """Implements exponential backoff retry logic."""
    
    def __init__(self, config: Optional[RetryConfig] = None):
        self.config = config or RetryConfig()
    
    def retry(self, func: Callable[[], T], *args, **kwargs) -> T:
        """
        Retry a function with exponential backoff.
        
        Args:
            func: Function to retry
            *args: Positional arguments for func
            **kwargs: Keyword arguments for func
            
        Returns:
            Result of successful function call
            
        Raises:
            RetryError: When all attempts fail
        """
        last_error = None
        delay = self.config.base_delay
        
        for attempt in range(1, self.config.max_attempts + 1):
            try:
                logger.debug(f"Attempt {attempt}/{self.config.max_attempts}")
                return func(*args, **kwargs)
            
            except self.config.retryable_exceptions as e:
                last_error = e
                logger.warning(f"Attempt {attempt} failed: {e}")
                
                if attempt == self.config.max_attempts:
                    break
                
                # Calculate next delay with exponential backoff
                if self.config.jitter:
                    import random
                    actual_delay = delay * (0.5 + random.random())
                else:
                    actual_delay = delay
                
                actual_delay = min(actual_delay, self.config.max_delay)
                logger.debug(f"Retrying in {actual_delay:.2f} seconds")
                time.sleep(actual_delay)
                
                delay *= self.config.exponential_base
        
        raise RetryError(
            f"All {self.config.max_attempts} attempts failed",
            self.config.max_attempts,
            last_error
        )
    
    def __call__(self, func: Callable) -> Callable:
        """Decorator for retry logic."""
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            return self.retry(func, *args, **kwargs)
        return wrapper


class CircuitBreaker:
    """Implements circuit breaker pattern."""
    
    def __init__(self, config: Optional[CircuitBreakerConfig] = None):
        self.config = config or CircuitBreakerConfig()
        self.state = CircuitState.CLOSED
        self.failures = 0
        self.successes = 0
        self.last_failure_time = None
        self._lock = threading.Lock()
    
    def call(self, func: Callable[[], T], *args, **kwargs) -> T:
        """
        Call function through circuit breaker.
        
        Args:
            func: Function to call
            *args: Positional arguments
            **kwargs: Keyword arguments
            
        Returns:
            Result of function call
            
        Raises:
            Exception: When circuit is open or function fails
        """
        with self._lock:
            if self.state == CircuitState.OPEN:
                if self._should_attempt_reset():
                    self.state = CircuitState.HALF_OPEN
                    logger.info("Circuit breaker entering HALF_OPEN state")
                else:
                    raise Exception("Circuit breaker is OPEN")
        
        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        
        except self.config.expected_exception as e:
            self._on_failure()
            raise
    
    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt reset."""
        if self.last_failure_time is None:
            return False
        
        time_since_failure = time.time() - self.last_failure_time
        return time_since_failure >= self.config.recovery_timeout
    
    def _on_success(self):
        """Handle successful call."""
        with self._lock:
            self.failures = 0
            
            if self.state == CircuitState.HALF_OPEN:
                self.successes += 1
                if self.successes >= self.config.success_threshold:
                    self.state = CircuitState.CLOSED
                    self.successes = 0
                    logger.info("Circuit breaker entering CLOSED state")
    
    def _on_failure(self):
        """Handle failed call."""
        with self._lock:
            self.failures += 1
            self.last_failure_time = time.time()
            
            if self.state == CircuitState.HALF_OPEN:
                self.state = CircuitState.OPEN
                logger.warning("Circuit breaker entering OPEN state (test failed)")
            
            elif self.failures >= self.config.failure_threshold:
                self.state = CircuitState.OPEN
                logger.warning(f"Circuit breaker entering OPEN state ({self.failures} failures)")
    
    def reset(self):
        """Manually reset circuit breaker."""
        with self._lock:
            self.state = CircuitState.CLOSED
            self.failures = 0
            self.successes = 0
            self.last_failure_time = None
            logger.info("Circuit breaker manually reset")


class ResourceMonitor:
    """Monitors system resources and enforces limits."""
    
    def __init__(self, limits: Optional[ResourceLimits] = None):
        self.limits = limits or ResourceLimits()
    
    def check_resources(self) -> dict[str, bool]:
        """
        Check if resources are within limits.
        
        Returns:
            Dictionary of resource checks and their status
        """
        checks = {}
        
        # Check memory
        memory = psutil.virtual_memory()
        available_mb = memory.available / (1024 * 1024)
        checks['memory'] = available_mb >= self.limits.max_memory_mb
        
        # Check disk space
        disk = psutil.disk_usage('/')
        available_disk_mb = disk.free / (1024 * 1024)
        checks['disk'] = available_disk_mb >= self.limits.max_disk_mb
        
        # Check CPU
        cpu_percent = psutil.cpu_percent(interval=0.1)
        checks['cpu'] = cpu_percent <= self.limits.max_cpu_percent
        
        # Check open files (Unix only)
        try:
            import resource
            soft, hard = resource.getrlimit(resource.RLIMIT_NOFILE)
            current_fds = len(os.listdir('/proc/self/fd')) if os.path.exists('/proc/self/fd') else 0
            checks['files'] = current_fds < self.limits.max_open_files
        except:
            checks['files'] = True  # Can't check on this platform
        
        # Check threads
        checks['threads'] = threading.active_count() < self.limits.max_threads
        
        return checks
    
    def ensure_resources(self):
        """
        Ensure resources are available.
        
        Raises:
            ResourceExhaustedError: When resources are exhausted
        """
        checks = self.check_resources()
        failed = [name for name, ok in checks.items() if not ok]
        
        if failed:
            raise ResourceExhaustedError(f"Resources exhausted: {', '.join(failed)}")
    
    @contextmanager
    def monitor(self):
        """Context manager for resource monitoring."""
        self.ensure_resources()
        yield
        # Could add post-operation checks here


class LockManager:
    """Manages file-based locks for concurrent operations."""
    
    def __init__(self, lock_dir: Optional[Path] = None):
        self.lock_dir = lock_dir or Path("/tmp/flavor/locks")
        self.lock_dir.mkdir(parents=True, exist_ok=True)
        self.held_locks = set()
    
    @contextmanager
    def lock(self, name: str, timeout: float = 30.0):
        """
        Acquire a named lock.
        
        Args:
            name: Lock name
            timeout: Maximum time to wait for lock
            
        Yields:
            Lock file path
            
        Raises:
            LockError: When unable to acquire lock
        """
        lock_file = self.lock_dir / f"{name}.lock"
        start_time = time.time()
        
        while True:
            try:
                # Try to acquire lock
                if self._try_acquire(lock_file):
                    self.held_locks.add(lock_file)
                    try:
                        yield lock_file
                    finally:
                        self._release(lock_file)
                        self.held_locks.discard(lock_file)
                    break
                
                # Check timeout
                if time.time() - start_time > timeout:
                    raise LockError(f"Timeout acquiring lock: {name}")
                
                # Check for stale lock
                if self._is_stale(lock_file):
                    logger.warning(f"Removing stale lock: {lock_file}")
                    lock_file.unlink()
                    continue
                
                # Wait before retry
                time.sleep(0.1)
                
            except Exception as e:
                if not isinstance(e, LockError):
                    logger.error(f"Error acquiring lock: {e}")
                raise
    
    def _try_acquire(self, lock_file: Path) -> bool:
        """Try to acquire a lock file."""
        try:
            # Atomic creation with O_EXCL
            fd = os.open(lock_file, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.write(fd, str(os.getpid()).encode())
            os.close(fd)
            return True
        except FileExistsError:
            return False
    
    def _release(self, lock_file: Path):
        """Release a lock file."""
        try:
            lock_file.unlink()
        except FileNotFoundError:
            pass  # Already released
    
    def _is_stale(self, lock_file: Path) -> bool:
        """Check if a lock is stale (process no longer exists)."""
        try:
            with open(lock_file, 'r') as f:
                pid = int(f.read().strip())
            
            # Check if process exists
            if psutil.pid_exists(pid):
                try:
                    proc = psutil.Process(pid)
                    # Additional check: is it a flavor process?
                    return 'flavor' not in proc.name().lower()
                except:
                    return False
            return True
            
        except:
            return True  # Can't read lock file, assume stale
    
    def cleanup_all(self):
        """Clean up all held locks (for emergency cleanup)."""
        for lock_file in self.held_locks.copy():
            self._release(lock_file)
            self.held_locks.discard(lock_file)


class HealthChecker:
    """Provides health check functionality."""
    
    def __init__(self):
        self.checks = {}
        self.last_check = {}
    
    def register_check(self, name: str, check_func: Callable[[], bool]):
        """Register a health check."""
        self.checks[name] = check_func
    
    def check_health(self) -> dict[str, bool]:
        """
        Run all health checks.
        
        Returns:
            Dictionary of check results
        """
        results = {}
        
        for name, check_func in self.checks.items():
            try:
                results[name] = check_func()
                self.last_check[name] = time.time()
            except Exception as e:
                logger.error(f"Health check {name} failed: {e}")
                results[name] = False
        
        return results
    
    def is_healthy(self) -> bool:
        """Check if all systems are healthy."""
        results = self.check_health()
        return all(results.values())
    
    def get_status(self) -> dict:
        """Get detailed health status."""
        results = self.check_health()
        return {
            'healthy': all(results.values()),
            'checks': results,
            'timestamp': time.time()
        }


class CheckpointManager:
    """Manages checkpoints for resumable operations."""
    
    def __init__(self, checkpoint_dir: Optional[Path] = None):
        self.checkpoint_dir = checkpoint_dir or Path("/tmp/flavor/checkpoints")
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)
    
    def save_checkpoint(self, operation_id: str, state: dict):
        """Save a checkpoint."""
        import json
        checkpoint_file = self.checkpoint_dir / f"{operation_id}.checkpoint"
        
        with open(checkpoint_file, 'w') as f:
            json.dump({
                'state': state,
                'timestamp': time.time(),
                'pid': os.getpid()
            }, f)
    
    def load_checkpoint(self, operation_id: str) -> Optional[dict]:
        """Load a checkpoint if it exists."""
        import json
        checkpoint_file = self.checkpoint_dir / f"{operation_id}.checkpoint"
        
        if not checkpoint_file.exists():
            return None
        
        try:
            with open(checkpoint_file, 'r') as f:
                data = json.load(f)
            
            # Check if checkpoint is still valid
            age = time.time() - data['timestamp']
            if age > 3600:  # 1 hour
                logger.warning(f"Checkpoint {operation_id} is too old ({age:.0f}s)")
                return None
            
            return data['state']
            
        except Exception as e:
            logger.error(f"Failed to load checkpoint: {e}")
            return None
    
    def remove_checkpoint(self, operation_id: str):
        """Remove a checkpoint."""
        checkpoint_file = self.checkpoint_dir / f"{operation_id}.checkpoint"
        try:
            checkpoint_file.unlink()
        except FileNotFoundError:
            pass
    
    @contextmanager
    def checkpointed_operation(self, operation_id: str):
        """Context manager for checkpointed operations."""
        state = self.load_checkpoint(operation_id)
        
        class CheckpointContext:
            def __init__(self, state):
                self.state = state or {}
                self.operation_id = operation_id
            
            def save(self):
                self.save_checkpoint(self.operation_id, self.state)
        
        context = CheckpointContext(state)
        
        try:
            yield context
            # Success - remove checkpoint
            self.remove_checkpoint(operation_id)
        except Exception:
            # Failure - checkpoint is preserved
            context.save()
            raise


# Global instances for convenience
default_retrier = ExponentialBackoffRetrier()
default_resource_monitor = ResourceMonitor()
default_lock_manager = LockManager()
default_health_checker = HealthChecker()
default_checkpoint_manager = CheckpointManager()


# Decorator for retry
def with_retry(max_attempts: int = 3, delay: float = 1.0):
    """Decorator to add retry logic to a function."""
    config = RetryConfig(max_attempts=max_attempts, base_delay=delay)
    retrier = ExponentialBackoffRetrier(config)
    return retrier


# Decorator for circuit breaker
def with_circuit_breaker(failure_threshold: int = 5):
    """Decorator to add circuit breaker to a function."""
    config = CircuitBreakerConfig(failure_threshold=failure_threshold)
    breaker = CircuitBreaker(config)
    
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            return breaker.call(func, *args, **kwargs)
        return wrapper
    
    return decorator