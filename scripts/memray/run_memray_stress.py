#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Memray stress test orchestrator.

Runs all five stress test scripts through memray profiler:
- memray_operations_stress.py
- memray_xor_stress.py
- memray_slot_descriptor_stress.py
- memray_builder_stress.py
- memray_reader_stress.py

Generates .bin files in memray-output/ and prints analysis commands.
"""

from pathlib import Path
import subprocess
import sys


def run_stress_tests() -> int:
    """
    Run all stress tests through memray profiler.

    Returns:
        0 on success, 1 on failure
    """
    root = Path(__file__).parent.parent.parent
    output_dir = root / "memray-output"
    output_dir.mkdir(exist_ok=True)

    scripts = [
        "scripts/memray/memray_operations_stress.py",
        "scripts/memray/memray_xor_stress.py",
        "scripts/memray/memray_slot_descriptor_stress.py",
        "scripts/memray/memray_builder_stress.py",
        "scripts/memray/memray_reader_stress.py",
    ]

    print("=" * 70)
    print("MEMRAY STRESS TEST ORCHESTRATOR")
    print("=" * 70)
    print()

    binfiles = []
    failed_scripts = []

    for script_path in scripts:
        script_name = Path(script_path).stem
        binfile = output_dir / f"{script_name}.bin"
        binfiles.append(binfile)

        print(f"Running {script_name}...")
        result = subprocess.run(
            ["uv", "run", "memray", "run", "--force", "-o", str(binfile), str(script_path)],
            cwd=str(root),
            capture_output=True,
            text=True,
        )

        if result.returncode == 0:
            print(f"  PASS: {binfile}")
        else:
            print(f"  FAIL: {result.stderr[:200]}")
            failed_scripts.append(script_path)

        print()

    if failed_scripts:
        print("=" * 70)
        print("FAILURES")
        print("=" * 70)
        for script in failed_scripts:
            print(f"  - {script}")
        return 1

    print("=" * 70)
    print("ANALYSIS COMMANDS (ready to paste)")
    print("=" * 70)
    print()

    for binfile in binfiles:
        if binfile.exists():
            print(f"memray flamegraph {binfile}")
            print(f"memray stats {binfile}")
            print()

    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"Output directory: {output_dir}")
    print(f"Binary files created: {len([b for b in binfiles if b.exists()])}/{len(binfiles)}")
    print()
    print("Next steps:")
    print("1. Review allocation patterns: memray stats <binfile>")
    print("2. Identify hotspots: memray flamegraph <binfile>")
    print("3. Run: uv run python scripts/memray/memray_analysis.py  (generates report + flamegraphs)")
    print()

    return 0


if __name__ == "__main__":
    sys.exit(run_stress_tests())
