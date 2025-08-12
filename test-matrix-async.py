#!/usr/bin/env python3
"""
Enhanced matrix test runner for PSPF 2025 inspired by wrkenv's approach.
Combines the best of both: pytest simplicity with async execution and rich UI.
"""

import asyncio
import json
import os
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from rich.console import Console
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TextColumn,
    TimeElapsedColumn,
)
from rich.table import Table


@dataclass
class MatrixCombination:
    """Represents a single builder/launcher combination to test."""
    builder: str
    launcher: str
    builder_binary: str = ""
    launcher_binary: str = ""

    def __post_init__(self):
        self.builder_binary = f"pspf-builder-rust" if self.builder == "rust" else "pspf-builder"
        self.launcher_binary = f"pspf-launcher-rust" if self.launcher == "rust" else "pspf-launcher"

    def __str__(self):
        return f"{self.builder}-{self.launcher}"


@dataclass
class TestResult:
    """Result of a single test within a combination."""
    name: str
    passed: bool
    error_message: Optional[str] = None
    duration: float = 0.0


@dataclass
class MatrixResult:
    """Result of testing a single builder/launcher combination."""
    combination: MatrixCombination
    success: bool
    duration_seconds: float = 0.0
    error_message: Optional[str] = None
    test_results: List[TestResult] = field(default_factory=list)
    
    @property
    def passed_tests(self) -> int:
        return sum(1 for t in self.test_results if t.passed)
    
    @property
    def total_tests(self) -> int:
        return len(self.test_results)


class PSPFMatrixRunner:
    """Matrix test runner for PSPF 2025 with async execution and rich UI."""
    
    def __init__(self, parallel_jobs: int = 4, timeout_seconds: int = 30):
        self.console = Console()
        self.parallel_jobs = parallel_jobs
        self.timeout_seconds = timeout_seconds
        self.manifest_path = Path("test-manifest.json")
        
    def generate_combinations(self) -> List[MatrixCombination]:
        """Generate all builder/launcher combinations."""
        builders = ["go", "rust"]
        launchers = ["go", "rust"]
        
        combinations = []
        for builder in builders:
            for launcher in launchers:
                combinations.append(MatrixCombination(builder, launcher))
        
        return combinations
    
    async def run_test_async(self, combination: MatrixCombination, semaphore: asyncio.Semaphore) -> MatrixResult:
        """Run tests for a single combination asynchronously."""
        async with semaphore:
            start_time = time.time()
            result = MatrixResult(combination=combination, success=True)
            
            bundle_name = f"async-matrix-{combination}.pspf"
            
            try:
                # Test 1: Build bundle
                build_result = await self._run_build_test(combination, bundle_name)
                result.test_results.append(build_result)
                if not build_result.passed:
                    result.success = False
                    result.error_message = "Build failed"
                    return result
                
                # Make bundle executable
                Path(bundle_name).chmod(0o755)
                
                # Test 2: CLI info
                info_result = await self._run_cli_test(bundle_name, "info", "CLI info test")
                result.test_results.append(info_result)
                if not info_result.passed:
                    result.success = False
                
                # Test 3: Verify
                verify_result = await self._run_cli_test(bundle_name, "verify", "Verify test")
                result.test_results.append(verify_result)
                if not verify_result.passed:
                    result.success = False
                
                # Test 4: Extract
                extract_result = await self._run_extract_test(bundle_name, combination)
                result.test_results.append(extract_result)
                if not extract_result.passed:
                    result.success = False
                
                # Test 5: Argument passthrough
                passthrough_result = await self._run_passthrough_test(bundle_name)
                result.test_results.append(passthrough_result)
                if not passthrough_result.passed:
                    result.success = False
                
                # Test 6: Builder identification
                builder_id_result = await self._run_builder_id_test(bundle_name, combination)
                result.test_results.append(builder_id_result)
                if not builder_id_result.passed:
                    result.success = False
                
            except Exception as e:
                result.success = False
                result.error_message = str(e)
            finally:
                # Cleanup
                Path(bundle_name).unlink(missing_ok=True)
                result.duration_seconds = time.time() - start_time
            
            return result
    
    async def _run_build_test(self, combination: MatrixCombination, bundle_name: str) -> TestResult:
        """Test building a bundle."""
        start = time.time()
        
        if combination.builder == "rust":
            cmd = [f"./{combination.builder_binary}", "--manifest", str(self.manifest_path), 
                   "--output", bundle_name, "--launcher", combination.launcher]
        else:
            cmd = [f"./{combination.builder_binary}", "-m", str(self.manifest_path), 
                   "-o", bundle_name, "-l", combination.launcher]
        
        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=self.timeout_seconds)
            
            if proc.returncode == 0 and Path(bundle_name).exists():
                return TestResult("Build", True, duration=time.time() - start)
            else:
                return TestResult("Build", False, 
                                error_message=f"Build failed: {stderr.decode()}", 
                                duration=time.time() - start)
        except asyncio.TimeoutError:
            return TestResult("Build", False, error_message="Build timeout", duration=time.time() - start)
        except Exception as e:
            return TestResult("Build", False, error_message=str(e), duration=time.time() - start)
    
    async def _run_cli_test(self, bundle_name: str, command: str, test_name: str) -> TestResult:
        """Run a CLI command test."""
        start = time.time()
        
        try:
            proc = await asyncio.create_subprocess_exec(
                f"./{bundle_name}", command,
                env={**os.environ, "FLAVOR_LAUNCHER_CLI": "true"},
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=self.timeout_seconds)
            
            if proc.returncode == 0:
                return TestResult(test_name, True, duration=time.time() - start)
            else:
                return TestResult(test_name, False, 
                                error_message=f"Command failed: {stderr.decode()}", 
                                duration=time.time() - start)
        except Exception as e:
            return TestResult(test_name, False, error_message=str(e), duration=time.time() - start)
    
    async def _run_extract_test(self, bundle_name: str, combination: MatrixCombination) -> TestResult:
        """Test slot extraction."""
        start = time.time()
        extract_dir = f"/tmp/async-matrix-{combination}"
        
        try:
            proc = await asyncio.create_subprocess_exec(
                f"./{bundle_name}", "extract", "0", extract_dir,
                env={**os.environ, "FLAVOR_LAUNCHER_CLI": "true"},
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=self.timeout_seconds)
            
            if proc.returncode == 0 and Path(f"{extract_dir}/readme.txt").exists():
                return TestResult("Extract", True, duration=time.time() - start)
            else:
                return TestResult("Extract", False, 
                                error_message="Extract failed or file missing", 
                                duration=time.time() - start)
        except Exception as e:
            return TestResult("Extract", False, error_message=str(e), duration=time.time() - start)
        finally:
            # Cleanup
            subprocess.run(["rm", "-rf", extract_dir], capture_output=True)
    
    async def _run_passthrough_test(self, bundle_name: str) -> TestResult:
        """Test argument passthrough."""
        start = time.time()
        
        try:
            proc = await asyncio.create_subprocess_exec(
                f"./{bundle_name}", "arg1", "arg2", "--flag", "value",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=self.timeout_seconds)
            output = stdout.decode() + stderr.decode()
            
            if "arg1 arg2 --flag value" in output:
                return TestResult("Arg Passthrough", True, duration=time.time() - start)
            else:
                return TestResult("Arg Passthrough", False, 
                                error_message="Arguments not found in output", 
                                duration=time.time() - start)
        except Exception as e:
            return TestResult("Arg Passthrough", False, error_message=str(e), duration=time.time() - start)
    
    async def _run_builder_id_test(self, bundle_name: str, combination: MatrixCombination) -> TestResult:
        """Test builder identification."""
        start = time.time()
        
        try:
            proc = await asyncio.create_subprocess_exec(
                f"./{bundle_name}", "info",
                env={**os.environ, "FLAVOR_LAUNCHER_CLI": "true"},
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=self.timeout_seconds)
            output = stdout.decode()
            
            expected_builder = f"{combination.builder}/pspf-builder"
            if expected_builder in output:
                return TestResult("Builder ID", True, duration=time.time() - start)
            else:
                return TestResult("Builder ID", False, 
                                error_message=f"Expected '{expected_builder}' not found", 
                                duration=time.time() - start)
        except Exception as e:
            return TestResult("Builder ID", False, error_message=str(e), duration=time.time() - start)
    
    async def run_all_tests(self) -> List[MatrixResult]:
        """Run all matrix tests with progress tracking."""
        combinations = self.generate_combinations()
        semaphore = asyncio.Semaphore(self.parallel_jobs)
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TimeElapsedColumn(),
            console=self.console,
        ) as progress:
            overall_task = progress.add_task(
                "[cyan]Running matrix tests...", total=len(combinations)
            )
            
            tasks = []
            for combination in combinations:
                task = asyncio.create_task(self.run_test_async(combination, semaphore))
                tasks.append(task)
                
                # Update progress as tasks complete
                async def update_progress(t):
                    result = await t
                    progress.update(overall_task, advance=1, 
                                  description=f"[cyan]Completed {combination}")
                    return result
                
                tasks[-1] = update_progress(tasks[-1])
            
            results = await asyncio.gather(*tasks)
        
        return results
    
    def display_results(self, results: List[MatrixResult]):
        """Display test results in a rich table."""
        table = Table(title="PSPF 2025 Matrix Test Results")
        table.add_column("Combination", style="cyan")
        table.add_column("Status", style="bold")
        table.add_column("Tests", justify="center")
        table.add_column("Duration", justify="right")
        table.add_column("Details")
        
        total_passed = 0
        total_failed = 0
        
        for result in results:
            status = "[green]PASSED[/green]" if result.success else "[red]FAILED[/red]"
            tests = f"{result.passed_tests}/{result.total_tests}"
            duration = f"{result.duration_seconds:.2f}s"
            
            details = []
            if result.error_message:
                details.append(f"[red]{result.error_message}[/red]")
            
            for test in result.test_results:
                if not test.passed:
                    details.append(f"[yellow]{test.name}: {test.error_message}[/yellow]")
            
            details_str = "\n".join(details) if details else "[green]All tests passed[/green]"
            
            table.add_row(str(result.combination), status, tests, duration, details_str)
            
            if result.success:
                total_passed += 1
            else:
                total_failed += 1
        
        self.console.print(table)
        
        # Summary
        self.console.print(f"\n[bold]Summary:[/bold]")
        self.console.print(f"  Total combinations: {len(results)}")
        self.console.print(f"  [green]Passed: {total_passed}[/green]")
        self.console.print(f"  [red]Failed: {total_failed}[/red]")
        
        # Save results to JSON
        results_data = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "summary": {
                "total": len(results),
                "passed": total_passed,
                "failed": total_failed
            },
            "results": [
                {
                    "combination": str(r.combination),
                    "success": r.success,
                    "duration": r.duration_seconds,
                    "error": r.error_message,
                    "tests": [
                        {
                            "name": t.name,
                            "passed": t.passed,
                            "error": t.error_message,
                            "duration": t.duration
                        }
                        for t in r.test_results
                    ]
                }
                for r in results
            ]
        }
        
        with open("matrix-test-results.json", "w") as f:
            json.dump(results_data, f, indent=2)
        
        self.console.print("\n[dim]Results saved to matrix-test-results.json[/dim]")
        
        return total_failed == 0


async def main():
    """Main entry point."""
    import os
    
    # Check prerequisites
    console = Console()
    missing = []
    for binary in ["pspf-builder", "pspf-builder-rust", "pspf-launcher", "pspf-launcher-rust"]:
        if not Path(binary).exists():
            missing.append(binary)
    
    if missing:
        console.print(f"[red]Missing binaries: {', '.join(missing)}[/red]")
        return 1
    
    runner = PSPFMatrixRunner(parallel_jobs=4, timeout_seconds=30)
    
    console.print("[bold cyan]PSPF 2025 Matrix Tests - Async Edition[/bold cyan]")
    console.print(f"Running {len(runner.generate_combinations())} combinations with {runner.parallel_jobs} parallel jobs\n")
    
    results = await runner.run_all_tests()
    success = runner.display_results(results)
    
    return 0 if success else 1


if __name__ == "__main__":
    try:
        # Check if rich is available
        import rich
    except ImportError:
        print("Installing required dependency: rich")
        subprocess.run([sys.executable, "-m", "pip", "install", "rich"], check=True)
    
    import sys
    sys.exit(asyncio.run(main()))