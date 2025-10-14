"""Display package metadata including build info"""

import json
import os
from pathlib import Path

import click


@click.command("metadata")
def metadata_command() -> None:
    """📋 Display package metadata including build info"""
    click.secho("=" * 60, fg="cyan")
    click.secho("📋 PACKAGE METADATA", fg="cyan", bold=True)
    click.secho("=" * 60, fg="cyan")

    # Try to load metadata from workenv
    workenv = os.environ.get("FLAVOR_WORKENV")
    if not workenv:
        click.secho("❌ FLAVOR_WORKENV not set - not running in flavor pack", fg="red")
        return

    workenv_path = Path(workenv)

    # Look for psp.json in various locations
    possible_paths = [
        workenv_path / "metadata" / "psp.json",
        workenv_path / "psp.json",
        workenv_path / ".psp" / "psp.json",
    ]

    metadata = None
    for path in possible_paths:
        if path.exists():
            try:
                with open(path) as f:
                    metadata = json.load(f)
                click.echo(f"📄 Loaded metadata from: {path}")
                break
            except Exception as e:
                click.secho(f"⚠️ Failed to load {path}: {e}", fg="yellow")

    if not metadata:
        # Create mock metadata for testing
        metadata = {
            "format": "PSPF/2025",
            "package": {
                "name": "taster",
                "version": "1.0.0",
                "description": "Test package for flavor functionality",
            },
            "build": {
                "builder": "flavor/python-builder",
                "timestamp": "2025-01-01T00:00:00Z",
                "host": "test-host",
            },
            "execution": {
                "primary_slot": 0,
                "command": "python -m taster.cli",
                "environment": {},
            },
            "slots": [
                {"index": 0, "name": "payload", "purpose": "payload"},
                {"index": 1, "name": "runtime", "purpose": "runtime"},
                {"index": 2, "name": "tools", "purpose": "tool"},
            ],
        }
        click.secho("⚠️ Using mock metadata for demonstration", fg="yellow")

    # Display metadata sections
    if "package" in metadata:
        click.secho("\n📦 Package:", fg="green")
        pkg = metadata["package"]
        click.echo(f"  Name: {pkg.get('name', 'unknown')}")
        click.echo(f"  Version: {pkg.get('version', 'unknown')}")
        if "description" in pkg:
            click.echo(f"  Description: {pkg['description']}")

    if "build" in metadata:
        click.secho("\n🔨 Build Information:", fg="yellow")
        build = metadata["build"]
        click.echo(f"  Builder: {build.get('builder', 'unknown')}")
        click.echo(f"  Timestamp: {build.get('timestamp', 'unknown')}")
        click.echo(f"  Host: {build.get('host', 'unknown')}")

    if "slots" in metadata:
        click.secho("\n📁 Slots:", fg="blue")
        for slot in metadata["slots"]:
            click.echo(f"  [{slot['index']}] {slot['name']} ({slot.get('purpose', 'unknown')})")

    if "execution" in metadata:
        click.secho("\n⚙️ Execution:", fg="magenta")
        exec_info = metadata["execution"]
        click.echo(f"  Command: {exec_info.get('command', 'unknown')}")
        click.echo(f"  Primary Slot: {exec_info.get('primary_slot', 0)}")
        if exec_info.get("environment"):
            click.echo(f"  Environment: {len(exec_info['environment'])} variables")

    if "verification" in metadata:
        click.secho("\n🔐 Verification:", fg="cyan")
        verify = metadata["verification"]
        if "integrity_seal" in verify:
            seal = verify["integrity_seal"]
            click.echo(f"  Algorithm: {seal.get('algorithm', 'unknown')}")
            click.echo(f"  Required: {seal.get('required', False)}")

    # Show raw JSON if verbose
    if click.get_current_context().params.get("verbose"):
        click.secho("\n📄 Raw Metadata (JSON):", fg="white", dim=True)
        click.echo(json.dumps(metadata, indent=2))
