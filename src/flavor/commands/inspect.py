#!/usr/bin/env python3
#
# flavor/commands/inspect.py
#
"""Inspect command for the flavor CLI."""

from pathlib import Path

import click


@click.command("inspect")
@click.argument(
    "package_file",
    type=click.Path(exists=True, dir_okay=False, resolve_path=True),
    required=True,
)
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["human", "json", "yaml"], case_sensitive=False),
    default="human",
    help="Output format (default: human)",
)
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    help="Show verbose output",
)
def inspect_command(package_file: str, output_format: str, verbose: bool) -> None:
    """Inspect a flavor package for detailed information."""
    from flavor.inspect import PackageInspector

    try:
        inspector = PackageInspector(Path(package_file))
        output = inspector.format_output(output_format, verbose=verbose)
        click.echo(output)
    except FileNotFoundError as e:
        click.secho(f"❌ Package not found: {e}", fg="red", err=True)
        raise click.Abort() from e
    except ValueError as e:
        click.secho(f"❌ Invalid package: {e}", fg="red", err=True)
        raise click.Abort() from e
    except Exception as e:
        click.secho(f"❌ Error inspecting package: {e}", fg="red", err=True)
        raise click.Abort() from e
