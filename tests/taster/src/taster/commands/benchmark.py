#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""Performance benchmarking and profiling commands."""

from __future__ import annotations

from collections.abc import Callable, Sequence
import json
from pathlib import Path
from queue import Empty, Queue
import subprocess
import sys
import tempfile
from threading import Event, Thread
import time
from typing import Literal

import click
from provide.foundation.console import perr, pout
import psutil

OperationMode = Literal["build", "read", "mixed"]
WorkerResult = tuple[int, int, int]


def _should_run_build(operation: OperationMode, ops_completed: int) -> bool:
    """Return True if this iteration should execute a build step."""
    return operation == "build" or (operation == "mixed" and ops_completed % 2 == 0)


def _make_worker(
    operation: OperationMode,
    stop_event: Event,
    results: Queue[WorkerResult],
) -> Callable[[int], None]:
    """Create a worker callback for the concurrent benchmark."""

    def worker(worker_id: int) -> None:
        """Execute PSPF build/read operations until the stop event triggers."""
        sys.path.insert(0, str(Path(__file__).parents[4] / "src"))
        from flavor.psp.format_2025 import PSPFBuilder, PSPFReader

        ops_count = 0
        errors = 0

        with tempfile.TemporaryDirectory() as tmpdir_str:
            tmpdir = Path(tmpdir_str)
            test_bundle: Path | None = None

            if operation in {"read", "mixed"}:
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
                    if _should_run_build(operation, ops_count):
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
                        bundle_path.unlink()
                    else:
                        if test_bundle is None:
                            raise RuntimeError("Test bundle missing for read operation")
                        reader = PSPFReader(test_bundle)
                        reader.verify_magic_trailer()
                        reader.read_metadata()

                    ops_count += 1

                except Exception as exc:
                    errors += 1
                    perr(f"Worker {worker_id} error: {exc}")

        results.put((worker_id, ops_count, errors))

    return worker


def _start_workers(worker_count: int, worker_fn: Callable[[int], None]) -> list[Thread]:
    """Spawn worker threads and return them."""
    threads: list[Thread] = []
    for worker_id in range(worker_count):
        thread = Thread(target=worker_fn, args=(worker_id,))
        thread.start()
        threads.append(thread)
    return threads


def _collect_worker_results(result_queue: Queue[WorkerResult]) -> list[WorkerResult]:
    """Drain the worker results queue."""
    worker_results: list[WorkerResult] = []
    while True:
        try:
            worker_results.append(result_queue.get_nowait())
        except Empty:
            break
    return worker_results


def _display_worker_summary(worker_results: Sequence[WorkerResult], duration: int) -> None:
    """Print aggregate and per-worker statistics."""
    total_ops = sum(result[1] for result in worker_results)
    total_errors = sum(result[2] for result in worker_results)

    pout(f"\n{'=' * 60}")
    pout("CONCURRENT TEST RESULTS")
    pout(f"{'=' * 60}")
    pout(f"Total operations: {total_ops}")
    if duration > 0:
        pout(f"Operations/second: {total_ops / duration:.1f}")
    pout(f"Total errors: {total_errors}")
    if total_ops > 0:
        error_rate = total_errors / total_ops * 100
        pout(f"Error rate: {error_rate:.2f}%")
    else:
        pout("Error rate: N/A")

    if worker_results:
        pout("\nPer-worker statistics:")
        for worker_id, ops, errors in sorted(worker_results):
            pout(f"  Worker {worker_id}: {ops} ops, {errors} errors")


@click.group("benchmark")
def benchmark_command() -> None:
    """⚡ Performance testing and profiling"""
    pass


@benchmark_command.command("memory")
@click.argument("command", nargs=-1, required=True)
@click.option("--interval", type=float, default=0.1, help="Sampling interval in seconds")
@click.option("--json-output", is_flag=True, help="Output as JSON")
def memory_profile(command: Sequence[str], interval: float, json_output: bool) -> None:
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
                    pout(
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
        perr(f"\n{'=' * 60}")
        perr(f"Duration: {result['duration']:.2f}s")
        perr(f"Peak RSS: {result['peak_rss_mb']:.1f}MB")
        perr(f"Avg RSS: {result['avg_rss_mb']:.1f}MB")
        perr(f"Peak CPU: {result['peak_cpu_percent']:.1f}%")
        perr(f"Exit code: {result['exit_code']}")


@benchmark_command.command("speed")
@click.option("--iterations", type=int, default=10, help="Number of iterations")
@click.option("--warmup", type=int, default=2, help="Warmup iterations")
def speed_test(iterations: int, warmup: int) -> None:
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

        pout(f"Running {warmup} warmup iterations...")

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

        pout(f"Running {iterations} benchmark iterations...")

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

            pout(
                f"  Iteration {i + 1}: Build={build_time * 1000:.1f}ms, Verify={verify_time * 1000:.1f}ms, Extract={extract_time * 1000:.1f}ms"
            )

    # Calculate statistics
    pout(f"\n{'=' * 60}")
    pout("BENCHMARK RESULTS")
    pout(f"{'=' * 60}")

    for op, times in results.items():
        if times:
            avg = sum(times) / len(times) * 1000  # Convert to ms
            min_time = min(times) * 1000
            max_time = max(times) * 1000

            pout(f"\n{op.upper()}:")
            pout(f"  Avg: {avg:.2f}ms")
            pout(f"  Min: {min_time:.2f}ms")
            pout(f"  Max: {max_time:.2f}ms")


@benchmark_command.command("concurrent")
@click.option("--workers", type=int, default=10, help="Number of concurrent workers")
@click.option("--duration", type=int, default=10, help="Test duration in seconds")
@click.option("--operation", type=click.Choice(["build", "read", "mixed"]), default="mixed")
def concurrent_test(workers: int, duration: int, operation: OperationMode) -> None:
    """Test concurrent PSPF operations."""

    results: Queue[WorkerResult] = Queue()
    stop_event = Event()
    worker_fn = _make_worker(operation, stop_event, results)

    pout(f"Starting {workers} workers for {duration} seconds...")
    threads = _start_workers(workers, worker_fn)

    time.sleep(duration)
    stop_event.set()

    for thread in threads:
        thread.join()

    worker_results = _collect_worker_results(results)
    _display_worker_summary(worker_results, duration)


@benchmark_command.command("leak")
@click.argument("command", nargs=-1, required=True)
@click.option("--threshold", type=int, default=10, help="Memory growth threshold in MB")
def leak_detector(command: Sequence[str], threshold: int) -> None:
    """Detect memory leaks in long-running processes."""

    proc = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    try:
        process = psutil.Process(proc.pid)

        initial_memory: float | None = None
        samples: list[tuple[float, float, float]] = []
        leak_detected = False

        perr("Monitoring for memory leaks...")
        perr("Press Ctrl+C to stop")

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
                    pout(
                        f"\n⚠️ POTENTIAL LEAK DETECTED: Memory grew by {growth:.1f}MB",
                        err=True,
                    )
                    leak_detected = True

                # Show progress
                pout(f"\rRSS: {current_rss:.1f}MB (Δ{growth:+.1f}MB)", nl=False, err=True)

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
        x = list(range(n))
        y = [sample[1] for sample in samples]

        x_mean = sum(x) / n
        y_mean = sum(y) / n

        numerator = sum((x[i] - x_mean) * (y[i] - y_mean) for i in range(n))
        denominator = sum((x[i] - x_mean) ** 2 for i in range(n))

        if denominator > 0:
            slope = numerator / denominator

            perr(f"\n\n{'=' * 60}")
            perr("LEAK ANALYSIS")
            perr(f"{'=' * 60}")
            perr(f"Memory trend: {slope:.3f} MB/sample")

            if slope > 0.1:  # Growing more than 0.1 MB per second
                perr("❌ LIKELY MEMORY LEAK")
            elif slope > 0.01:
                perr("⚠️ POSSIBLE MEMORY LEAK")
            else:
                pass


# 🌶️📦🔚
