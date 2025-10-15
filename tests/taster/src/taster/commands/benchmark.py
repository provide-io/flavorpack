#!/usr/bin/env python3
"""Performance benchmarking and profiling commands"""

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import time

import click
import psutil


@click.group("benchmark")
def benchmark_command() -> None:
    """⚡ Performance testing and profiling"""
    pass


@benchmark_command.command("memory")
@click.argument("command", nargs=-1, required=True)
@click.option("--interval", type=float, default=0.1, help="Sampling interval in seconds")
@click.option("--json-output", is_flag=True, help="Output as JSON")
def memory_profile(command, interval, json_output) -> None:
    """Track memory usage of a command"""

    # Start the process
    proc = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    memory_samples = []
    start_time = time.time()

    try:
        process = psutil.Process(proc.pid)

        while proc.poll() is None:
            try:
                # Sample memory and CPU
                mem_info = process.memory_info()
                cpu_percent = process.cpu_percent(interval=interval)

                sample = {
                    "time": time.time() - start_time,
                    "rss": mem_info.rss,  # Resident Set Size
                    "vms": mem_info.vms,  # Virtual Memory Size
                    "cpu": cpu_percent,
                    "threads": process.num_threads(),
                }

                memory_samples.append(sample)

                if not json_output:
                    click.echo(
                        f"[{sample['time']:.1f}s] RSS: {sample['rss'] / 1024 / 1024:.1f}MB, CPU: {sample['cpu']:.1f}%",
                        err=True,
                    )

            except psutil.NoSuchProcess:
                break

            time.sleep(interval)

    except KeyboardInterrupt:
        proc.terminate()

    # Wait for completion
    _stdout, _stderr = proc.communicate()
    end_time = time.time() - start_time

    # Calculate statistics
    if memory_samples:
        peak_rss = max(s["rss"] for s in memory_samples)
        avg_rss = sum(s["rss"] for s in memory_samples) / len(memory_samples)
        peak_cpu = max(s["cpu"] for s in memory_samples)
        avg_cpu = sum(s["cpu"] for s in memory_samples) / len(memory_samples)
    else:
        peak_rss = avg_rss = peak_cpu = avg_cpu = 0

    result = {
        "command": " ".join(command),
        "duration": end_time,
        "exit_code": proc.returncode,
        "samples": memory_samples,
        "peak_rss_mb": peak_rss / 1024 / 1024,
        "avg_rss_mb": avg_rss / 1024 / 1024,
        "peak_cpu_percent": peak_cpu,
        "avg_cpu_percent": avg_cpu,
        "total_samples": len(memory_samples),
    }

    if json_output:
        print(json.dumps(result, indent=2))
    else:
        click.echo(f"\n{'=' * 60}", err=True)
        click.echo(f"Duration: {result['duration']:.2f}s", err=True)
        click.echo(f"Peak RSS: {result['peak_rss_mb']:.1f}MB", err=True)
        click.echo(f"Avg RSS: {result['avg_rss_mb']:.1f}MB", err=True)
        click.echo(f"Peak CPU: {result['peak_cpu_percent']:.1f}%", err=True)
        click.echo(f"Exit code: {result['exit_code']}", err=True)


@benchmark_command.command("speed")
@click.option("--iterations", type=int, default=10, help="Number of iterations")
@click.option("--warmup", type=int, default=2, help="Warmup iterations")
def speed_test(iterations, warmup) -> None:
    """Benchmark PSPF operations"""

    results = {"build": [], "verify": [], "extract": []}

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)

        # Create test data
        test_file = tmpdir / "test.txt"
        test_file.write_text("Test data for benchmarking" * 100)

        # Import what we need
        sys.path.insert(0, str(Path(__file__).parents[4] / "src"))
        from flavor.psp.format_2025 import PSPFBuilder, PSPFReader

        click.echo(f"Running {warmup} warmup iterations...")

        # Warmup
        for _ in range(warmup):
            builder = PSPFBuilder()
            bundle_path = tmpdir / "warmup.psp"
            builder.build(
                output_path=bundle_path,
                metadata={
                    "format": "PSPF/2025",
                    "package": {"name": "test", "version": "1.0"},
                },
                slots=[],
            )
            bundle_path.unlink()

        click.echo(f"Running {iterations} benchmark iterations...")

        # Benchmark build
        for i in range(iterations):
            start = time.perf_counter()

            builder = PSPFBuilder()
            bundle_path = tmpdir / f"bench_{i}.psp"
            builder.build(
                output_path=bundle_path,
                metadata={
                    "format": "PSPF/2025",
                    "package": {"name": "test", "version": "1.0"},
                },
                slots=[],
            )

            build_time = time.perf_counter() - start
            results["build"].append(build_time)

            # Benchmark verify
            start = time.perf_counter()
            reader = PSPFReader(bundle_path)
            reader.verify_magic_trailer()
            reader.verify_all_checksums()
            verify_time = time.perf_counter() - start
            results["verify"].append(verify_time)

            # Benchmark extract
            start = time.perf_counter()
            reader.read_metadata()
            extract_time = time.perf_counter() - start
            results["extract"].append(extract_time)

            click.echo(
                f"  Iteration {i + 1}: Build={build_time * 1000:.1f}ms, Verify={verify_time * 1000:.1f}ms, Extract={extract_time * 1000:.1f}ms"
            )

    # Calculate statistics
    click.echo(f"\n{'=' * 60}")
    click.echo("BENCHMARK RESULTS")
    click.echo(f"{'=' * 60}")

    for op, times in results.items():
        if times:
            avg = sum(times) / len(times) * 1000  # Convert to ms
            min_time = min(times) * 1000
            max_time = max(times) * 1000

            click.echo(f"\n{op.upper()}:")
            click.echo(f"  Avg: {avg:.2f}ms")
            click.echo(f"  Min: {min_time:.2f}ms")
            click.echo(f"  Max: {max_time:.2f}ms")


@benchmark_command.command("concurrent")
@click.option("--workers", type=int, default=10, help="Number of concurrent workers")
@click.option("--duration", type=int, default=10, help="Test duration in seconds")
@click.option("--operation", type=click.Choice(["build", "read", "mixed"]), default="mixed")
def concurrent_test(workers, duration, operation) -> None:
    """Test concurrent PSPF operations"""

    import queue
    import threading

    results = queue.Queue()
    stop_event = threading.Event()

    def worker(worker_id) -> None:
        """Worker thread"""
        sys.path.insert(0, str(Path(__file__).parents[4] / "src"))
        from flavor.psp.format_2025 import PSPFBuilder, PSPFReader

        ops_count = 0
        errors = 0

        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)

            # Create a test bundle for read operations
            if operation in ["read", "mixed"]:
                builder = PSPFBuilder()
                test_bundle = tmpdir / "test.psp"
                builder.build(
                    output_path=test_bundle,
                    metadata={
                        "format": "PSPF/2025",
                        "package": {"name": "test", "version": "1.0"},
                    },
                    slots=[],
                )

            while not stop_event.is_set():
                try:
                    if operation == "build" or (operation == "mixed" and ops_count % 2 == 0):
                        # Build operation
                        builder = PSPFBuilder()
                        bundle_path = tmpdir / f"worker_{worker_id}_{ops_count}.psp"
                        builder.build(
                            output_path=bundle_path,
                            metadata={
                                "format": "PSPF/2025",
                                "package": {
                                    "name": f"test_{worker_id}",
                                    "version": "1.0",
                                },
                            },
                            slots=[],
                        )
                        bundle_path.unlink()  # Clean up

                    else:
                        # Read operation
                        reader = PSPFReader(test_bundle)
                        reader.verify_magic_trailer()
                        reader.read_metadata()

                    ops_count += 1

                except Exception as e:
                    errors += 1
                    click.echo(f"Worker {worker_id} error: {e}", err=True)

        results.put((worker_id, ops_count, errors))

    # Start workers
    threads = []
    click.echo(f"Starting {workers} workers for {duration} seconds...")

    for i in range(workers):
        t = threading.Thread(target=worker, args=(i,))
        t.start()
        threads.append(t)

    # Run for specified duration
    time.sleep(duration)
    stop_event.set()

    # Wait for workers to finish
    for t in threads:
        t.join()

    # Collect results
    total_ops = 0
    total_errors = 0
    worker_results = []

    while not results.empty():
        worker_id, ops, errors = results.get()
        total_ops += ops
        total_errors += errors
        worker_results.append((worker_id, ops, errors))

    # Display results
    click.echo(f"\n{'=' * 60}")
    click.echo("CONCURRENT TEST RESULTS")
    click.echo(f"{'=' * 60}")
    click.echo(f"Total operations: {total_ops}")
    click.echo(f"Operations/second: {total_ops / duration:.1f}")
    click.echo(f"Total errors: {total_errors}")
    click.echo(f"Error rate: {total_errors / total_ops * 100:.2f}%" if total_ops > 0 else "N/A")

    if worker_results:
        click.echo("\nPer-worker statistics:")
        for worker_id, ops, errors in sorted(worker_results):
            click.echo(f"  Worker {worker_id}: {ops} ops, {errors} errors")


@benchmark_command.command("leak")
@click.argument("command", nargs=-1, required=True)
@click.option("--threshold", type=int, default=10, help="Memory growth threshold in MB")
def leak_detector(command, threshold) -> None:
    """Detect memory leaks in long-running processes"""

    proc = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    try:
        process = psutil.Process(proc.pid)

        initial_memory = None
        samples = []
        leak_detected = False

        click.echo("Monitoring for memory leaks...", err=True)
        click.echo("Press Ctrl+C to stop", err=True)

        while proc.poll() is None:
            try:
                mem_info = process.memory_info()
                current_rss = mem_info.rss / 1024 / 1024  # MB

                if initial_memory is None:
                    initial_memory = current_rss

                growth = current_rss - initial_memory
                samples.append((time.time(), current_rss, growth))

                # Check for leak
                if growth > threshold and not leak_detected:
                    click.echo(
                        f"\n⚠️ POTENTIAL LEAK DETECTED: Memory grew by {growth:.1f}MB",
                        err=True,
                    )
                    leak_detected = True

                # Show progress
                click.echo(f"\rRSS: {current_rss:.1f}MB (Δ{growth:+.1f}MB)", nl=False, err=True)

                time.sleep(1)

            except psutil.NoSuchProcess:
                break

    except KeyboardInterrupt:
        proc.terminate()

    proc.wait()

    # Analyze trend
    if len(samples) > 10:
        # Simple linear regression to detect trend
        n = len(samples)
        x = [i for i in range(n)]
        y = [s[1] for s in samples]  # RSS values

        x_mean = sum(x) / n
        y_mean = sum(y) / n

        numerator = sum((x[i] - x_mean) * (y[i] - y_mean) for i in range(n))
        denominator = sum((x[i] - x_mean) ** 2 for i in range(n))

        if denominator > 0:
            slope = numerator / denominator

            click.echo(f"\n\n{'=' * 60}", err=True)
            click.echo("LEAK ANALYSIS", err=True)
            click.echo(f"{'=' * 60}", err=True)
            click.echo(f"Memory trend: {slope:.3f} MB/sample", err=True)

            if slope > 0.1:  # Growing more than 0.1 MB per second
                click.echo("❌ LIKELY MEMORY LEAK", err=True)
            elif slope > 0.01:
                click.echo("⚠️ POSSIBLE MEMORY LEAK", err=True)
            else:
                click.echo("✅ NO LEAK DETECTED", err=True)
