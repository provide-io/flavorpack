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
            
            # Package metadata
            if "package" in result:
                pkg = result["package"]
                click.echo(
                    f"Package: {pkg.get('name', 'unknown')} v{pkg.get('version', 'unknown')}"
                )
            
            # Build metadata
            if "build" in result and result["build"]:
                build = result["build"]
                if "timestamp" in build:
                    click.echo(f"Built: {build['timestamp']}")
                if "builder_version" in build:
                    click.echo(f"Builder: {build['builder_version']}")
                if "launcher_type" in build:
                    click.echo(f"Launcher Type: {build['launcher_type']}")
            
            # Comprehensive slot information
            if "slots" in result:
                click.echo("\nSlots:")
                for slot in result["slots"]:
                    # Format size
                    size_str = f"{slot['size'] / 1024:.1f} KB" if slot['size'] < 1024 * 1024 else f"{slot['size'] / (1024 * 1024):.1f} MB"
                    
                    # Basic slot info
                    slot_line = f"  [{slot['index']}] {slot['id']}: {size_str}"
                    
                    # Add encoding if not raw
                    if slot.get('encoding') and slot['encoding'] != 'raw':
                        slot_line += f" [{slot['encoding']}]"
                    
                    click.echo(slot_line)
                    
                    # Additional metadata on separate lines
                    if slot.get('purpose'):
                        click.echo(f"      Purpose: {slot['purpose']}")
                    if slot.get('lifecycle'):
                        click.echo(f"      Lifecycle: {slot['lifecycle']}")
                    if slot.get('target'):
                        click.echo(f"      Target: {slot['target']}")
                    if slot.get('type'):
                        click.echo(f"      Type: {slot['type']}")
                    if slot.get('permissions'):
                        click.echo(f"      Permissions: {slot['permissions']}")
                    if slot.get('checksum'):
                        click.echo(f"      Checksum: {slot['checksum']}")

        # Signature verification result
        if result["signature_valid"]:
            click.secho("\n✅ Signature verification successful", fg="green")
        else:
            click.secho("\n❌ Signature verification failed", fg="red")
            raise click.Abort()

    except Exception as e:
        click.secho(f"❌ Verification failed: {e}", fg="red", err=True)
        raise click.Abort() from e
