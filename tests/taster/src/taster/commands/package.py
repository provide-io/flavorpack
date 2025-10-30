# 
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""TODO: Add module docstring."""

# 
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""Package management commands using Flavor API"""

from pathlib import Path
import sys

import click


def _get_flavor_api():
    """Get the Flavor API."""
    try:
        import flavor.api as flavor_api

        return flavor_api
    except ImportError:
        click.echo(
            "Error: Flavor API not available. Ensure flavor package is installed.",
            err=True,
        )
        sys.exit(1)


@click.group("package")
def package_command() -> None:
    pass


@package_command.command("build")
@click.argument("manifest", type=click.Path(exists=True, path_type=Path), default="pyproject.toml")
@click.option("--output", "-o", type=click.Path(path_type=Path), help="Output path")
@click.option(
    "--launcher-bin",
    type=click.Path(exists=True, path_type=Path),
    help="Path to launcher binary",
)
@click.option("--strip", is_flag=True, help="Strip binaries")
@click.option("--key-seed", help="Seed for deterministic key generation")
def build(manifest, output, launcher_bin, strip, key_seed) -> None:
    """Build a PSPF package from manifest"""
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

        for path in paths:

    except Exception as e:
        click.echo(f"❌ Build failed: {e}", err=True)
        sys.exit(1)


@package_command.command("verify")
@click.argument("package", type=click.Path(exists=True, path_type=Path))
def verify(package) -> None:
    """Verify a PSPF package"""
    flavor_api = _get_flavor_api()

    try:
        result = flavor_api.verify_package(package)

        if isinstance(result, dict):
            for key, value in result.items():
                click.echo(f"  {key}: {value}")

    except Exception as e:
        click.echo(f"❌ Verification failed: {e}", err=True)
        sys.exit(1)


@package_command.command("generate-keys")
@click.option(
    "--output",
    "-o",
    type=click.Path(path_type=Path),
    default="keys",
    help="Output directory",
)
def generate_keys(output) -> None:
    """Generate signing keys"""
    flavor_api = _get_flavor_api()
    output_dir = Path(output)

    try:
        priv_key, pub_key = flavor_api.generate_keys(output_dir)
        click.echo(f"  Private: {priv_key}")
        click.echo(f"  Public: {pub_key}")

    except Exception as e:
        click.echo(f"❌ Key generation failed: {e}", err=True)
        sys.exit(1)


@package_command.command("clean-cache")
def clean_cache() -> None:
    """Clean Flavor's build cache"""
    flavor_api = _get_flavor_api()

    try:
        flavor_api.clean_cache()

    except Exception as e:
        click.echo(f"❌ Cache cleaning failed: {e}", err=True)
        sys.exit(1)


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
def test_json(builder_bin, launcher_bin) -> None:
    """Test JSON manifest support"""
    import json
    import subprocess
    import tempfile

    flavor_api = _get_flavor_api()

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)

        # Create a simple JSON manifest
        manifest_path = tmpdir / "test.json"
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
        manifest_path.write_text(json.dumps(manifest, indent=2))

        output_path = tmpdir / "test.psp"

        try:
            click.echo(f"  Builder: {builder_bin or 'default'}")
            click.echo(f"  Launcher: {launcher_bin or 'default'}")

            # Build the package
            paths = flavor_api.build_package_from_manifest(
                manifest_path=manifest_path,
                output_path=output_path,
                builder_bin=builder_bin,
                launcher_bin=launcher_bin,
                key_seed="test-json",
                show_progress=False,
            )

            if not paths or not output_path.exists():
                click.echo("❌ Package build failed - no output", err=True)
                sys.exit(1)


            # Make it executable and test it
            output_path.chmod(0o755)
            result = subprocess.run([str(output_path)], capture_output=True, text=True)

            if result.returncode == 0:
                if result.stdout:
                    click.echo(f"  Output: {result.stdout.strip()}")
            else:
                click.echo(
                    f"❌ Package execution failed with code {result.returncode}",
                    err=True,
                )
                if result.stderr:
                    click.echo(f"  Error: {result.stderr}", err=True)
                sys.exit(1)

        except Exception as e:
            click.echo(f"❌ JSON manifest test failed: {e}", err=True)
            sys.exit(1)

# 🌶️📦🔚
