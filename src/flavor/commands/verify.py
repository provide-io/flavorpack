#!/usr/bin/env python3
#
# flavor/commands/verify.py
#
"""Verify command for the flavor CLI."""

from pathlib import Path

import click

from flavor.api import verify_package


@click.command("verify")
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
