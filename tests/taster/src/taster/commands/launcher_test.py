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
            click.secho(f"❌ Launcher '{launcher}' not found", fg="red")
            sys.exit(1)
    else:
        # Default to Rust launcher
        try:
            launcher_path = helper_manager.get_helper("flavor-rs-launcher")
            launcher_name = "flavor-rs-launcher"
        except FileNotFoundError:
            click.secho("❌ Rust launcher not found. Run 'flavor helpers build'.", fg="red")
            sys.exit(1)

    click.secho(f"🚀 Testing launcher: {launcher_name}", fg="cyan", bold=True)
    click.secho(f"   Path: {launcher_path}", fg="cyan")

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
                click.secho("❌ Build failed: no artifacts produced", fg="red")
                sys.exit(1)

            package_path = artifacts[0]

            # Make executable
            package_path.chmod(0o755)

            # Execute package
            click.secho("\n🏃 Executing package...", fg="yellow")

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
            click.secho("\n📊 Execution Results:", fg="cyan", bold=True)
            click.secho(f"Exit code: {result.returncode}")

            if result.stdout:
                click.secho("\n📝 STDOUT:", fg="green")
                click.echo(result.stdout)

            if result.stderr:
                click.secho("\n⚠️ STDERR:", fg="yellow")
                click.echo(result.stderr)

            # Check success
            if result.returncode == 0 and "Launcher test successful" in result.stdout:

                # Additional verification
                if verbose:
                    click.secho("\n🔍 Package details:", fg="cyan")
                    info_result = run(
                        [str(package_path), "info"],
                        capture_output=True,
                        check=False,
                        env={"FLAVOR_LAUNCHER_CLI": "true"},
                    )
                    if info_result.returncode == 0:
                        click.echo(info_result.stdout)
            else:
                click.secho("\n❌ LAUNCHER TEST FAILED!", fg="red", bold=True)

                # Debug info
                if verbose:
                    click.secho("\n🐛 Debug Information:", fg="yellow")
                    click.echo(f"Package exists: {package_path.exists()}")
                    click.echo(
                        f"Package size: {package_path.stat().st_size if package_path.exists() else 'N/A'}"
                    )
                    click.echo(
                        f"Package permissions: {oct(package_path.stat().st_mode) if package_path.exists() else 'N/A'}"
                    )

                    # Try to read package metadata
                    try:
                        from flavor.psp.format_2025 import PSPFReader

                        with PSPFReader(package_path) as reader:
                            metadata = reader.read_metadata()
                            click.echo(f"Package metadata: {json.dumps(metadata, indent=2)[:500]}")
                    except Exception as e:
                        click.echo(f"Could not read metadata: {e}")

                sys.exit(1)

        except Exception as e:
            click.secho(f"\n❌ Error: {e}", fg="red")
            if verbose:
                import traceback

                click.echo(traceback.format_exc())
            sys.exit(1)


if __name__ == "__main__":
    launcher_test_command()

# 🌶️📦🔚
