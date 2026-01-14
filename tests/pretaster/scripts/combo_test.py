#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""Simple test script for builder/launcher combinations."""

from __future__ import annotations

import io
import os
from pathlib import Path
import subprocess
import sys
import tempfile

# Fix UTF-8 encoding on Windows (avoid cp1252 encoding errors with emojis)
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")


def handle_command(cmd: str, *args: str) -> int:  # noqa: C901 - command dispatcher
    """Handle different test commands."""
    if cmd == "info":
        print("  Package: pretaster-combination")
        print("  Version: 1.0.0")
        print(f"  Python: {sys.executable}")
        print(f"  Workenv: {os.getenv('FLAVOR_WORKENV', 'Not set')}")
        return 0
    elif cmd == "env":
        for key in sorted(os.environ.keys())[:10]:
            print(f"  {key}={os.environ[key][:50]}")
        print(f"  ... ({len(os.environ)} total)")
        return 0
    elif cmd == "argv":
        print("📝 Arguments received:")
        for i, arg in enumerate(args):
            print(f"  [{i}]: {arg}")
        return 0
    elif cmd == "echo":
        print(" ".join(args))
        return 0
    elif cmd == "file":
        # Simple file test
        if args and args[0] == "workenv-test":
            # Use cross-platform temp directory
            test_file = Path(tempfile.gettempdir()) / "workenv-test.txt"
            test_file.write_text("Test content")
            return 0
        print("❌ Unknown file command")
        return 1
    elif cmd == "exit":
        exit_code = int(args[0]) if args else 0
        print(f"🚪 Exiting with code {exit_code}")
        return exit_code
    elif cmd == "volatile-test":
        # Test volatile and init lifecycle slots
        workenv = Path(os.getenv("FLAVOR_WORKENV", "/tmp"))

        # Check if volatile slot exists (should always be extracted fresh)
        volatile_path = workenv / "volatile-data"
        if volatile_path.exists():
            with volatile_path.open() as file_obj:
                content = file_obj.read()
                print(f"     Content: {content[:50]}...")
        else:
            print(f"  ❌ Volatile slot NOT found: {volatile_path}")

        # Check if init slot exists (should be removed after setup)
        init_path = workenv / "init-setup"
        if init_path.exists():
            print(f"  ❌ Init slot still exists (should be removed): {init_path}")
            return 1
        else:
            pass

        return 0
    elif cmd == "manylinux-test":
        # Test that manylinux2014 platform tags are working
        print("=" * 60)

        # Test packages that require binary wheels
        test_packages = ["cryptography", "cffi"]

        with tempfile.TemporaryDirectory() as temp_dir:
            # Build the download command as PythonPackager would
            cmd = [
                "pip3",
                "download",
                "--dest",
                temp_dir,
                "--only-binary",
                ":all:",
                "--platform",
                "manylinux2014_x86_64",
                "--python-version",
                "3.11",
                *test_packages,
            ]

            print("Testing download command:")
            print(" ".join(cmd))
            print()

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)

            if result.returncode == 0:
                wheels = list(Path(temp_dir).glob("*.whl"))

                # Check each package
                for pkg in test_packages:
                    found = False
                    for wheel in wheels:
                        if pkg in wheel.name.lower() and "manylinux" in wheel.name:
                            found = True
                            break
                    if not found:
                        print(f"  ❌ {pkg}: Not found")
                        return 1

                return 0
            else:
                print(f"❌ Download failed: {result.stderr[:200]}")
                return 1
    else:
        print(f"❌ Unknown command: {cmd}")
        return 1


if __name__ == "__main__":
    args = sys.argv[1:]
    if not args:
        print("Usage: combo_test.py <command> [args...]")
        sys.exit(1)

    cmd = args[0]
    cmd_args = args[1:] if len(args) > 1 else []
    exit_code = handle_command(cmd, *cmd_args)
    sys.exit(exit_code)

# 🌶️📦🔚
