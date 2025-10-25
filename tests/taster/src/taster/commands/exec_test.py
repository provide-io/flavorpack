#!/usr/bin/env python3
"""Test direct execution vs script execution to diagnose permission issues."""

from pathlib import Path
import tempfile

import click
from provide.foundation.process import run

from flavor.helpers import HelperManager
from flavor.package import build_package_from_manifest


@click.command("exec-test")
@click.option("--verbose", "-v", is_flag=True, help="Verbose output")
def exec_test_command(verbose) -> None:
    """🔬 Test direct binary execution vs script execution."""

    click.secho("🔬 EXECUTION TEST", fg="cyan", bold=True)
    click.secho("=" * 60, fg="cyan")

    helper_manager = HelperManager()

    # Test 1: Direct binary execution
    click.secho("\n📌 Test 1: Direct binary execution", fg="yellow")
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_dir = Path(temp_dir)

        # Create a simple binary command (using Python directly)
        src_dir = temp_dir / "src" / "binary_test"
        src_dir.mkdir(parents=True)

        (src_dir / "__init__.py").write_text("")
        (src_dir / "__main__.py").write_text("""
import sys
print("✅ Binary execution successful!")
sys.exit(0)
""")

        manifest = temp_dir / "pyproject.toml"
        manifest.write_text("""
[project]
name = "binary-test"
version = "1.0.0"

[tool.flavor]
entry_point = "binary_test.__main__:main"
# Use Python binary directly, not a script
command = "{workenv}/bin/python3.11 -m binary_test"
""")

        try:
            # Build with Rust launcher
            rust_launcher = helper_manager.get_helper("flavor-rs-launcher")
            artifacts = build_package_from_manifest(
                manifest_path=manifest,
                launcher_bin=rust_launcher,
                key_seed="test123",
                show_progress=verbose,
            )

            package_path = artifacts[0]
            package_path.chmod(0o755)

            # Execute
            env = {"FLAVOR_EXEC_MODE": "exec"}
            if verbose:
                env["FLAVOR_LOG_LEVEL"] = "debug"

            result = run(
                [str(package_path)],
                capture_output=True,
                check=False,
                env=env,
                timeout=5,
            )

            if result.returncode == 0 and "Binary execution successful" in result.stdout:
                click.secho("  ✅ Binary execution: PASSED", fg="green")
            else:
                click.secho("  ❌ Binary execution: FAILED", fg="red")
                if verbose:
                    click.echo(f"    Exit code: {result.returncode}")
                    if result.stderr:
                        click.echo(f"    Error: {result.stderr[:200]}")
        except Exception as e:
            click.secho(f"  ❌ Binary execution: ERROR - {e}", fg="red")

    # Test 2: Script execution (with shebang)
    click.secho("\n📌 Test 2: Script execution (with shebang)", fg="yellow")
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_dir = Path(temp_dir)

        # Create a script-based command
        src_dir = temp_dir / "src" / "script_test"
        src_dir.mkdir(parents=True)

        (src_dir / "__init__.py").write_text("")
        (src_dir / "__main__.py").write_text("""
import sys
print("✅ Script execution successful!")
sys.exit(0)
""")

        manifest = temp_dir / "pyproject.toml"
        manifest.write_text("""
[project]
name = "script-test"
version = "1.0.0"

[tool.flavor]
entry_point = "script_test.__main__:main"
# Default command will use the entry point script
""")

        try:
            # Build with Rust launcher
            rust_launcher = helper_manager.get_helper("flavor-rs-launcher")
            artifacts = build_package_from_manifest(
                manifest_path=manifest,
                launcher_bin=rust_launcher,
                key_seed="test123",
                show_progress=verbose,
            )

            package_path = artifacts[0]
            package_path.chmod(0o755)

            # Execute with both modes
            for mode in ["spawn", "exec"]:
                click.echo(f"    Testing {mode} mode...")
                env = {"FLAVOR_EXEC_MODE": mode}
                if verbose:
                    env["FLAVOR_LOG_LEVEL"] = "debug"

                result = run(
                    [str(package_path)],
                    capture_output=True,
                    check=False,
                    env=env,
                    timeout=5,
                )

                if result.returncode == 0 and "Script execution successful" in result.stdout:
                    click.secho(f"      ✅ {mode} mode: PASSED", fg="green")
                else:
                    click.secho(f"      ❌ {mode} mode: FAILED", fg="red")
                    if verbose:
                        click.echo(f"        Exit code: {result.returncode}")
                        if result.stderr:
                            click.echo(f"        Error: {result.stderr[:200]}")
        except Exception as e:
            click.secho(f"  ❌ Script execution: ERROR - {e}", fg="red")

    # Test 3: Direct workenv access
    click.secho("\n📌 Test 3: Direct workenv command execution", fg="yellow")
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_dir = Path(temp_dir)

        # Create a test that directly runs from workenv
        src_dir = temp_dir / "src" / "direct_test"
        src_dir.mkdir(parents=True)

        (src_dir / "__init__.py").write_text("")
        (src_dir / "__main__.py").write_text("""
import sys
print("✅ Direct execution successful!")
sys.exit(0)
""")

        # Create custom script in the package

        manifest = temp_dir / "pyproject.toml"
        manifest.write_text("""
[project]
name = "direct-test"
version = "1.0.0"

[tool.flavor]
entry_point = "direct_test.__main__:main"
# Use a shell script directly
command = "{workenv}/test.sh"
setup_commands = [
    "echo '#!/bin/sh' > {workenv}/test.sh",
    "echo 'echo \"✅ Direct shell execution successful!\"' >> {workenv}/test.sh",
    "chmod +x {workenv}/test.sh"
]
""")

        try:
            # Build with Rust launcher
            rust_launcher = helper_manager.get_helper("flavor-rs-launcher")
            artifacts = build_package_from_manifest(
                manifest_path=manifest,
                launcher_bin=rust_launcher,
                key_seed="test123",
                show_progress=verbose,
            )

            package_path = artifacts[0]
            package_path.chmod(0o755)

            # Execute
            env = {"FLAVOR_EXEC_MODE": "exec"}
            if verbose:
                env["FLAVOR_LOG_LEVEL"] = "debug"

            result = run(
                [str(package_path)],
                capture_output=True,
                check=False,
                env=env,
                timeout=5,
            )

            if result.returncode == 0 and "Direct shell execution successful" in result.stdout:
                click.secho("  ✅ Direct workenv execution: PASSED", fg="green")
            else:
                click.secho("  ❌ Direct workenv execution: FAILED", fg="red")
                if verbose:
                    click.echo(f"    Exit code: {result.returncode}")
                    if result.stderr:
                        click.echo(f"    Error: {result.stderr[:200]}")
        except Exception as e:
            click.secho(f"  ❌ Direct workenv execution: ERROR - {e}", fg="red")

    click.secho("\n" + "=" * 60, fg="cyan")
    click.secho("🔬 EXECUTION TEST COMPLETE", fg="cyan", bold=True)


if __name__ == "__main__":
    exec_test_command()
