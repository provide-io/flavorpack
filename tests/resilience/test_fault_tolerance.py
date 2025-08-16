"""
Resilience and fault tolerance tests for Flavor.

These tests ensure the system can handle failures gracefully.
"""

import os
import tempfile
import threading
import time
import signal
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest

from flavor.psp.format_2025 import PSPFBuilder, PSPFReader, PSPFLauncher


class TestDiskFailures:
    """Test handling of disk-related failures."""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test environment."""
        self.temp_dir = Path(tempfile.mkdtemp())
        yield
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_disk_full_during_extraction(self):
        """Test behavior when disk becomes full during extraction."""
        # Create a package
        package_path = self.temp_dir / "test.pspf"
        builder = PSPFBuilder()
        builder.add_slot("large", b"A" * 1024 * 1024)  # 1MB
        builder.build(package_path)
        
        # Mock disk full error
        with patch('builtins.open') as mock_open:
            mock_open.side_effect = OSError(28, "No space left on device")
            
            reader = PSPFReader(package_path)
            with pytest.raises(OSError) as exc_info:
                reader.extract_all(self.temp_dir / "extract")
            
            # Should provide helpful error message
            assert "disk" in str(exc_info.value).lower() or "space" in str(exc_info.value).lower()
    
    def test_readonly_filesystem(self):
        """Test handling of read-only filesystem."""
        extract_dir = self.temp_dir / "readonly"
        extract_dir.mkdir()
        
        # Make directory read-only
        os.chmod(extract_dir, 0o444)
        
        package_path = self.temp_dir / "test.pspf"
        builder = PSPFBuilder()
        builder.add_slot("test", b"data")
        builder.build(package_path)
        
        reader = PSPFReader(package_path)
        with pytest.raises(PermissionError):
            reader.extract_all(extract_dir)
        
        # Restore permissions for cleanup
        os.chmod(extract_dir, 0o755)
    
    def test_corrupted_package_partial_read(self):
        """Test handling of corrupted packages."""
        # Create valid package
        package_path = self.temp_dir / "corrupt.pspf"
        builder = PSPFBuilder()
        builder.add_slot("test", b"data")
        builder.build(package_path)
        
        # Truncate package (simulate corruption)
        with open(package_path, 'rb') as f:
            data = f.read()
        
        with open(package_path, 'wb') as f:
            f.write(data[:len(data)//2])  # Write only half
        
        reader = PSPFReader(package_path)
        with pytest.raises(Exception) as exc_info:
            reader.read_index()
        
        # Should indicate corruption
        assert "corrupt" in str(exc_info.value).lower() or "invalid" in str(exc_info.value).lower()
    
    def test_extraction_cleanup_on_failure(self):
        """Ensure partial extractions are cleaned up on failure."""
        package_path = self.temp_dir / "test.pspf"
        extract_dir = self.temp_dir / "extract"
        
        builder = PSPFBuilder()
        builder.add_slot("slot1", b"data1")
        builder.add_slot("slot2", b"data2")
        builder.build(package_path)
        
        # Mock failure during second slot extraction
        original_extract = PSPFReader.extract_slot
        call_count = [0]
        
        def mock_extract(self, slot_index, dest_dir):
            call_count[0] += 1
            if call_count[0] == 2:
                raise Exception("Simulated extraction failure")
            return original_extract(self, slot_index, dest_dir)
        
        with patch.object(PSPFReader, 'extract_slot', mock_extract):
            reader = PSPFReader(package_path)
            with pytest.raises(Exception):
                reader.extract_all(extract_dir)
        
        # Check that incomplete extraction is marked
        incomplete_marker = extract_dir / ".extraction.incomplete"
        assert incomplete_marker.exists() or not extract_dir.exists()


class TestProcessFailures:
    """Test handling of process-related failures."""
    
    def test_child_process_crash(self):
        """Test handling when child process crashes."""
        launcher = PSPFLauncher()
        
        # Mock a crashing child process
        with patch('subprocess.Popen') as mock_popen:
            mock_proc = MagicMock()
            mock_proc.poll.return_value = -11  # SIGSEGV
            mock_proc.returncode = -11
            mock_popen.return_value = mock_proc
            
            result = launcher.execute("test.pspf", ["--crash"])
            assert result.returncode == -11
            assert result.crashed is True
    
    def test_signal_handling_during_extraction(self):
        """Test signal handling during long operations."""
        package_path = Path("test.pspf")
        
        # Create large package for slow extraction
        builder = PSPFBuilder()
        for i in range(100):
            builder.add_slot(f"slot_{i}", b"A" * 10000)
        builder.build(package_path)
        
        extraction_started = threading.Event()
        extraction_interrupted = False
        
        def extract_with_signal():
            nonlocal extraction_interrupted
            try:
                reader = PSPFReader(package_path)
                extraction_started.set()
                reader.extract_all("extract")
            except KeyboardInterrupt:
                extraction_interrupted = True
        
        # Start extraction in thread
        thread = threading.Thread(target=extract_with_signal)
        thread.start()
        
        # Wait for extraction to start, then send signal
        extraction_started.wait(timeout=5)
        time.sleep(0.1)
        os.kill(os.getpid(), signal.SIGINT)
        
        thread.join(timeout=5)
        assert extraction_interrupted, "Signal was not properly handled"
    
    def test_zombie_process_cleanup(self):
        """Test cleanup of zombie processes."""
        launcher = PSPFLauncher()
        
        # Track child processes
        child_pids = []
        
        with patch('subprocess.Popen') as mock_popen:
            mock_proc = MagicMock()
            mock_proc.pid = 12345
            mock_proc.poll.return_value = None  # Still running
            mock_popen.return_value = mock_proc
            child_pids.append(mock_proc.pid)
            
            # Launch process
            launcher.execute_async("test.pspf", ["--long-running"])
        
        # Simulate parent termination
        launcher.cleanup()
        
        # Verify cleanup was attempted
        mock_proc.terminate.assert_called()
    
    def test_memory_exhaustion_handling(self):
        """Test handling of memory exhaustion."""
        with patch('psutil.virtual_memory') as mock_memory:
            # Simulate low memory
            mock_memory.return_value.available = 1024 * 1024  # 1MB available
            
            launcher = PSPFLauncher()
            
            # Should detect low memory and refuse to start
            with pytest.raises(MemoryError) as exc_info:
                launcher.check_resources_before_launch()
            
            assert "memory" in str(exc_info.value).lower()


class TestNetworkFailures:
    """Test handling of network-related failures."""
    
    def test_package_download_interruption(self):
        """Test handling of interrupted package downloads."""
        import urllib.error
        
        with patch('urllib.request.urlopen') as mock_urlopen:
            # Simulate network interruption
            mock_urlopen.side_effect = urllib.error.URLError("Network is unreachable")
            
            downloader = PackageDownloader()
            with pytest.raises(NetworkError) as exc_info:
                downloader.download("https://example.com/package.pspf")
            
            assert "network" in str(exc_info.value).lower()
    
    def test_retry_with_exponential_backoff(self):
        """Test retry mechanism with exponential backoff."""
        attempts = []
        
        def flaky_operation():
            attempts.append(time.time())
            if len(attempts) < 3:
                raise ConnectionError("Temporary failure")
            return "success"
        
        retrier = ExponentialBackoffRetrier(max_attempts=5, base_delay=0.1)
        result = retrier.retry(flaky_operation)
        
        assert result == "success"
        assert len(attempts) == 3
        
        # Check exponential backoff timing
        if len(attempts) > 2:
            delay1 = attempts[1] - attempts[0]
            delay2 = attempts[2] - attempts[1]
            assert delay2 > delay1 * 1.5  # Should increase exponentially


class TestConcurrencyIssues:
    """Test handling of concurrency-related issues."""
    
    def test_concurrent_extraction_lock(self):
        """Test that concurrent extractions are properly locked."""
        package_path = Path("test.pspf")
        extract_dir = Path("extract")
        
        builder = PSPFBuilder()
        builder.add_slot("test", b"data")
        builder.build(package_path)
        
        results = []
        lock_acquired = []
        
        def extract_package():
            try:
                reader = PSPFReader(package_path)
                with reader.extraction_lock(extract_dir):
                    lock_acquired.append(threading.current_thread().name)
                    time.sleep(0.1)  # Simulate extraction
                    reader.extract_all(extract_dir)
                results.append("success")
            except LockError:
                results.append("locked")
        
        # Start multiple extraction threads
        threads = []
        for i in range(5):
            t = threading.Thread(target=extract_package, name=f"Thread-{i}")
            threads.append(t)
            t.start()
        
        for t in threads:
            t.join()
        
        # Only one should succeed, others should be locked
        assert results.count("success") == 1
        assert results.count("locked") == 4
        assert len(lock_acquired) == 1  # Only one thread got the lock
    
    def test_stale_lock_detection(self):
        """Test detection and cleanup of stale locks."""
        lock_file = Path(".extraction.lock")
        
        # Create stale lock (PID that doesn't exist)
        with open(lock_file, 'w') as f:
            f.write("99999999")  # Non-existent PID
        
        launcher = PSPFLauncher()
        
        # Should detect stale lock and clean it up
        assert launcher.acquire_lock(lock_file) is True
        
        # Lock file should be updated with current PID
        with open(lock_file, 'r') as f:
            assert f.read() == str(os.getpid())
    
    def test_race_condition_in_cache(self):
        """Test race conditions in cache access."""
        cache_dir = Path("cache")
        cache_file = cache_dir / "data.cache"
        
        write_count = [0]
        read_count = [0]
        errors = []
        
        def write_cache():
            try:
                cache_dir.mkdir(exist_ok=True)
                for i in range(100):
                    with open(cache_file, 'w') as f:
                        f.write(f"data_{i}")
                    write_count[0] += 1
            except Exception as e:
                errors.append(e)
        
        def read_cache():
            try:
                for i in range(100):
                    if cache_file.exists():
                        with open(cache_file, 'r') as f:
                            _ = f.read()
                        read_count[0] += 1
            except Exception as e:
                errors.append(e)
        
        # Start concurrent readers and writers
        threads = []
        for i in range(3):
            threads.append(threading.Thread(target=write_cache))
            threads.append(threading.Thread(target=read_cache))
        
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        # Should handle concurrency without errors
        assert len(errors) == 0, f"Race condition errors: {errors}"


class TestResourceLeaks:
    """Test prevention of resource leaks."""
    
    def test_file_descriptor_leak(self):
        """Test that file descriptors are properly closed."""
        import resource
        
        # Get initial FD count
        initial_fds = len(os.listdir('/proc/self/fd')) if os.path.exists('/proc/self/fd') else 0
        
        # Perform many operations
        for i in range(100):
            package_path = Path(f"test_{i}.pspf")
            builder = PSPFBuilder()
            builder.add_slot("test", b"data")
            builder.build(package_path)
            
            reader = PSPFReader(package_path)
            reader.read_index()
            reader.close()
            
            package_path.unlink()
        
        # Check FD count hasn't grown significantly
        final_fds = len(os.listdir('/proc/self/fd')) if os.path.exists('/proc/self/fd') else 0
        
        # Allow small variance but not leak
        assert final_fds - initial_fds < 10, f"File descriptor leak detected: {initial_fds} -> {final_fds}"
    
    def test_memory_leak_detection(self):
        """Test for memory leaks during operations."""
        import gc
        import tracemalloc
        
        tracemalloc.start()
        
        # Take initial snapshot
        gc.collect()
        snapshot1 = tracemalloc.take_snapshot()
        
        # Perform many operations
        for i in range(100):
            builder = PSPFBuilder()
            for j in range(10):
                builder.add_slot(f"slot_{j}", b"A" * 10000)
            
            package_path = Path(f"test_{i}.pspf")
            builder.build(package_path)
            
            reader = PSPFReader(package_path)
            reader.extract_all(f"extract_{i}")
            
            # Cleanup
            shutil.rmtree(f"extract_{i}", ignore_errors=True)
            package_path.unlink()
        
        # Take final snapshot
        gc.collect()
        snapshot2 = tracemalloc.take_snapshot()
        
        # Compare memory usage
        top_stats = snapshot2.compare_to(snapshot1, 'lineno')
        
        # Check for significant memory growth
        total_growth = sum(stat.size_diff for stat in top_stats)
        
        # Allow some growth but not leak (< 10MB)
        assert total_growth < 10 * 1024 * 1024, f"Memory leak detected: {total_growth} bytes"
    
    def test_thread_leak_prevention(self):
        """Test that threads are properly cleaned up."""
        initial_threads = threading.active_count()
        
        # Perform operations that create threads
        launcher = PSPFLauncher()
        
        for i in range(10):
            # Launch async operations
            handle = launcher.execute_async("test.pspf", ["--async"])
            handle.wait(timeout=1)
            handle.cleanup()
        
        # Allow time for thread cleanup
        time.sleep(0.5)
        
        final_threads = threading.active_count()
        
        # Should not leak threads
        assert final_threads - initial_threads < 3, f"Thread leak: {initial_threads} -> {final_threads}"


class TestRecoveryMechanisms:
    """Test recovery mechanisms for various failures."""
    
    def test_automatic_retry_on_transient_failure(self):
        """Test automatic retry on transient failures."""
        attempt_count = [0]
        
        def flaky_extraction():
            attempt_count[0] += 1
            if attempt_count[0] < 3:
                raise IOError("Temporary I/O error")
            return "success"
        
        launcher = PSPFLauncher()
        launcher.with_retry(max_attempts=5)
        
        result = launcher.execute_with_retry(flaky_extraction)
        assert result == "success"
        assert attempt_count[0] == 3
    
    def test_graceful_degradation(self):
        """Test graceful degradation when non-critical components fail."""
        launcher = PSPFLauncher()
        
        # Simulate telemetry failure (non-critical)
        with patch('flavor.telemetry.send_metrics') as mock_telemetry:
            mock_telemetry.side_effect = Exception("Telemetry service down")
            
            # Should still work without telemetry
            result = launcher.execute("test.pspf", ["--run"])
            assert result.success is True
    
    def test_rollback_on_failed_update(self):
        """Test rollback mechanism when update fails."""
        updater = PackageUpdater()
        
        # Backup current state
        original_version = updater.get_current_version()
        
        # Simulate failed update
        with patch('flavor.updater.apply_update') as mock_update:
            mock_update.side_effect = Exception("Update failed")
            
            try:
                updater.update_to_version("2.0.0")
            except:
                pass
            
            # Should rollback to original version
            assert updater.get_current_version() == original_version
    
    def test_checkpoint_resume(self):
        """Test checkpoint/resume for long operations."""
        extractor = CheckpointedExtractor()
        
        # Simulate interruption after 3 slots
        with patch.object(extractor, 'extract_slot') as mock_extract:
            mock_extract.side_effect = [
                "slot_0",
                "slot_1", 
                "slot_2",
                KeyboardInterrupt("User interrupted"),
            ]
            
            try:
                extractor.extract_with_checkpoint("package.pspf", 10)
            except KeyboardInterrupt:
                pass
        
        # Should have checkpoint
        assert extractor.get_checkpoint() == 3
        
        # Resume from checkpoint
        with patch.object(extractor, 'extract_slot') as mock_extract:
            mock_extract.side_effect = [f"slot_{i}" for i in range(3, 10)]
            
            extractor.resume_from_checkpoint("package.pspf")
        
        # Should complete all slots
        assert extractor.get_checkpoint() == 10