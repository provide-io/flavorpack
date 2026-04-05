#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""Test direct execution vs script execution to diagnose permission issues."""

from __future__ import annotations

from pathlib import Path
import shutil
import tempfile
from typing import Any

import click
from provide.foundation.console import pout
from provide.foundation.process import run

from flavor.cache import get_cache_dir
from flavor.config.defaults import ENV_CACHE_COMPAT, ENV_EXEC_MODE, ENV_LOG_LEVEL
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

[project.scripts]
binary-test = "binary_test.__main__:main"

[tool.flavor]
entry_point = "binary_test.__main__:main"
"""

SCRIPT_MANIFEST = """\
[project]
name = "script-test"
version = "1.0.0"

[project.scripts]
script-test = "script_test.__main__:main"

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

BOOTSTRAP_MANIFEST = """\
[project]
name = "bootstrap-test"
version = "1.0.0"
dependencies = []

[project.scripts]
bootstrap-test = "bootstrap_test.__main__:main"
"""


@click.command("exec-test")
@click.option("--verbose", "-v", is_flag=True, help="Verbose output")
def exec_test_command(verbose: bool) -> None:
    """Run a battery of execution-mode experiments."""
    pout("=" * 60, color="cyan")

    helper_manager = HelperManager()
    failures = 0
    failures += int(not _run_bootstrap_cache_test(helper_manager, verbose))
    failures += int(not _run_binary_test(helper_manager, verbose))
    failures += int(not _run_script_test(helper_manager, verbose))

    pout("\n" + "=" * 60, color="cyan")
    if failures:
        raise click.ClickException(f"{failures} execution test(s) failed")


def _run_binary_test(helper_manager: HelperManager, verbose: bool) -> bool:
    """Validate direct binary execution with exec mode."""
    pout("\n📌 Test 2: Direct binary execution", color="yellow")
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
                return True

            _report_failure("Binary execution", result, verbose)
            return False
    except Exception as exc:
        pout(f"  ❌ Binary execution: ERROR - {exc}", color="red")
        return False


def _run_bootstrap_cache_test(helper_manager: HelperManager, verbose: bool) -> bool:
    """Validate first-run bootstrap and second-run cache reuse."""
    pout("\n📌 Test 1: Python bootstrap and cache reuse", color="yellow")
    try:
        with tempfile.TemporaryDirectory() as temp_dir_str:
            temp_dir = Path(temp_dir_str)
            manifest = _prepare_bootstrap_project(temp_dir)

            # Workenv name is derived from PSP filename (not package_name+version).
            # build_package_from_manifest outputs bootstrap-test.psp so the launcher
            # creates {cache_dir}/bootstrap-test/.
            workenv_dir = get_cache_dir() / "bootstrap-test"
            if workenv_dir.exists():
                shutil.rmtree(workenv_dir, ignore_errors=True)

            package_path = _build_package(helper_manager, manifest, verbose)
            env = _build_env(mode="spawn", verbose=verbose)

            first_result = _execute_package(package_path, env)
            if first_result.returncode != 0 or "Bootstrap cache test successful" not in first_result.stdout:
                _report_failure("Bootstrap first run", first_result, verbose)
                return False

            marker_path = workenv_dir / "metadata" / "installed"
            wheels_dir = workenv_dir / "wheels"
            wheel_files = list(wheels_dir.glob("*.whl")) if wheels_dir.exists() else []
            if not marker_path.exists() or not wheel_files:
                pout("  ❌ Bootstrap first run: missing installed marker or wheel payloads", color="red")
                return False

            marker_mtime = marker_path.stat().st_mtime_ns

            second_result = _execute_package(package_path, env)
            if second_result.returncode != 0 or "Bootstrap cache test successful" not in second_result.stdout:
                _report_failure("Bootstrap second run", second_result, verbose)
                return False

            if marker_path.stat().st_mtime_ns != marker_mtime:
                pout("  ❌ Bootstrap cache reuse: setup marker changed on second run", color="red")
                return False

            pout("  ✅ Bootstrap and cache reuse succeeded", fg="green")
            return True
    except Exception as exc:
        pout(f"  ❌ Bootstrap cache test: ERROR - {exc}", color="red")
        return False


def _run_script_test(helper_manager: HelperManager, verbose: bool) -> bool:
    """Validate script execution in spawn and exec modes."""
    pout("\n📌 Test 3: Script execution (with shebang)", color="yellow")
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

            success = True
            for mode in ["spawn", "exec"]:
                pout(f"    Testing {mode} mode...")
                env = _build_env(mode=mode, verbose=verbose)
                result = _execute_package(package_path, env)
                if result.returncode == 0 and "Script execution successful" in result.stdout:
                    pout(f"      ✅ {mode} mode succeeded", fg="green")
                else:
                    _report_failure(f"{mode} mode", result, verbose)
                    success = False
            return success
    except Exception as exc:
        pout(f"  ❌ Script execution: ERROR - {exc}", color="red")
        return False


def _run_direct_workenv_test(helper_manager: HelperManager, verbose: bool) -> bool:
    """Validate executing a workenv-provided shell script."""
    pout("\n📌 Test 4: Direct workenv command execution", color="yellow")
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
                return True

            _report_failure("Direct workenv execution", result, verbose)
            return False
    except Exception as exc:
        pout(f"  ❌ Direct workenv execution: ERROR - {exc}", color="red")
        return False


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


def _prepare_bootstrap_project(temp_dir: Path) -> Path:
    """Write a minimal console-script project for bootstrap/cache testing."""
    src_dir = temp_dir / "src" / "bootstrap_test"
    src_dir.mkdir(parents=True, exist_ok=True)
    (src_dir / "__init__.py").write_text("", encoding="utf-8")
    (src_dir / "__main__.py").write_text(
        MODULE_TEMPLATE.format(message="Bootstrap cache test successful"),
        encoding="utf-8",
    )

    manifest = temp_dir / "pyproject.toml"
    manifest.write_text(BOOTSTRAP_MANIFEST, encoding="utf-8")
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
    import os

    env = {ENV_EXEC_MODE: mode}
    if verbose:
        env[ENV_LOG_LEVEL] = "debug"
    # Pass through essential vars so the inner PSP can bootstrap (locate cache
    # dir, find uv, write temp files). Without HOME the Rust launcher uses a
    # fallback path that differs from what Path.home() returns in the test.
    for var in ("HOME", "PATH", "USER", "TEMP", "TMP", "TMPDIR", ENV_CACHE_COMPAT):
        if val := os.environ.get(var):
            env[var] = val
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
