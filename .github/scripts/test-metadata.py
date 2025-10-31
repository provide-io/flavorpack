#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""Unified test metadata collection and reporting tool.
Consolidates test metadata collection, results combining, and platform metadata generation.

Usage:
    test-metadata.py collect [output_dir]  - Collect test metadata
    test-metadata.py combine <input_dir> [output_file]  - Combine test results
    test-metadata.py platform <platform> <version> [cache_hit]  - Generate platform metadata"""

from datetime import UTC, datetime
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
from typing import Any

# Set up Windows Unicode support early - same as flavor/cli.py
if sys.platform == "win32":
    # Ensure UTF-8 encoding for Windows console
    if not os.environ.get("PYTHONIOENCODING"):
        os.environ["PYTHONIOENCODING"] = "utf-8"
    if not os.environ.get("PYTHONUTF8"):
        os.environ["PYTHONUTF8"] = "1"


def run_command(cmd: list[str], timeout: int = 5) -> str:
    """Run command and return output."""
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return result.stdout.strip() if result.returncode == 0 else ""
    except Exception:
        return ""


def collect_system_info() -> dict[str, Any]:
    """Collect system information."""
    return {
        "timestamp": datetime.now(UTC).isoformat(),
        "platform": platform.system(),
        "architecture": platform.machine(),
        "processor": platform.processor() or "unknown",
        "python_version": platform.python_version(),
        "python_implementation": platform.python_implementation(),
        "pip_version": run_command(["pip", "--version"]),
        "uv_version": run_command(["uv", "--version"]),
        "pytest_version": run_command(["pytest", "--version"]),
        "github_runner": os.environ.get("RUNNER_NAME", "local"),
        "github_run_id": os.environ.get("GITHUB_RUN_ID", ""),
        "github_workflow": os.environ.get("GITHUB_WORKFLOW", ""),
        "github_ref": os.environ.get("GITHUB_REF", ""),
        "github_sha": os.environ.get("GITHUB_SHA", ""),
    }


def collect_test_metadata(output_dir: Path) -> None:
    """Collect comprehensive test metadata."""
    output_dir.mkdir(parents=True, exist_ok=True)

    print("📊 Collecting test metadata...")

    # System information
    system_info = collect_system_info()
    (output_dir / "system-info.json").write_text(json.dumps(system_info, indent=2))

    # Python packages
    pip_list = run_command(["pip", "list", "--format=json"])
    if pip_list:
        (output_dir / "pip-list.json").write_text(pip_list)

    # Test summary from pytest report
    test_report = Path("test-report.json")
    if test_report.exists():
        with open(test_report) as f:
            data = json.load(f)

        summary = {
            "total_tests": data.get("summary", {}).get("total", 0),
            "passed": data.get("summary", {}).get("passed", 0),
            "failed": data.get("summary", {}).get("failed", 0),
            "skipped": data.get("summary", {}).get("skipped", 0),
            "duration": data.get("duration", 0),
        }

        # Find slowest tests
        if "tests" in data:
            tests = [
                {"name": t["nodeid"], "duration": t.get("duration", 0)}
                for t in data["tests"]
                if t.get("duration", 0) > 0
            ]
            tests.sort(key=lambda x: x["duration"], reverse=True)
            summary["slowest_tests"] = tests[:10]

        (output_dir / "test-summary.json").write_text(json.dumps(summary, indent=2))

    # Coverage summary
    coverage_report = Path("coverage.json")
    if coverage_report.exists():
        with open(coverage_report) as f:
            data = json.load(f)

        totals = data.get("totals", {})
        coverage_summary = {
            "total_lines": totals.get("num_statements", 0),
            "covered_lines": totals.get("covered_lines", 0),
            "percent_covered": totals.get("percent_covered", 0),
            "files_analyzed": len(data.get("files", {})),
        }
        (output_dir / "coverage-summary.json").write_text(json.dumps(coverage_summary, indent=2))

    # Git info
    git_info = {
        "branch": run_command(["git", "branch", "--show-current"]),
        "commit": run_command(["git", "rev-parse", "HEAD"]),
        "status": run_command(["git", "status", "--short"]),
    }
    (output_dir / "git-info.json").write_text(json.dumps(git_info, indent=2))

    # Environment variables (filtered)
    env_vars = {
        k: v
        for k, v in os.environ.items()
        if any(k.startswith(p) for p in ["PYTHON", "PIP", "UV", "PYTEST", "GITHUB", "CI", "FLAVOR"])
    }
    (output_dir / "environment.json").write_text(json.dumps(env_vars, indent=2))


def combine_test_results(input_dir: Path, output_file: Path) -> None:
    """Combine test results from multiple platforms."""
    print(f"📋 Combining test results from {input_dir}")

    combined = {
        "timestamp": datetime.now(UTC).isoformat(),
        "platforms": {},
        "summary": {
            "platforms_tested": 0,
            "total_tests": 0,
            "passed": 0,
            "failed": 0,
            "skipped": 0,
        },
    }

    # Process each platform's test results
    platforms = [
        "linux_amd64",
        "linux_arm64",
        "darwin_amd64",
        "darwin_arm64",
        "windows_amd64",
    ]

    for platform_name in platforms:
        # Find test result files for this platform
        pattern = f"*{platform_name}*test*.json"
        test_files = list(input_dir.glob(f"**/{pattern}"))

        if test_files:
            # Merge results from all test files for this platform
            platform_data = {}
            for test_file in test_files:
                try:
                    with open(test_file) as f:
                        data = json.load(f)
                        # Merge data
                        if not platform_data:
                            platform_data = data
                        else:
                            # Merge test counts
                            if "summary" in data:
                                if "summary" not in platform_data:
                                    platform_data["summary"] = {}
                                for key in ["total", "passed", "failed", "skipped"]:
                                    platform_data["summary"][key] = platform_data["summary"].get(
                                        key, 0
                                    ) + data["summary"].get(key, 0)
                except Exception as e:
                    print(f"    ⚠️ Error reading {test_file}: {e}")

            if platform_data:
                combined["platforms"][platform_name] = platform_data
                combined["summary"]["platforms_tested"] += 1

                # Update totals
                if "summary" in platform_data:
                    for key in ["total_tests", "passed", "failed", "skipped"]:
                        combined["summary"][key] += platform_data["summary"].get(key.replace("_tests", ""), 0)
        else:
            print(f"  ⚠️ No test results for {platform_name}")

    # Write combined results
    output_file.parent.mkdir(parents=True, exist_ok=True)
    output_file.write_text(json.dumps(combined, indent=2))

    # Display summary
    print("\n📊 Combined test results:")
    s = combined["summary"]
    print(f"  Platforms tested: {s['platforms_tested']}")
    print(f"  Total tests: {s['total_tests']}")
    print(f"  Passed: {s['passed']}")
    print(f"  Failed: {s['failed']}")
    print(f"  Skipped: {s['skipped']}")


def generate_platform_metadata(platform_name: str, version: str, cache_hit: bool = False) -> None:
    """Generate platform-specific build metadata."""
    output_dir = Path("artifacts/metadata")
    output_dir.mkdir(parents=True, exist_ok=True)

    metadata = {
        "platform": platform_name,
        "version": version,
        "build": {
            "timestamp": datetime.now(UTC).isoformat(),
            "source": "cache" if cache_hit else "built",
            "cache_hit": cache_hit,
        },
        "runner": {
            "os": os.environ.get("RUNNER_OS", platform.system()),
            "arch": os.environ.get("RUNNER_ARCH", platform.machine()),
            "name": os.environ.get("RUNNER_NAME", "local"),
        },
        "github": {
            "job": os.environ.get("GITHUB_JOB", ""),
            "workflow": os.environ.get("GITHUB_WORKFLOW", ""),
            "run_id": os.environ.get("GITHUB_RUN_ID", ""),
            "run_number": os.environ.get("GITHUB_RUN_NUMBER", ""),
            "sha": os.environ.get("GITHUB_SHA", ""),
            "ref": os.environ.get("GITHUB_REF", ""),
        },
        "binaries": [],
    }

    # Check for binaries
    bin_dir = Path("helpers/bin")
    if bin_dir.exists():
        for binary_path in bin_dir.glob(f"*{platform_name}*"):
            if binary_path.is_file():
                binary_info = {
                    "name": binary_path.name,
                    "size": binary_path.stat().st_size,
                }

                # Determine component type
                if "go-launcher" in binary_path.name:
                    binary_info["component"] = "go-launcher"
                elif "go-builder" in binary_path.name:
                    binary_info["component"] = "go-builder"
                elif "rs-launcher" in binary_path.name:
                    binary_info["component"] = "rust-launcher"
                elif "rs-builder" in binary_path.name:
                    binary_info["component"] = "rust-builder"

                metadata["binaries"].append(binary_info)

    # Write metadata
    output_file = output_dir / f"platform-metadata-{platform_name}.json"
    output_file.write_text(json.dumps(metadata, indent=2))

    print(f"📊 Generated platform metadata for {platform_name}")
    print(f"   Version: {version}")
    print(f"   Source: {'cache' if cache_hit else 'built'}")
    print(f"   Binaries: {len(metadata['binaries'])}")
    print(f"   Output: {output_file}")


def main() -> None:
    """Main entry point."""
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    command = sys.argv[1]

    if command == "collect":
        output_dir = Path(sys.argv[2] if len(sys.argv) > 2 else "test-metadata")
        collect_test_metadata(output_dir)

    elif command == "combine":
        if len(sys.argv) < 3:
            print("Usage: test-metadata.py combine <input_dir> [output_file]")
            sys.exit(1)
        input_dir = Path(sys.argv[2])
        output_file = Path(sys.argv[3] if len(sys.argv) > 3 else "combined-test-report.json")
        combine_test_results(input_dir, output_file)

    elif command == "platform":
        if len(sys.argv) < 4:
            print("Usage: test-metadata.py platform <platform> <version> [cache_hit]")
            sys.exit(1)
        platform_name = sys.argv[2]
        version = sys.argv[3]
        cache_hit = sys.argv[4].lower() == "true" if len(sys.argv) > 4 else False
        generate_platform_metadata(platform_name, version, cache_hit)

    else:
        print(f"Unknown command: {command}")
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()

# 🌶️📦🔚
