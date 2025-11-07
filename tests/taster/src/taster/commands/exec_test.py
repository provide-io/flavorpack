#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""TODO: Add module docstring."""

#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""Test direct execution vs script execution to diagnose permission issues."""

from pathlib import Path
import tempfile

import click
from provide.foundation.console import perr, pout
from provide.foundation.process import run

from flavor.helpers import HelperManager
from flavor.package import build_package_from_manifest


@click.command("exec-test")
@click.option("--verbose", "-v", is_flag=True, help="Verbose output")
def exec_test_command(verbose) -> None:
    pout("=" * 60, color="cyan")

    helper_manager = HelperManager()

    # Test 1: Direct binary execution
    pout("\n📌 Test 1: Direct binary execution", color="yellow")
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_dir = Path(temp_dir)

        # Create a simple binary command (using Python directly)
        src_dir = temp_dir / "src" / "binary_test"
        src_dir.mkdir(parents=True)

        (src_dir / "__init__.py").write_text("")
        (src_dir / "__main__.py").write_text("""
import sys
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
                pass
            else:
                pout("  ❌ Binary execution: FAILED", color="red")
                if verbose:
                    pout(f"    Exit code: {result.returncode}")
                    if result.stderr:
                        pout(f"    Error: {result.stderr[:200]}")
        except Exception as e:
            pout(f"  ❌ Binary execution: ERROR - {e}", color="red")

    # Test 2: Script execution (with shebang)
    pout("\n📌 Test 2: Script execution (with shebang)", fg="yellow")
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_dir = Path(temp_dir)

        # Create a script-based command
        src_dir = temp_dir / "src" / "script_test"
        src_dir.mkdir(parents=True)

        (src_dir / "__init__.py").write_text("")
        (src_dir / "__main__.py").write_text("""
import sys
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
                pout(f"    Testing {mode} mode...")
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
                    pass
                else:
                    pout(f"      ❌ {mode} mode: FAILED", color="red")
                    if verbose:
                        pout(f"        Exit code: {result.returncode}")
                        if result.stderr:
                            pout(f"        Error: {result.stderr[:200]}")
        except Exception as e:
            pout(f"  ❌ Script execution: ERROR - {e}", color="red")

    # Test 3: Direct workenv access
    pout("\n📌 Test 3: Direct workenv command execution", color="yellow")
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_dir = Path(temp_dir)

        # Create a test that directly runs from workenv
        src_dir = temp_dir / "src" / "direct_test"
        src_dir.mkdir(parents=True)

        (src_dir / "__init__.py").write_text("")
        (src_dir / "__main__.py").write_text("""
import sys
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
                pass
            else:
                pout("  ❌ Direct workenv execution: FAILED", color="red")
                if verbose:
                    pout(f"    Exit code: {result.returncode}")
                    if result.stderr:
                        pout(f"    Error: {result.stderr[:200]}")
        except Exception as e:
            pout(f"  ❌ Direct workenv execution: ERROR - {e}", color="red")

    pout("\n" + "=" * 60, color="cyan")


if __name__ == "__main__":
    exec_test_command()

# 🌶️📦🔚
