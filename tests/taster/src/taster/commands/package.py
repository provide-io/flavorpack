#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""Package management commands using the Flavor API."""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import tempfile
from typing import Any

import click
from provide.foundation.console import perr, pout


def _get_flavor_api() -> Any:
    """Import the Flavor API, exiting with a helpful message if unavailable."""
    try:
        import flavor.api as flavor_api
    except ImportError as exc:  # pragma: no cover - defensive check
        raise click.ClickException(
            "Flavor API not available. Install the flavor package before running packaging commands."
        ) from exc
    return flavor_api


@click.group("package")
def package_command() -> None:
    """Grouping for package management commands."""


@package_command.command("build")
@click.argument("manifest", type=click.Path(exists=True, path_type=Path), default="pyproject.toml")
@click.option("--output", "-o", type=click.Path(path_type=Path), help="Output path")
@click.option(
    "--launcher-bin",
    type=click.Path(exists=True, path_type=Path),
    help="Path to launcher binary",
)
@click.option("--strip", is_flag=True, help="Strip binaries before packaging")
@click.option("--key-seed", help="Seed for deterministic key generation")
def build(
    manifest: Path,
    output: Path | None,
    launcher_bin: Path | None,
    strip: bool,
    key_seed: str | None,
) -> None:
    """Build a PSPF package from a manifest file."""
    flavor_api = _get_flavor_api()
    try:
        paths = flavor_api.build_package_from_manifest(
            manifest_path=manifest,
            output_path=output,
            launcher_bin=launcher_bin,
            strip_binaries=strip,
            key_seed=key_seed,
            show_progress=True,
        )
        for built_path in paths or []:
            pout(f"  ✅ Wrote {built_path}")
    except Exception as exc:
        raise click.ClickException(f"Build failed: {exc}") from exc


@package_command.command("verify")
@click.argument("package", type=click.Path(exists=True, path_type=Path))
def verify(package: Path) -> None:
    """Verify a PSPF package."""
    flavor_api = _get_flavor_api()
    try:
        result = flavor_api.verify_package(package)
    except Exception as exc:
        raise click.ClickException(f"Verification failed: {exc}") from exc

    if isinstance(result, dict):
        for key, value in result.items():
            pout(f"  {key}: {value}")
    else:
        pout("Verification completed.")


@package_command.command("generate-keys")
@click.option(
    "--output",
    "-o",
    type=click.Path(path_type=Path),
    default="keys",
    help="Output directory",
)
def generate_keys(output: Path) -> None:
    """Generate signing keys."""
    flavor_api = _get_flavor_api()
    try:
        priv_key, pub_key = flavor_api.generate_keys(output)
        pout(f"  Private: {priv_key}")
        pout(f"  Public: {pub_key}")
    except Exception as exc:
        raise click.ClickException(f"Key generation failed: {exc}") from exc


@package_command.command("clean-cache")
def clean_cache() -> None:
    """Clean Flavor's build cache."""
    flavor_api = _get_flavor_api()
    try:
        flavor_api.clean_cache()
        pout("Cache cleaned.")
    except Exception as exc:
        raise click.ClickException(f"Cache cleaning failed: {exc}") from exc


@package_command.command("test-json")
@click.option(
    "--builder-bin",
    type=click.Path(exists=True, path_type=Path),
    help="Path to builder binary",
)
@click.option(
    "--launcher-bin",
    type=click.Path(exists=True, path_type=Path),
    help="Path to launcher binary",
)
def test_json(builder_bin: Path | None, launcher_bin: Path | None) -> None:
    """Exercise JSON manifest support by building and executing a sample package."""
    flavor_api = _get_flavor_api()
    with tempfile.TemporaryDirectory() as temp_dir:
        workdir = Path(temp_dir)
        manifest_path = workdir / "test.json"
        manifest = {
            "package": {
                "name": "json-test",
                "version": "1.0.0",
                "description": "Testing JSON manifest support",
            },
            "execution": {
                "command": "echo 'JSON manifest test successful!'",
                "environment": {"TEST_VAR": "json-manifest"},
            },
        }
        manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        output_path = workdir / "test.psp"

        pout(f"  Builder: {builder_bin or 'default'}")
        pout(f"  Launcher: {launcher_bin or 'default'}")

        try:
            paths = flavor_api.build_package_from_manifest(
                manifest_path=manifest_path,
                output_path=output_path,
                builder_bin=builder_bin,
                launcher_bin=launcher_bin,
                key_seed="test-json",
                show_progress=False,
            )
        except Exception as exc:
            raise click.ClickException(f"JSON manifest build failed: {exc}") from exc

        if not paths or not output_path.exists():
            raise click.ClickException("Package build failed - no output")

        output_path.chmod(0o755)
        result = subprocess.run([str(output_path)], capture_output=True, text=True, check=False)
        if result.returncode != 0:
            if result.stderr:
                perr(result.stderr)
            raise click.ClickException(f"Package execution failed with code {result.returncode}")

        if result.stdout:
            pout(f"  Output: {result.stdout.strip()}")


# 🌶️📦🔚
