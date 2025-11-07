#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""Test launcher execution with a minimal Python package."""

import json
from pathlib import Path
import sys
import tempfile

import click
from provide.foundation.console import perr, pout
from provide.foundation.process import run

from flavor.helpers import HelperManager
from flavor.package import build_package_from_manifest


@click.command("launcher-test")
@click.option("--launcher", "-l", help="Specific launcher to test (e.g., flavor-rs-launcher)")
@click.option("--verbose", "-v", is_flag=True, help="Verbose output")
@click.option("--key-seed", default="test123", help="Key seed for deterministic builds")
@click.option(
    "--exec-mode",
    type=click.Choice(["exec", "spawn"]),
    default="exec",
    help="Execution mode",
)
def launcher_test_command(launcher, verbose, key_seed, exec_mode) -> None:
    """🚀 Test launcher execution with a minimal Python package."""

    helper_manager = HelperManager()

    # Get launcher
    if launcher:
        try:
            launcher_path = helper_manager.get_helper(launcher)
            launcher_name = launcher
        except FileNotFoundError:
            pout(f"❌ Launcher '{launcher}' not found", color="red")
            sys.exit(1)
    else:
        # Default to Rust launcher
        try:
            launcher_path = helper_manager.get_helper("flavor-rs-launcher")
            launcher_name = "flavor-rs-launcher"
        except FileNotFoundError:
            pout("❌ Rust launcher not found. Run 'flavor helpers build'.", color="red")
            sys.exit(1)

    pout(f"🚀 Testing launcher: {launcher_name}", color="cyan", bold=True)
    pout(f"   Path: {launcher_path}", color="cyan")

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_dir = Path(temp_dir)

        # Create minimal Python app
        src_dir = temp_dir / "src" / "test_app"
        src_dir.mkdir(parents=True)

        (src_dir / "__init__.py").write_text("")
        (src_dir / "__main__.py").write_text("""
import sys
sys.exit(0)
""")

        # Create minimal manifest
        manifest = temp_dir / "pyproject.toml"
        manifest.write_text("""
[project]
name = "launcher-test"
version = "1.0.0"

[tool.flavor]
entry_point = "test_app.__main__:main"
""")

        # Build package
        try:
            artifacts = build_package_from_manifest(
                manifest_path=manifest,
                launcher_bin=launcher_path,
                key_seed=key_seed,
                show_progress=verbose,
            )

            if not artifacts:
                pout("❌ Build failed: no artifacts produced", color="red")
                sys.exit(1)

            package_path = artifacts[0]

            # Make executable
            package_path.chmod(0o755)

            # Execute package
            pout("\n🏃 Executing package...", color="yellow")

            # Set environment for debugging
            env = {}
            if verbose:
                env["FLAVOR_LOG_LEVEL"] = "debug"
                env["RUST_BACKTRACE"] = "1"
            env["FLAVOR_EXEC_MODE"] = exec_mode

            result = run(
                [str(package_path)],
                capture_output=True,
                check=False,
                env=env,
                timeout=10,
            )

            # Display results
            pout("\n📊 Execution Results:", color="cyan", bold=True)
            pout(f"Exit code: {result.returncode}")

            if result.stdout:
                pout("\n📝 STDOUT:", color="green")
                pout(result.stdout)

            if result.stderr:
                pout("\n⚠️ STDERR:", color="yellow")
                pout(result.stderr)

            # Check success
            if result.returncode == 0 and "Launcher test successful" in result.stdout:
                # Additional verification
                if verbose:
                    pout("\n🔍 Package details:", color="cyan")
                    info_result = run(
                        [str(package_path), "info"],
                        capture_output=True,
                        check=False,
                        env={"FLAVOR_LAUNCHER_CLI": "true"},
                    )
                    if info_result.returncode == 0:
                        pout(info_result.stdout)
            else:
                pout("\n❌ LAUNCHER TEST FAILED!", color="red", bold=True)

                # Debug info
                if verbose:
                    pout("\n🐛 Debug Information:", color="yellow")
                    pout(f"Package exists: {package_path.exists()}")
                    pout(f"Package size: {package_path.stat().st_size if package_path.exists() else 'N/A'}")
                    pout(
                        f"Package permissions: {oct(package_path.stat().st_mode) if package_path.exists() else 'N/A'}"
                    )

                    # Try to read package metadata
                    try:
                        from flavor.psp.format_2025 import PSPFReader

                        with PSPFReader(package_path) as reader:
                            metadata = reader.read_metadata()
                            pout(f"Package metadata: {json.dumps(metadata, indent=2)[:500]}")
                    except Exception as e:
                        pout(f"Could not read metadata: {e}")

                sys.exit(1)

        except Exception as e:
            pout(f"\n❌ Error: {e}", color="red")
            if verbose:
                import traceback

                pout(traceback.format_exc())
            sys.exit(1)


if __name__ == "__main__":
    launcher_test_command()

# 🌶️📦🔚
