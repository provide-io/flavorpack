#!/usr/bin/env python3
#
# flavor/commands/package.py
#
"""Package command for the flavor CLI."""

from pathlib import Path

import click

from flavor.api import build_package_from_manifest, verify_package
from flavor.exceptions import BuildError, PackagingError


def safe_echo(message: str, **kwargs) -> None:
    """Echo a message, handling Windows encoding issues."""
    try:
        click.echo(message, **kwargs)
    except UnicodeEncodeError:
        # On Windows, replace emojis with ASCII alternatives
        message = message.replace("🚀", "[LAUNCH]")
        message = message.replace("✅", "[OK]")
        message = message.replace("❌", "[ERROR]")
        message = message.replace("🔍", "[VERIFY]")
        message = message.replace("📦", "[PACKAGE]")
        message = message.replace("⚠️", "[WARN]")
        message = message.replace("ℹ️", "[INFO]")
        click.echo(message, **kwargs)


@click.command("pack")
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
    help="Custom output path for the package (defaults to dist/<name>.psp).",
)
@click.option(
    "--launcher-bin",
    type=click.Path(exists=True, dir_okay=False, resolve_path=True),
    help="Path to launcher binary to embed in the package.",
)
@click.option(
    "--builder-bin",
    type=click.Path(exists=True, dir_okay=False, resolve_path=True),
    help="Path to builder binary (overrides default builder selection).",
)
@click.option(
    "--verify/--no-verify",
    default=True,
    help="Verify the package after building (default: verify).",
)
@click.option(
    "--strip",
    is_flag=True,
    help="Strip debug symbols from launcher binary for size reduction.",
)
@click.option(
    "--progress",
    is_flag=True,
    help="Show progress bars during packaging.",
)
@click.option(
    "--quiet",
    is_flag=True,
    help="Suppress progress output.",
)
@click.option(
    "--private-key",
    type=click.Path(exists=True, dir_okay=False, resolve_path=True),
    help="Path to private key (PEM format) for signing.",
)
@click.option(
    "--public-key",
    type=click.Path(exists=True, dir_okay=False, resolve_path=True),
    help="Path to public key (PEM format, optional if private key provided).",
)
@click.option(
    "--key-seed",
    type=str,
    help="Seed for deterministic key generation.",
)
@click.option(
    "--workenv-base",
    type=click.Path(exists=True, file_okay=False, resolve_path=True),
    help="Base directory for {workenv} resolution (defaults to CWD).",
)
@click.option(
    "--output-format",
    type=click.Choice(["text", "json"], case_sensitive=False),
    help="Output format (or set FLAVOR_OUTPUT_FORMAT env var).",
)
@click.option(
    "--output-file",
    type=str,
    help="Output file path, STDOUT, or STDERR (or set FLAVOR_OUTPUT_FILE env var).",
)
def pack_command(
    pyproject_toml_path: str,
    output_path: str | None,
    launcher_bin: str | None,
    builder_bin: str | None,
    verify: bool,
    strip: bool,
    progress: bool,
    quiet: bool,
    private_key: str | None,
    public_key: str | None,
    key_seed: str | None,
    workenv_base: str | None,
    output_format: str | None,
    output_file: str | None,
) -> None:
    """Pack the application for one or more target platforms."""
    if not quiet:
        safe_echo("🚀 Packaging application...")

    # Set workenv base if provided via flag
    if workenv_base:
        import os

        os.environ["FLAVOR_WORKENV_BASE"] = workenv_base

    try:
        built_artifacts = build_package_from_manifest(
            Path(pyproject_toml_path),
            output_path=Path(output_path) if output_path else None,
            launcher_bin=Path(launcher_bin) if launcher_bin else None,
            builder_bin=Path(builder_bin) if builder_bin else None,
            strip_binaries=strip,
            show_progress=progress and not quiet,
            private_key_path=Path(private_key) if private_key else None,
            public_key_path=Path(public_key) if public_key else None,
            key_seed=key_seed,
        )
        for artifact in built_artifacts:
            if not quiet:
                try:
                    click.secho(
                        f"✅ Successfully built artifact at {artifact}",
                        fg="green",
                    )
                except UnicodeEncodeError:
                    click.secho(
                        f"[OK] Successfully built artifact at {artifact}",
                        fg="green",
                    )

            # Show optimization results if strip was used
            if strip and not quiet:
                safe_echo("  📉 Binary optimized (debug symbols stripped)")

            # Verify the package if requested
            if verify:
                if not quiet:
                    safe_echo(f"🔍 Verifying {artifact}...")
                try:
                    result = verify_package(artifact)
                    if result["signature_valid"]:
                        if not quiet:
                            try:
                                click.secho(
                                    "  ✅ Package verified successfully", fg="green"
                                )
                            except UnicodeEncodeError:
                                click.secho(
                                    "  [OK] Package verified successfully", fg="green"
                                )
                    else:
                        try:
                            click.secho("  ❌ Package verification failed", fg="red")
                        except UnicodeEncodeError:
                            click.secho(
                                "  [ERROR] Package verification failed", fg="red"
                            )
                        raise BuildError(f"Verification failed for {artifact}")
                except Exception as e:
                    try:
                        click.secho(f"  ❌ Verification error: {e}", fg="red")
                    except UnicodeEncodeError:
                        click.secho(f"  [ERROR] Verification error: {e}", fg="red")
                    raise BuildError(f"Verification failed for {artifact}: {e}") from e

        if built_artifacts:
            if not quiet:
                try:
                    click.secho("✅ All targets built successfully.", fg="green")
                except UnicodeEncodeError:
                    click.secho("[OK] All targets built successfully.", fg="green")
        else:
            try:
                click.secho("⚠️ No targets were specified or built.", fg="yellow")
            except UnicodeEncodeError:
                click.secho("[WARN] No targets were specified or built.", fg="yellow")

    except (BuildError, PackagingError, click.UsageError) as e:
        try:
            click.secho(f"❌ Packaging Failed:\n{e}", fg="red", err=True)
        except UnicodeEncodeError:
            click.secho(f"[ERROR] Packaging Failed:\n{e}", fg="red", err=True)
        raise click.Abort() from e
