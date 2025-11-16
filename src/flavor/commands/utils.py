#!/usr/bin/env python3
#
# flavor/commands/utils.py
#
"""Utility commands for the flavor CLI."""

from pathlib import Path

import click


@click.command("clean")
@click.option(
    "--all",
    is_flag=True,
    help="Clean both work environment and helpers",
)
@click.option(
    "--helpers",
    is_flag=True,
    help="Clean only helper binaries",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Show what would be removed without removing",
)
@click.option(
    "--yes",
    "-y",
    is_flag=True,
    help="Skip confirmation prompt",
)
def clean_command(all: bool, helpers: bool, dry_run: bool, yes: bool) -> None:
    """Clean work environment cache (default) or helpers."""
    from flavor.cache import CacheManager

    # Determine what to clean
    clean_workenv = not helpers or all
    clean_helpers = helpers or all

    if dry_run:
        click.echo("🔍 DRY RUN - Nothing will be removed\n")

    total_freed = 0

    # Clean workenv
    if clean_workenv:
        manager = CacheManager()
        cached = manager.list_cached()

        if cached:
            size = manager.get_cache_size()
            size_mb = size / (1024 * 1024)

            if dry_run:
                click.echo(
                    f"Would remove {len(cached)} cached packages ({size_mb:.1f} MB):"
                )
                for pkg in cached:
                    pkg_size_mb = pkg["size"] / (1024 * 1024)
                    name = pkg.get("name", pkg["id"])
                    click.echo(f"  - {name} ({pkg_size_mb:.1f} MB)")
            else:
                if not yes and not click.confirm(
                    f"Remove {len(cached)} cached packages ({size_mb:.1f} MB)?"
                ):
                    click.echo("Aborted.")
                    return

                removed = manager.clean()
                if removed:
                    click.secho(
                        f"✅ Removed {len(removed)} cached packages", fg="green"
                    )
                    total_freed += size

    # Clean helpers
    if clean_helpers:
        helper_dir = Path.home() / ".cache" / "flavor" / "bin"
        if helper_dir.exists():
            helpers_list = list(helper_dir.glob("flavor-*"))
            helpers_list = [
                h for h in helpers_list if h.suffix != ".d"
            ]  # Skip .d files

            if helpers_list:
                total_size = sum(h.stat().st_size for h in helpers_list)
                size_mb = total_size / (1024 * 1024)

                if dry_run:
                    click.echo(
                        f"\nWould remove {len(helpers_list)} helper binaries ({size_mb:.1f} MB):"
                    )
                    for helper in helpers_list:
                        h_size_mb = helper.stat().st_size / (1024 * 1024)
                        click.echo(f"  - {helper.name} ({h_size_mb:.1f} MB)")
                else:
                    if not yes and not click.confirm(
                        f"Remove {len(helpers_list)} helper binaries ({size_mb:.1f} MB)?"
                    ):
                        click.echo("Aborted.")
                        return

                    import shutil

                    shutil.rmtree(helper_dir)
                    click.secho(
                        f"✅ Removed {len(helpers_list)} helper binaries", fg="green"
                    )
                    total_freed += total_size

    if not dry_run and total_freed > 0:
        freed_mb = total_freed / (1024 * 1024)
        click.secho(f"\n💾 Total freed: {freed_mb:.1f} MB", fg="green")


@click.command("analyze-deps")
@click.option(
    "--manifest",
    "manifest_path",
    default="pyproject.toml",
    type=click.Path(exists=True, dir_okay=False, resolve_path=True),
    help="Path to the pyproject.toml manifest file.",
)
def analyze_deps_command(manifest_path: str) -> None:
    """Analyze package dependencies to help identify what can be optimized."""
    import tomllib

    from flavor.safe_optimization import DependencyAnalyzer

    manifest = Path(manifest_path)
    project_root = manifest.parent

    click.echo("🔍 Analyzing dependencies...")
    analyzer = DependencyAnalyzer()

    # Analyze imports in the project
    imports = analyzer.analyze_imports(project_root)

    # Read declared dependencies from pyproject.toml
    with manifest.open("rb") as f:
        pyproject = tomllib.load(f)

    dependencies = []
    if "project" in pyproject and "dependencies" in pyproject["project"]:
        dependencies = pyproject["project"]["dependencies"]

    # Extract package names from dependencies
    declared_packages = set()
    for dep in dependencies:
        # Handle formats like "package>=1.0" or "package[extra]"
        pkg_name = (
            dep.split("[")[0]
            .split(">=")[0]
            .split("==")[0]
            .split(">")[0]
            .split("<")[0]
            .strip()
        )
        declared_packages.add(pkg_name.lower())

    # Show analysis
    click.echo("\n📦 Declared Dependencies:")
    for pkg in sorted(declared_packages):
        click.echo(f"  • {pkg}")

    click.echo(f"\n📊 Imported Modules ({len(imports)} total):")
    # Group imports by standard library vs third-party
    stdlib = {
        "os",
        "sys",
        "time",
        "json",
        "pathlib",
        "typing",
        "datetime",
        "re",
        "collections",
        "itertools",
        "functools",
        "math",
        "random",
        "string",
        "io",
        "tempfile",
        "shutil",
        "subprocess",
        "platform",
        "hashlib",
    }

    third_party = []
    std_lib = []
    for module in sorted(imports.keys()):
        if module in stdlib:
            std_lib.append(module)
        else:
            third_party.append(module)

    if std_lib:
        click.echo("\n  Standard Library:")
        for module in std_lib[:10]:  # Show first 10
            list(imports[module])[:2]  # Show first 2 files
            click.echo(f"    • {module} (used in {len(imports[module])} files)")

    if third_party:
        click.echo("\n  Third-Party:")
        for module in third_party:
            click.echo(f"    • {module} (used in {len(imports[module])} files)")

    # Suggest optimization potential
    click.echo("\n💡 Optimization Potential:")
    click.echo("  Safe to remove:")
    click.echo("    • __pycache__ directories")
    click.echo("    • .pyc files")
    click.echo("    • test/ directories")
    click.echo("    • docs/ directories")
    click.echo("    • *.pyi type stub files")

    click.echo("\n  Use --optimize flag to apply these safe optimizations:")
    click.echo("    flavor package --optimize")
