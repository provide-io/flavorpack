#!/usr/bin/env python3
#
# flavor/cli.py
#
"The `flavor` command-line interface."

import importlib.metadata
from pathlib import Path

import click

from flavor.api import build_package_from_manifest, verify_package
from flavor.exceptions import BuildError
from flavor.packaging.keys import generate_key_pair

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
    """PSPF (Progressive Secure Package Format) Build Tool."""
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
    """Generates an ECDSA P-256 key pair for package integrity signing."""
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
@click.option(
    "--output",
    "output_path",
    type=click.Path(dir_okay=False, resolve_path=True),
    help="Custom output path for the package (defaults to dist/<name>.pspf).",
)
@click.option(
    "--launcher",
    type=click.Choice(["go", "rust"], case_sensitive=False),
    default=None,
    help="Launcher type to embed (defaults to 'rust' or value from FLAVOR_LAUNCHER env var).",
)
def package_command(
    pyproject_toml_path: str, output_path: str | None, launcher: str | None
) -> None:
    """Packages the application for one or more target platforms."""
    click.echo("🚀 Packaging application...")
    try:
        built_artifacts = build_package_from_manifest(
            Path(pyproject_toml_path),
            output_path=Path(output_path) if output_path else None,
            launcher_type=launcher,
        )
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
        result = verify_package(final_package_file)

        # Display results
        click.echo(f"\nPackage Format: {result['format']}")
        click.echo(f"Version: {result['version']}")
        click.echo(f"Launcher Size: {result['launcher_size'] / (1024 * 1024):.1f} MB")

        if result["format"] == "PSPF/2025":
            click.echo(f"Slot Count: {result['slot_count']}")
            if "package" in result:
                pkg = result["package"]
                click.echo(
                    f"Package: {pkg.get('name', 'unknown')} v{pkg.get('version', 'unknown')}"
                )
            if "slots" in result:
                click.echo("\nSlots:")
                for slot in result["slots"]:
                    click.echo(
                        f"  [{slot['index']}] {slot['name']}: {slot['size'] / 1024:.1f} KB"
                    )

        # Signature verification result
        if result["signature_valid"]:
            click.secho("\n✅ Signature verification successful", fg="green")
        else:
            click.secho("\n❌ Signature verification failed", fg="red")
            raise click.Abort()

    except Exception as e:
        click.secho(f"❌ Verification failed: {e}", fg="red", err=True)
        raise click.Abort() from e


@cli.command("clean")
def clean_command() -> None:
    """Removes cached Go binaries."""
    click.echo("Clean command not available - compiler moved to scraps")


main = cli


if __name__ == "__main__":
    cli()


# 🖱️ ⌨️ 🕹️


# 📦🍜🖥️🪄
