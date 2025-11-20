#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""Test direct execution vs script execution to diagnose permission issues."""

from __future__ import annotations

from pathlib import Path
import tempfile
from typing import Any

import click
from provide.foundation.console import pout
from provide.foundation.process import run

from flavor.helpers import HelperManager
from flavor.package import build_package_from_manifest

MODULE_TEMPLATE = """\
import sys


def main() -> None:
    print("{message}")
    sys.exit(0)


if __name__ == "__main__":
    main()
"""

BINARY_MANIFEST = """\
[project]
name = "binary-test"
version = "1.0.0"

[tool.flavor]
entry_point = "binary_test.__main__:main"
command = "{workenv}/bin/python3.11 -m binary_test"
"""

SCRIPT_MANIFEST = """\
[project]
name = "script-test"
version = "1.0.0"

[tool.flavor]
entry_point = "script_test.__main__:main"
"""

DIRECT_MANIFEST = """\
[project]
name = "direct-test"
version = "1.0.0"

[tool.flavor]
entry_point = "direct_test.__main__:main"
command = "{workenv}/test.sh"
setup_commands = [
    "echo '#!/bin/sh' > {workenv}/test.sh",
    "chmod +x {workenv}/test.sh"
]
"""


@click.command("exec-test")
@click.option("--verbose", "-v", is_flag=True, help="Verbose output")
def exec_test_command(verbose: bool) -> None:
    """Run a battery of execution-mode experiments."""
    pout("=" * 60, color="cyan")

    helper_manager = HelperManager()
    _run_binary_test(helper_manager, verbose)
    _run_script_test(helper_manager, verbose)
    _run_direct_workenv_test(helper_manager, verbose)

    pout("\n" + "=" * 60, color="cyan")


def _run_binary_test(helper_manager: HelperManager, verbose: bool) -> None:
    """Validate direct binary execution with exec mode."""
    pout("\n📌 Test 1: Direct binary execution", color="yellow")
    try:
        with tempfile.TemporaryDirectory() as temp_dir_str:
            temp_dir = Path(temp_dir_str)
            manifest = _prepare_project(
                temp_dir,
                "binary_test",
                BINARY_MANIFEST,
                success_message="Binary execution successful",
            )
            package_path = _build_package(helper_manager, manifest, verbose)
            env = _build_env(mode="exec", verbose=verbose)
            result = _execute_package(package_path, env)

            if result.returncode == 0 and "Binary execution successful" in result.stdout:
                pout("  ✅ Binary execution succeeded", fg="green")
            else:
                _report_failure("Binary execution", result, verbose)
    except Exception as exc:
        pout(f"  ❌ Binary execution: ERROR - {exc}", color="red")


def _run_script_test(helper_manager: HelperManager, verbose: bool) -> None:
    """Validate script execution in spawn and exec modes."""
    pout("\n📌 Test 2: Script execution (with shebang)", fg="yellow")
    try:
        with tempfile.TemporaryDirectory() as temp_dir_str:
            temp_dir = Path(temp_dir_str)
            manifest = _prepare_project(
                temp_dir,
                "script_test",
                SCRIPT_MANIFEST,
                success_message="Script execution successful",
            )
            package_path = _build_package(helper_manager, manifest, verbose)

            for mode in ["spawn", "exec"]:
                pout(f"    Testing {mode} mode...")
                env = _build_env(mode=mode, verbose=verbose)
                result = _execute_package(package_path, env)
                if result.returncode == 0 and "Script execution successful" in result.stdout:
                    pout(f"      ✅ {mode} mode succeeded", fg="green")
                else:
                    _report_failure(f"{mode} mode", result, verbose)
    except Exception as exc:
        pout(f"  ❌ Script execution: ERROR - {exc}", color="red")


def _run_direct_workenv_test(helper_manager: HelperManager, verbose: bool) -> None:
    """Validate executing a workenv-provided shell script."""
    pout("\n📌 Test 3: Direct workenv command execution", color="yellow")
    try:
        with tempfile.TemporaryDirectory() as temp_dir_str:
            temp_dir = Path(temp_dir_str)
            manifest = _prepare_project(
                temp_dir,
                "direct_test",
                DIRECT_MANIFEST,
                success_message="Direct shell execution successful",
            )
            package_path = _build_package(helper_manager, manifest, verbose)
            env = _build_env(mode="exec", verbose=verbose)
            result = _execute_package(package_path, env)

            if result.returncode == 0 and "Direct shell execution successful" in result.stdout:
                pout("  ✅ Direct workenv execution succeeded", fg="green")
            else:
                _report_failure("Direct workenv execution", result, verbose)
    except Exception as exc:
        pout(f"  ❌ Direct workenv execution: ERROR - {exc}", color="red")


def _prepare_project(
    temp_dir: Path,
    package_name: str,
    manifest_content: str,
    *,
    success_message: str,
) -> Path:
    """Write a minimal Python package and corresponding manifest."""
    src_dir = temp_dir / "src" / package_name
    src_dir.mkdir(parents=True, exist_ok=True)
    (src_dir / "__init__.py").write_text("", encoding="utf-8")
    module_body = MODULE_TEMPLATE.format(message=success_message)
    (src_dir / "__main__.py").write_text(module_body, encoding="utf-8")

    manifest = temp_dir / "pyproject.toml"
    manifest.write_text(manifest_content, encoding="utf-8")
    return manifest


def _build_package(helper_manager: HelperManager, manifest: Path, verbose: bool) -> Path:
    """Build a PSPF package using the Rust launcher."""
    rust_launcher = helper_manager.get_helper("flavor-rs-launcher")
    artifacts = build_package_from_manifest(
        manifest_path=manifest,
        launcher_bin=rust_launcher,
        key_seed="test123",
        show_progress=verbose,
    )

    package_path = Path(artifacts[0])
    package_path.chmod(0o755)
    return package_path


def _build_env(mode: str, verbose: bool) -> dict[str, str]:
    """Create an environment dictionary for launcher execution."""
    env = {"FLAVOR_EXEC_MODE": mode}
    if verbose:
        env["FLAVOR_LOG_LEVEL"] = "debug"
    return env


def _execute_package(package_path: Path, env: dict[str, str]) -> Any:
    """Run a package and capture the result."""
    return run(
        [str(package_path)],
        capture_output=True,
        check=False,
        env=env,
        timeout=5,
    )


def _report_failure(case: str, result: Any, verbose: bool) -> None:
    """Emit detailed diagnostics for a failed invocation."""
    pout(f"  ❌ {case}: FAILED", color="red")
    if not verbose:
        return

    pout(f"    Exit code: {result.returncode}")
    stderr = getattr(result, "stderr", "")
    if stderr:
        pout(f"    Error: {stderr[:200]}")


if __name__ == "__main__":
    exec_test_command()


# 🌶️📦🔚
