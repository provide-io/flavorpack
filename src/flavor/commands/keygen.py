#!/usr/bin/env python3
#
# flavor/commands/keygen.py
#
"""Key generation command for the flavor CLI."""

from pathlib import Path

import click

from flavor.exceptions import BuildError
from flavor.packaging.keys import generate_key_pair


@click.command("keygen")
@click.option(
    "--out-dir",
    default="keys",
    type=click.Path(file_okay=False, writable=True, resolve_path=True),
    help="Directory to save the Ed25519 key pair.",
)
def keygen_command(out_dir: str) -> None:
    """Generates an Ed25519 key pair for package integrity signing."""
    try:
        generate_key_pair(Path(out_dir))
        click.secho(
            f"✅ Package integrity key pair generated in '{out_dir}'.", fg="green"
        )
    except BuildError as e:
        click.secho(f"❌ Keygen failed: {e}", fg="red", err=True)
        raise click.Abort() from e
