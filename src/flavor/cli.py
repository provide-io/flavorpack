#!/usr/bin/env python3
#
# flavor/cli.py
#
"The `flavor` command-line interface."

import importlib.metadata
from pathlib import Path
import shutil
import subprocess

import click

from .api import build_package_from_manifest, verify_package
from .compiler import _get_cache_dir
from .exceptions import BuildError
from .packaging.keys import generate_key_pair

try:
    __version__ = importlib.metadata.version("flavor")
except importlib.metadata.PackageNotFoundError:
    __version__ = "0.0.0-dev"


@click.group(context_settings=dict(help_option_names=["-h", "--help"]))
@click.version_option(
    __version__,
    "-V",
    "--version",
    prog_name="flavor",
    message="%(prog)s version %(version)s",
)
@click.option(
    "--log-level",
    type=click.Choice(
        ["trace", "debug", "info", "warning", "error"],
        case_sensitive=False,
    ),
    default="info",
    help="Set logging level (default: info).",
)
@click.pass_context
def cli(ctx: click.Context, log_level: str) -> None:
    """Pyvider Secure Packaging Format (flavor) Build Tool."""
    ctx.ensure_object(dict)
    ctx.obj["log_level"] = log_level

    from pyvider.telemetry import LoggingConfig, TelemetryConfig, setup_telemetry

    telemetry_log_level = log_level.upper()

    config = TelemetryConfig(
        service_name="flavor",
        logging=LoggingConfig(
            default_level=telemetry_log_level,  # type: ignore
        ),
    )
    setup_telemetry(config)


@cli.command()
@click.option(
    "--out-dir",
    default="keys",
    type=click.Path(file_okay=False, writable=True, resolve_path=True),
    help="Directory to save the ECDSA key pair.",
)
def keygen(out_dir: str) -> None:
    """Generates an ECDSA P-256 key pair for flavor package integrity signing."""
    try:
        generate_key_pair(Path(out_dir))
        click.secho(
            f"✅ Package integrity key pair generated in '{out_dir}'.", fg="green"
        )
    except BuildError as e:
        click.secho(f"❌ Keygen failed: {e}", fg="red", err=True)
        raise click.Abort() from e


@cli.command("package")
@click.option(
    "--manifest",
    "pyproject_toml_path",
    default="pyproject.toml",
    type=click.Path(exists=True, dir_okay=False, resolve_path=True),
    help="Path to the pyproject.toml manifest file.",
)
def package_command(pyproject_toml_path: str) -> None:
    """Packages the provider for one or more target platforms."""
    click.echo("🚀 Packaging provider...")
    try:
        built_artifacts = build_package_from_manifest(Path(pyproject_toml_path))
        for artifact in built_artifacts:
            click.secho(
                f"✅ Successfully built artifact at {artifact}",
                fg="green",
            )
        if built_artifacts:
            click.secho("✅ All targets built successfully.", fg="green")
        else:
            click.secho("⚠️ No targets were specified or built.", fg="yellow")

    except (BuildError, click.UsageError) as e:
        click.secho(f"❌ Packaging Failed:\n{e}", fg="red", err=True)
        raise click.Abort() from e


@cli.command("verify")
@click.argument(
    "package_file",
    type=click.Path(exists=True, dir_okay=False, resolve_path=True),
    required=True,
)
def verify_command(package_file: str) -> None:
    """Verifies a flavor package."""
    final_package_file = Path(package_file)
    click.echo(f"🔍 Verifying package '{final_package_file}'...")
    try:
        verify_package(final_package_file)
        click.secho("✅ Go-based cryptographic verification successful.", fg="green")
    except (BuildError, subprocess.CalledProcessError) as e:
        stderr_info = (
            f"  Stderr: {e.stderr.strip()}" if hasattr(e, "stderr") and e.stderr else ""
        )
        click.secho(
            f"❌ Go-based verification failed: {e}{stderr_info}", fg="red", err=True
        )
        raise click.Abort() from e


@cli.command("clean")
def clean_command() -> None:
    """Removes cached Go binaries."""
    click.echo("🧹 Cleaning cached Go binaries...")
    cache_dir = _get_cache_dir()
    bin_dir = cache_dir / "bin"
    if bin_dir.exists():
        shutil.rmtree(bin_dir, ignore_errors=True)
        click.secho(f"✅ Removed cache directory: {bin_dir}", fg="green")
    else:
        click.secho("Info: Cache directory not found, nothing to clean.", fg="yellow")


main = cli
# 🖱️ ⌨️ 🕹️


# 📦🍜🖥️🪄
