#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""Package command for the flavor CLI."""

from __future__ import annotations

from pathlib import Path

import click
from provide.foundation.console import perr, pout

from flavor.console import get_command_logger
from flavor.exceptions import BuildError, PackagingError
from flavor.package import build_package_from_manifest, verify_package

# Get structured logger for this command
log = get_command_logger("pack")


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
    log.debug(
        "Starting package command",
        manifest=pyproject_toml_path,
        output_path=output_path,
        quiet=quiet,
    )

    if not quiet:
        pout("🚀 Packaging application...")

    _setup_workenv_base(workenv_base)

    try:
        if not quiet:
            pass

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

        if not quiet:
            pout("🔍 Processing and verifying artifacts...")

        _process_built_artifacts(built_artifacts, verify, strip, quiet)
        _show_final_results(built_artifacts, quiet)

        log.info("Packaging completed successfully", artifact_count=len(built_artifacts))

    except (BuildError, PackagingError, click.UsageError) as e:
        log.error("Packaging failed", error=str(e), manifest=pyproject_toml_path)
        perr(f"❌ Packaging Failed:\n{e}")
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


def _process_built_artifacts(built_artifacts: list[Path], verify: bool, strip: bool, quiet: bool) -> None:
    """Process each built artifact with verification and optimization reporting."""
    for artifact in built_artifacts:
        log.debug("Processing artifact", artifact=str(artifact), verify=verify, strip=strip)
        if not quiet:
            pass

        if strip and not quiet:
            pout("  📉 Binary optimized (debug symbols stripped)")

        if verify:
            _verify_artifact(artifact, quiet)


def _verify_artifact(artifact: Path, quiet: bool) -> None:
    """Verify a single artifact and handle the results."""
    log.debug("Verifying artifact", artifact=str(artifact))
    if not quiet:
        pout(f"🔍 Verifying {artifact}...")

    try:
        result = verify_package(artifact)
        if result["signature_valid"]:
            log.info("Package verified successfully", artifact=str(artifact))
            if not quiet:
                pass
        else:
            log.error("Package verification failed", artifact=str(artifact))
            perr("  ❌ Package verification failed")
            raise BuildError(f"Verification failed for {artifact}")
    except Exception as e:
        log.error("Verification error", artifact=str(artifact), error=str(e))
        perr(f"  ❌ Verification error: {e}")
        raise BuildError(f"Verification failed for {artifact}: {e}") from e


def _show_final_results(built_artifacts: list[Path], quiet: bool) -> None:
    """Show final results of the packaging process."""
    if built_artifacts:
        log.info("All targets built successfully", artifact_count=len(built_artifacts))
        if not quiet:
            pass
    else:
        log.warning("No targets were specified or built")
        pout("⚠️ No targets were specified or built.")


# 🌶️📦🔚
