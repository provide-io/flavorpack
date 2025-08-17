# 🛡️ Flavor Resilience Implementation Plan

## Priority 1: Immediate Stability Fixes (This Week)

### 1. Fix the 29 Failing Tests
These are your stability baseline - they must work reliably.

```bash
# Run to see current failures
workenv/flavor_darwin_arm64/bin/pytest tests/ -x --tb=short | grep FAILED

# Key failures to fix first:
- test_slot_lifecycle_* (5 tests) - Core extraction logic
- test_exit_code_propagation - Process management
- test_execute_bundle - Main execution path
- test_orchestrator_* - Build process
```

**Action**: Fix these tests FIRST before adding resilience features.

### 2. Add Resource Checks Before Operations
Prevent failures by checking resources upfront.

```python
# In src/flavor/psp/format_2025/launcher.py
from flavor.resilience import ResourceMonitor, ResourceExhaustedError

class PSPFLauncher:
    def __init__(self):
        self.resource_monitor = ResourceMonitor()
    
    def execute_bundle(self, bundle_path: Path, args: list[str]):
        # Check resources BEFORE starting
        try:
            self.resource_monitor.ensure_resources()
        except ResourceExhaustedError as e:
            logger.error(f"Insufficient resources: {e}")
            return ExecutionResult(success=False, error=str(e))
        
        # Continue with execution...
```

### 3. Add Extraction Locking
Prevent concurrent extractions that corrupt each other.

```python
# In src/flavor/psp/format_2025/reader.py
from flavor.resilience import LockManager

class PSPFReader:
    def extract_all(self, dest_dir: Path):
        lock_manager = LockManager()
        
        # Use package hash as lock name
        package_hash = hashlib.sha256(self.bundle_path.read_bytes()).hexdigest()[:8]
        
        with lock_manager.lock(f"extract_{package_hash}"):
            # Mark extraction as incomplete
            incomplete_marker = dest_dir / ".extraction.incomplete"
            incomplete_marker.touch()
            
            try:
                # Do extraction
                for slot in self.get_slots():
                    self.extract_slot(slot, dest_dir)
                
                # Mark as complete
                incomplete_marker.unlink()
                (dest_dir / ".extraction.complete").touch()
                
            except Exception as e:
                logger.error(f"Extraction failed: {e}")
                # Incomplete marker remains
                raise
```

### 4. Add Retry Logic to Network/IO Operations
Make transient failures recoverable.

```python
# In src/flavor/packaging/python_packager.py
from flavor.resilience import with_retry

class PythonPackager:
    @with_retry(max_attempts=3, delay=1.0)
    def download_dependencies(self):
        """Download with automatic retry."""
        # Network operations here
        pass
    
    @with_retry(max_attempts=3, delay=0.5)
    def write_large_file(self, path: Path, data: bytes):
        """Write with retry for disk issues."""
        path.write_bytes(data)
```

## Priority 2: Critical Resilience Features (Next 3 Days)

### 5. Implement Checkpointing for Long Operations
Allow resumption after interruption.

```python
# In src/flavor/packaging/orchestrator.py
from flavor.resilience import CheckpointManager

class PackagingOrchestrator:
    def build_package(self, config: dict) -> Path:
        checkpoint_mgr = CheckpointManager()
        
        with checkpoint_mgr.checkpointed_operation("build") as checkpoint:
            # Resume from checkpoint if available
            completed_steps = checkpoint.state.get("completed", [])
            
            steps = ["download", "build", "package", "sign"]
            for step in steps:
                if step in completed_steps:
                    logger.info(f"Skipping completed step: {step}")
                    continue
                
                try:
                    self._execute_step(step)
                    completed_steps.append(step)
                    checkpoint.state["completed"] = completed_steps
                    checkpoint.save()  # Save progress
                except KeyboardInterrupt:
                    logger.info("Interrupted - checkpoint saved")
                    raise
```

### 6. Add Circuit Breaker for External Services
Prevent cascade failures.

```python
# In src/flavor/api.py
from flavor.resilience import CircuitBreaker, CircuitBreakerConfig

class FlavorAPI:
    def __init__(self):
        self.pypi_breaker = CircuitBreaker(
            CircuitBreakerConfig(
                failure_threshold=3,
                recovery_timeout=30.0
            )
        )
    
    def fetch_from_pypi(self, package: str):
        try:
            return self.pypi_breaker.call(self._fetch_pypi, package)
        except Exception as e:
            # Fallback to local cache or mirror
            return self._fetch_from_cache(package)
```

### 7. Add Health Checks
Monitor system health proactively.

```python
# In src/flavor/cli.py
from flavor.resilience import HealthChecker

@cli.command()
def health():
    """Check system health."""
    checker = HealthChecker()
    
    # Register checks
    checker.register_check("disk_space", check_disk_space)
    checker.register_check("memory", check_memory)
    checker.register_check("helpers", check_helpers_exist)
    checker.register_check("python", check_python_version)
    
    status = checker.get_status()
    
    if status['healthy']:
        click.secho("✅ All systems healthy", fg='green')
    else:
        click.secho("❌ Health issues detected:", fg='red')
        for check, result in status['checks'].items():
            if not result:
                click.echo(f"  - {check}: FAILED")
```

## Priority 3: Enhanced Stability (Week 2)

### 8. Graceful Degradation
Continue working even when non-critical components fail.

```python
# In src/flavor/psp/format_2025/launcher.py
class PSPFLauncher:
    def execute_bundle(self, bundle_path: Path, args: list[str]):
        result = ExecutionResult()
        
        # Critical path - must work
        try:
            self._extract_and_run(bundle_path, args)
            result.success = True
        except Exception as e:
            result.success = False
            result.error = str(e)
            return result
        
        # Non-critical - continue on failure
        try:
            self._send_telemetry(result)
        except:
            logger.debug("Telemetry failed - continuing")
        
        try:
            self._update_cache_stats()
        except:
            logger.debug("Cache stats update failed - continuing")
        
        return result
```

### 9. Automatic Cleanup
Clean up resources even on failure.

```python
# In src/flavor/psp/format_2025/reader.py
import atexit
import signal

class PSPFReader:
    def __init__(self, bundle_path: Path):
        self.bundle_path = bundle_path
        self.temp_files = []
        
        # Register cleanup
        atexit.register(self._cleanup)
        signal.signal(signal.SIGTERM, self._signal_handler)
        signal.signal(signal.SIGINT, self._signal_handler)
    
    def _cleanup(self):
        """Clean up temporary files."""
        for temp_file in self.temp_files:
            try:
                if temp_file.exists():
                    if temp_file.is_dir():
                        shutil.rmtree(temp_file)
                    else:
                        temp_file.unlink()
            except:
                pass  # Best effort
    
    def _signal_handler(self, signum, frame):
        """Handle signals gracefully."""
        logger.info(f"Received signal {signum} - cleaning up")
        self._cleanup()
        sys.exit(128 + signum)
```

### 10. Monitoring & Metrics
Track failures to identify patterns.

```python
# In src/flavor/metrics.py
from dataclasses import dataclass
from datetime import datetime
import json

@dataclass
class FailureMetric:
    timestamp: datetime
    operation: str
    error_type: str
    error_message: str
    recovery_attempted: bool
    recovery_successful: bool

class MetricsCollector:
    def __init__(self):
        self.metrics_file = Path.home() / ".flavor" / "metrics.jsonl"
        self.metrics_file.parent.mkdir(exist_ok=True)
    
    def record_failure(self, metric: FailureMetric):
        with open(self.metrics_file, 'a') as f:
            f.write(json.dumps(asdict(metric)) + '\n')
    
    def get_failure_rate(self, operation: str, hours: int = 24) -> float:
        # Calculate failure rate for monitoring
        pass
```

## Testing Strategy

### 1. Chaos Testing Script
```bash
#!/bin/bash
# tests/chaos/run_chaos_tests.sh

echo "🔥 Running chaos tests..."

# Test 1: Disk full
echo "Testing disk full..."
dd if=/dev/zero of=/tmp/bigfile bs=1M count=10000 2>/dev/null
flavor package --manifest pyproject.toml --output test.psp
rm /tmp/bigfile

# Test 2: Kill during extraction
echo "Testing interruption..."
flavor package --manifest pyproject.toml --output test.psp &
PID=$!
sleep 2
kill -TERM $PID
wait $PID

# Test 3: Concurrent execution
echo "Testing concurrency..."
for i in {1..10}; do
    ./test.psp --test &
done
wait

echo "✅ Chaos tests complete"
```

### 2. Load Testing
```python
# tests/load/test_load.py
import concurrent.futures
import time

def test_concurrent_package_builds():
    """Test system under load."""
    
    def build_package(index):
        start = time.time()
        try:
            result = flavor.package(f"test_{index}.psp")
            return ("success", time.time() - start)
        except Exception as e:
            return ("failure", str(e))
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
        futures = [executor.submit(build_package, i) for i in range(100)]
        results = [f.result() for f in futures]
    
    successes = [r for r in results if r[0] == "success"]
    failures = [r for r in results if r[0] == "failure"]
    
    print(f"Success rate: {len(successes)}/100")
    print(f"Average time: {sum(r[1] for r in successes) / len(successes):.2f}s")
    
    assert len(successes) >= 95, "Too many failures under load"
```

## Monitoring Dashboard

Create a simple monitoring script:

```python
# scripts/monitor.py
#!/usr/bin/env python3
"""Real-time Flavor health monitor."""

import time
import psutil
from rich.console import Console
from rich.table import Table
from rich.live import Live

from flavor.resilience import HealthChecker, ResourceMonitor

def create_dashboard():
    console = Console()
    
    while True:
        table = Table(title="Flavor System Monitor")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green")
        table.add_column("Status", style="yellow")
        
        # Resource metrics
        mem = psutil.virtual_memory()
        table.add_row("Memory", f"{mem.percent:.1f}%", "✅" if mem.percent < 80 else "⚠️")
        
        disk = psutil.disk_usage('/')
        table.add_row("Disk", f"{disk.percent:.1f}%", "✅" if disk.percent < 90 else "⚠️")
        
        cpu = psutil.cpu_percent(interval=1)
        table.add_row("CPU", f"{cpu:.1f}%", "✅" if cpu < 80 else "⚠️")
        
        # Health checks
        checker = HealthChecker()
        health = checker.is_healthy()
        table.add_row("Health", "Healthy" if health else "Issues", "✅" if health else "❌")
        
        console.clear()
        console.print(table)
        time.sleep(5)

if __name__ == "__main__":
    create_dashboard()
```

## Implementation Order

1. **Today**: Fix failing tests (Priority 1, items 1-4)
2. **Tomorrow**: Add checkpointing and circuit breakers (Priority 2, items 5-7)
3. **Day 3**: Implement graceful degradation and cleanup (Priority 3, items 8-10)
4. **Day 4**: Run chaos tests and fix issues found
5. **Day 5**: Load testing and performance tuning

## Success Metrics

Track these metrics to measure resilience improvement:

| Metric | Current | Target | Measurement |
|--------|---------|--------|-------------|
| Test Success Rate | 82% | 95% | `pytest` results |
| Concurrent Execution | Fails | 10+ parallel | Chaos test |
| Recovery from Interrupt | No | Yes | SIGTERM test |
| Disk Full Handling | Crash | Graceful | Chaos test |
| Memory Leak | Unknown | <10MB/hour | Load test |
| Lock Contention | Corrupt | Safe | Concurrent test |
| Failure Recovery Rate | 0% | 80% | Retry success |

## Next Immediate Step

Run this command to see what's actually failing:
```bash
workenv/flavor_darwin_arm64/bin/pytest tests/ -x --tb=short 2>&1 | grep -A5 "FAILED\|ERROR"
```

Then fix those specific failures before adding new resilience features. The resilience code I've provided can be integrated once the base tests pass.