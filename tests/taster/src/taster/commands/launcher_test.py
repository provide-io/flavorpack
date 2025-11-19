#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""Test launcher execution with a minimal Python package."""

from __future__ import annotations

import json
from pathlib import Path
import tempfile
from typing import Any

import click
from provide.foundation.console import pout
from provide.foundation.process import run

from flavor.helpers import HelperManager
from flavor.package import build_package_from_manifest

APP_MAIN = """\
import sys


def main() -> None:
    print("Launcher test successful")
    sys.exit(0)


if __name__ == "__main__":
    main()
"""

APP_MANIFEST = """\
[project]
name = "launcher-test"
version = "1.0.0"

[tool.flavor]
entry_point = "test_app.__main__:main"
"""


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
def launcher_test_command(
    launcher: str | None,
    verbose: bool,
    key_seed: str,
    exec_mode: str,
) -> None:
    """Test launcher execution with a minimal Python package."""
    helper_manager = HelperManager()

    try:
        launcher_path, launcher_name = _resolve_launcher(helper_manager, launcher)
        pout(f"🚀 Testing launcher: {launcher_name}", color="cyan", bold=True)
        pout(f"   Path: {launcher_path}", color="cyan")

        with tempfile.TemporaryDirectory() as temp_dir_str:
            temp_dir = Path(temp_dir_str)
            manifest = _create_test_project(temp_dir)
            package_path = _build_package(manifest, launcher_path, key_seed, verbose)
            result = _execute_package(package_path, exec_mode, verbose)
            _print_execution_results(result, verbose, package_path)
    except Exception as exc:
        if verbose:
            import traceback

            pout(traceback.format_exc())
        raise click.ClickException(str(exc)) from exc


def _resolve_launcher(helper_manager: HelperManager, requested: str | None) -> tuple[Path, str]:
    """Return the path and name of the launcher to test."""
    launcher_name = requested or "flavor-rs-launcher"
    try:
        launcher_path = helper_manager.get_helper(launcher_name)
    except FileNotFoundError as exc:
        instructions = "Run 'flavor helpers build' to compile helpers."
        raise click.ClickException(f"Launcher '{launcher_name}' not found. {instructions}") from exc
    return Path(launcher_path), launcher_name


def _create_test_project(temp_dir: Path) -> Path:
    """Create a minimal Python application and manifest."""
    src_dir = temp_dir / "src" / "test_app"
    src_dir.mkdir(parents=True, exist_ok=True)
    (src_dir / "__init__.py").write_text("", encoding="utf-8")
    (src_dir / "__main__.py").write_text(APP_MAIN, encoding="utf-8")

    manifest = temp_dir / "pyproject.toml"
    manifest.write_text(APP_MANIFEST, encoding="utf-8")
    return manifest


def _build_package(manifest: Path, launcher_path: Path, key_seed: str, verbose: bool) -> Path:
    """Invoke the builder to produce a PSPF package."""
    artifacts = build_package_from_manifest(
        manifest_path=manifest,
        launcher_bin=launcher_path,
        key_seed=key_seed,
        show_progress=verbose,
    )
    if not artifacts:
        raise click.ClickException("Build failed: no artifacts produced")

    package_path = Path(artifacts[0])
    package_path.chmod(0o755)
    return package_path


def _execute_package(package_path: Path, exec_mode: str, verbose: bool) -> Any:
    """Execute the package using the requested mode."""
    env = {"FLAVOR_EXEC_MODE": exec_mode}
    if verbose:
        env["FLAVOR_LOG_LEVEL"] = "debug"
        env["RUST_BACKTRACE"] = "1"

    return run(
        [str(package_path)],
        capture_output=True,
        check=False,
        env=env,
        timeout=10,
    )


def _print_execution_results(result: Any, verbose: bool, package_path: Path) -> None:
    """Display launcher execution output."""
    pout("\n📊 Execution Results:", color="cyan", bold=True)
    pout(f"Exit code: {result.returncode}")

    if result.stdout:
        pout("\n📝 STDOUT:", color="green")
        pout(result.stdout)

    if result.stderr:
        pout("\n⚠️ STDERR:", color="yellow")
        pout(result.stderr)

    stdout = result.stdout or ""
    if result.returncode == 0 and "Launcher test successful" in stdout:
        if verbose:
            _print_package_details(package_path)
        return

    _print_debug_info(package_path, verbose)
    raise click.ClickException("Launcher test failed")


def _print_package_details(package_path: Path) -> None:
    """Display launcher info command output when verbose."""
    pout("\n🔍 Package details:", color="cyan")
    info_result = run(
        [str(package_path), "info"],
        capture_output=True,
        check=False,
        env={"FLAVOR_LAUNCHER_CLI": "true"},
    )
    if info_result.returncode == 0 and info_result.stdout:
        pout(info_result.stdout)


def _print_debug_info(package_path: Path, verbose: bool) -> None:
    """Provide additional troubleshooting information."""
    if not verbose:
        return

    pout("\n🐛 Debug Information:", color="yellow")
    pout(f"Package exists: {package_path.exists()}")
    if package_path.exists():
        pout(f"Package size: {package_path.stat().st_size}")
        pout(f"Package permissions: {oct(package_path.stat().st_mode)}")
        try:
            from flavor.psp.format_2025 import PSPFReader

            with PSPFReader(package_path) as reader:
                metadata = reader.read_metadata()
                pout(f"Package metadata: {json.dumps(metadata, indent=2)[:500]}")
        except Exception as exc:
            pout(f"Could not read metadata: {exc}")


if __name__ == "__main__":
    launcher_test_command()


# 🌶️📦🔚
