#!/usr/bin/env python3
#
# flavor/commands/package.py
#
"""Package command for the flavor CLI."""

from pathlib import Path
from typing import Any

import click

from flavor.exceptions import BuildError, PackagingError
from flavor.package import build_package_from_manifest, verify_package


def safe_echo(message: str, **kwargs: Any) -> None:
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
        message = message.replace("ℹ️", "[INFO]")  # noqa: RUF001
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

    _setup_workenv_base(workenv_base)

    try:
        built_artifacts = _build_package_artifacts(
            pyproject_toml_path,
            output_path,
            launcher_bin,
            builder_bin,
            strip,
            progress,
            quiet,
            private_key,
            public_key,
            key_seed,
        )

        _process_built_artifacts(built_artifacts, verify, strip, quiet)
        _show_final_results(built_artifacts, quiet)

    except (BuildError, PackagingError, click.UsageError) as e:
        _safe_click_secho(
            f"❌ Packaging Failed:\n{e}",
            "[ERROR] Packaging Failed:\n{e}",
            fg="red",
            err=True,
        )
        raise click.Abort() from e


def _setup_workenv_base(workenv_base: str | None) -> None:
    """Set workenv base if provided via flag."""
    if workenv_base:
        import os

        os.environ["FLAVOR_WORKENV_BASE"] = workenv_base


def _build_package_artifacts(
    pyproject_toml_path: str,
    output_path: str | None,
    launcher_bin: str | None,
    builder_bin: str | None,
    strip: bool,
    progress: bool,
    quiet: bool,
    private_key: str | None,
    public_key: str | None,
    key_seed: str | None,
) -> list[Path]:
    """Build package artifacts using the build_package_from_manifest function."""
    return build_package_from_manifest(
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


def _process_built_artifacts(
    built_artifacts: list[Path], verify: bool, strip: bool, quiet: bool
) -> None:
    """Process each built artifact with verification and optimization reporting."""
    for artifact in built_artifacts:
        if not quiet:
            _safe_click_secho(
                f"✅ Successfully built artifact at {artifact}",
                f"[OK] Successfully built artifact at {artifact}",
                fg="green",
            )

        if strip and not quiet:
            safe_echo("  📉 Binary optimized (debug symbols stripped)")

        if verify:
            _verify_artifact(artifact, quiet)


def _verify_artifact(artifact: Path, quiet: bool) -> None:
    """Verify a single artifact and handle the results."""
    if not quiet:
        safe_echo(f"🔍 Verifying {artifact}...")

    try:
        result = verify_package(artifact)
        if result["signature_valid"]:
            if not quiet:
                _safe_click_secho(
                    "  ✅ Package verified successfully",
                    "  [OK] Package verified successfully",
                    fg="green",
                )
        else:
            _safe_click_secho(
                "  ❌ Package verification failed",
                "  [ERROR] Package verification failed",
                fg="red",
            )
            raise BuildError(f"Verification failed for {artifact}")
    except Exception as e:
        _safe_click_secho(
            f"  ❌ Verification error: {e}",
            f"  [ERROR] Verification error: {e}",
            fg="red",
        )
        raise BuildError(f"Verification failed for {artifact}: {e}") from e


def _show_final_results(built_artifacts: list[Path], quiet: bool) -> None:
    """Show final results of the packaging process."""
    if built_artifacts:
        if not quiet:
            _safe_click_secho(
                "✅ All targets built successfully.",
                "[OK] All targets built successfully.",
                fg="green",
            )
    else:
        _safe_click_secho(
            "⚠️ No targets were specified or built.",
            "[WARN] No targets were specified or built.",
            fg="yellow",
        )


def _safe_click_secho(unicode_msg: str, fallback_msg: str, **kwargs: Any) -> None:
    """Safely echo with Unicode fallback handling."""
    try:
        click.secho(unicode_msg, **kwargs)
    except UnicodeEncodeError:
        click.secho(fallback_msg, **kwargs)
