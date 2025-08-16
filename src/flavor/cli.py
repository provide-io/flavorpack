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
def package_command(
    pyproject_toml_path: str, output_path: str | None, launcher: str | None, 
    verify: bool, strip: bool, progress: bool, quiet: bool,
    private_key: str | None, public_key: str | None, key_seed: str | None
) -> None:
    """Packages the application for one or more target platforms."""
    if not quiet:
        click.echo("🚀 Packaging application...")
    
    # Handle strip flag
    optimize_binaries = strip
    
    try:
        built_artifacts = build_package_from_manifest(
            Path(pyproject_toml_path),
            output_path=Path(output_path) if output_path else None,
            launcher_type=launcher,
            strip_binaries=strip,
            show_progress=progress and not quiet,
            private_key_path=Path(private_key) if private_key else None,
            public_key_path=Path(public_key) if public_key else None,
            key_seed=key_seed,
        )
        for artifact in built_artifacts:
            if not quiet:
                click.secho(
                    f"✅ Successfully built artifact at {artifact}",
                    fg="green",
                )
            
            # Show optimization results if strip was used
            if strip and not quiet:
                # Try to get optimization info from build result
                click.echo("  📉 Binary optimized (debug symbols stripped)")
            
            # Verify the package if requested
            if verify:
                if not quiet:
                    click.echo(f"🔍 Verifying {artifact}...")
                try:
                    result = verify_package(artifact)
                    if result["signature_valid"]:
                        if not quiet:
                            click.secho("  ✅ Package verified successfully", fg="green")
                    else:
                        click.secho("  ❌ Package verification failed", fg="red")
                        raise BuildError(f"Verification failed for {artifact}")
                except Exception as e:
                    click.secho(f"  ❌ Verification error: {e}", fg="red")
                    raise BuildError(f"Verification failed for {artifact}: {e}") from e
                    
        if built_artifacts:
            if not quiet:
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


@cli.command("inspect")
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
    "--verbose", "-v",
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


@cli.command("clean")
def clean_command() -> None:
    """Removes cached Go binaries."""
    click.echo("Clean command not available - compiler moved to scraps")


main = cli


if __name__ == "__main__":
    cli()


@cli.command("analyze-deps")
@click.option(
    "--manifest",
    "manifest_path",
    default="pyproject.toml",
    type=click.Path(exists=True, dir_okay=False, resolve_path=True),
    help="Path to the pyproject.toml manifest file.",
)
def analyze_deps_command(manifest_path: str) -> None:
    """Analyze package dependencies to help identify what can be optimized."""
    from flavor.safe_optimization import DependencyAnalyzer
    from pathlib import Path
    import tomllib
    
    manifest = Path(manifest_path)
    project_root = manifest.parent
    
    click.echo("🔍 Analyzing dependencies...")
    analyzer = DependencyAnalyzer()
    
    # Analyze imports in the project
    imports = analyzer.analyze_imports(project_root)
    
    # Read declared dependencies from pyproject.toml
    with open(manifest, "rb") as f:
        pyproject = tomllib.load(f)
    
    dependencies = []
    if "project" in pyproject and "dependencies" in pyproject["project"]:
        dependencies = pyproject["project"]["dependencies"]
    
    # Extract package names from dependencies
    declared_packages = set()
    for dep in dependencies:
        # Handle formats like "package>=1.0" or "package[extra]"
        pkg_name = dep.split("[")[0].split(">=")[0].split("==")[0].split(">")[0].split("<")[0].strip()
        declared_packages.add(pkg_name.lower())
    
    # Show analysis
    click.echo("\n📦 Declared Dependencies:")
    for pkg in sorted(declared_packages):
        click.echo(f"  • {pkg}")
    
    click.echo(f"\n📊 Imported Modules ({len(imports)} total):")
    # Group imports by standard library vs third-party
    stdlib = {"os", "sys", "time", "json", "pathlib", "typing", "datetime", "re", 
              "collections", "itertools", "functools", "math", "random", "string",
              "io", "tempfile", "shutil", "subprocess", "platform", "hashlib"}
    
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
            files = list(imports[module])[:2]  # Show first 2 files
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


@cli.command()
def list_helpers() -> None:
    """List available launcher and builder helpers."""
    from flavor.packaging.orchestrator import PackagingOrchestrator
    
    helpers = PackagingOrchestrator.discover_helpers()
    
    click.echo("🔍 Available Flavor Helpers")
    click.echo("=" * 40)
    
    if helpers["launchers"]:
        click.echo("\n📦 Launcher Helpers:")
        for launcher in sorted(helpers["launchers"]):
            click.echo(f"  • {launcher}")
    else:
        click.echo("\n⚠️  No launcher helpers found in helpers/bin")
    
    if helpers["builders"]:
        click.echo("\n🔨 Builder Helpers:")
        for builder in sorted(helpers["builders"]):
            click.echo(f"  • {builder}")
    else:
        click.echo("\n⚠️  No builder helpers found in helpers/bin")
    
    click.echo("\n💡 To use a specific launcher, add --launcher <type> to your package command")
    click.echo("   Example: flavor package --launcher go --manifest pyproject.toml")


@cli.group()
def cache() -> None:
    """Manage the Flavor package cache."""
    pass


@cache.command("list")
def cache_list() -> None:
    """List cached packages."""
    from flavor.cache import CacheManager
    
    manager = CacheManager()
    cached = manager.list_cached()
    
    if not cached:
        click.echo("No cached packages found.")
        return
    
    click.echo("🗂️  Cached Packages:")
    click.echo("=" * 60)
    
    for pkg in cached:
        size_mb = pkg["size"] / (1024 * 1024)
        name = pkg.get("name", pkg["id"])
        version = pkg.get("version", "")
        
        if version:
            click.echo(f"\n📦 {name} v{version}")
        else:
            click.echo(f"\n📦 {name}")
        
        click.echo(f"   ID: {pkg['id']}")
        click.echo(f"   Size: {size_mb:.1f} MB")
        
        import datetime
        modified = datetime.datetime.fromtimestamp(pkg["modified"])
        click.echo(f"   Modified: {modified.strftime('%Y-%m-%d %H:%M:%S')}")


@cache.command("info")
def cache_info() -> None:
    """Show cache information."""
    from flavor.cache import CacheManager, get_cache_dir
    
    manager = CacheManager()
    cached = manager.list_cached()
    total_size = manager.get_cache_size()
    
    click.echo("📊 Cache Information")
    click.echo("=" * 40)
    click.echo(f"Cache directory: {get_cache_dir()}")
    click.echo(f"Total size: {total_size / (1024 * 1024):.1f} MB")
    click.echo(f"Number of packages: {len(cached)}")


@cache.command("clean")
@click.option(
    "--older-than",
    type=int,
    help="Remove packages older than N days",
)
@click.option(
    "--yes", "-y",
    is_flag=True,
    help="Skip confirmation prompt",
)
def cache_clean(older_than: int | None, yes: bool) -> None:
    """Clean the cache."""
    from flavor.cache import CacheManager
    
    manager = CacheManager()
    
    if not yes:
        if older_than:
            prompt = f"Remove cached packages older than {older_than} days?"
        else:
            prompt = "Remove all cached packages?"
        
        if not click.confirm(prompt):
            click.echo("Aborted.")
            return
    
    # Clean incomplete extractions first
    incomplete = manager.clean_incomplete()
    if incomplete:
        click.echo(f"Removed {len(incomplete)} incomplete extractions")
    
    # Clean old packages
    removed = manager.clean(max_age_days=older_than)
    
    if removed:
        click.secho(f"✅ Cleaned {len(removed)} packages from cache", fg="green")
    else:
        click.echo("No packages to clean")


@cache.command("remove")
@click.argument("package_id")
@click.option(
    "--yes", "-y",
    is_flag=True,
    help="Skip confirmation prompt",
)
def cache_remove(package_id: str, yes: bool) -> None:
    """Remove a specific cached package."""
    from flavor.cache import CacheManager
    
    manager = CacheManager()
    
    if not yes:
        info = manager.get_info(package_id)
        if info:
            size_mb = info["size"] / (1024 * 1024)
            name = info.get("name", package_id)
            if not click.confirm(f"Remove {name} ({size_mb:.1f} MB)?"):
                click.echo("Aborted.")
                return
    
    if manager.remove(package_id):
        click.secho(f"✅ Removed package '{package_id}'", fg="green")
    else:
        click.secho(f"❌ Package '{package_id}' not found", fg="red")


@cli.group()
def helper() -> None:
    """Manage Flavor helper binaries (launchers and builders)."""
    pass


@helper.command("list")
@click.option(
    "--verbose", "-v",
    is_flag=True,
    help="Show detailed information",
)
def helper_list(verbose: bool) -> None:
    """List available helper binaries."""
    from flavor.helpers import HelperManager
    
    manager = HelperManager()
    helpers = manager.list_helpers()
    
    if not helpers["launchers"] and not helpers["builders"]:
        click.echo("No helpers found. Build them with: flavor helper build")
        return
    
    click.echo("🔧 Available Flavor Helpers")
    click.echo("=" * 60)
    
    if helpers["launchers"]:
        click.echo("\n📦 Launchers:")
        for launcher in sorted(helpers["launchers"], key=lambda h: h.name):
            size_mb = launcher.size / (1024 * 1024)
            click.echo(f"  • {launcher.name} ({launcher.language}, {size_mb:.1f} MB)")
            if verbose:
                if launcher.version:
                    click.echo(f"    Version: {launcher.version}")
                if launcher.checksum:
                    click.echo(f"    Checksum: {launcher.checksum}")
                if launcher.built_from:
                    click.echo(f"    Source: {launcher.built_from}")
    
    if helpers["builders"]:
        click.echo("\n🔨 Builders:")
        for builder in sorted(helpers["builders"], key=lambda h: h.name):
            size_mb = builder.size / (1024 * 1024)
            click.echo(f"  • {builder.name} ({builder.language}, {size_mb:.1f} MB)")
            if verbose:
                if builder.version:
                    click.echo(f"    Version: {builder.version}")
                if builder.checksum:
                    click.echo(f"    Checksum: {builder.checksum}")
                if builder.built_from:
                    click.echo(f"    Source: {builder.built_from}")


@helper.command("build")
@click.option(
    "--lang",
    type=click.Choice(["go", "rust", "all"], case_sensitive=False),
    default="all",
    help="Language to build helpers for (default: all)",
)
@click.option(
    "--force", "-f",
    is_flag=True,
    help="Force rebuild even if binaries exist",
)
def helper_build(lang: str, force: bool) -> None:
    """Build helper binaries from source."""
    from flavor.helpers import HelperManager
    
    manager = HelperManager()
    
    language = None if lang == "all" else lang
    
    click.echo(f"🔨 Building {lang} helpers...")
    
    built = manager.build_helpers(language=language, force=force)
    
    if built:
        click.secho(f"✅ Built {len(built)} helper(s):", fg="green")
        for path in built:
            size_mb = path.stat().st_size / (1024 * 1024)
            click.echo(f"  • {path.name} ({size_mb:.1f} MB)")
    else:
        click.secho("⚠️  No helpers were built", fg="yellow")
        click.echo("Make sure you have the required compilers installed:")
        click.echo("  • Go: go version")
        click.echo("  • Rust: cargo --version")


@helper.command("clean")
@click.option(
    "--lang",
    type=click.Choice(["go", "rust", "all"], case_sensitive=False),
    default="all",
    help="Language to clean helpers for (default: all)",
)
@click.option(
    "--yes", "-y",
    is_flag=True,
    help="Skip confirmation prompt",
)
def helper_clean(lang: str, yes: bool) -> None:
    """Remove built helper binaries."""
    from flavor.helpers import HelperManager
    
    manager = HelperManager()
    
    if not yes:
        if not click.confirm(f"Remove {lang} helper binaries?"):
            click.echo("Aborted.")
            return
    
    language = None if lang == "all" else lang
    
    removed = manager.clean_helpers(language=language)
    
    if removed:
        click.secho(f"✅ Removed {len(removed)} helper(s):", fg="green")
        for path in removed:
            click.echo(f"  • {path.name}")
    else:
        click.echo("No helpers to remove")


@helper.command("info")
@click.argument("name")
def helper_info(name: str) -> None:
    """Show detailed information about a specific helper."""
    from flavor.helpers import HelperManager
    
    manager = HelperManager()
    info = manager.get_helper_info(name)
    
    if not info:
        click.secho(f"❌ Helper '{name}' not found", fg="red")
        return
    
    click.echo(f"🔧 Helper Information: {info.name}")
    click.echo("=" * 60)
    click.echo(f"Type: {info.type}")
    click.echo(f"Language: {info.language}")
    click.echo(f"Path: {info.path}")
    click.echo(f"Size: {info.size / (1024 * 1024):.1f} MB")
    
    if info.version:
        click.echo(f"Version: {info.version}")
    
    if info.checksum:
        click.echo(f"Checksum: {info.checksum}")
    
    if info.built_from:
        click.echo(f"Source: {info.built_from}")
        if info.built_from.exists():
            click.echo("  ✅ Source directory exists")
        else:
            click.echo("  ⚠️  Source directory not found")
    
    # Check if executable
    if info.path.exists():
        import os
        if os.access(info.path, os.X_OK):
            click.echo("Status: ✅ Executable")
        else:
            click.echo("Status: ❌ Not executable")
    else:
        click.echo("Status: ❌ File not found")


@helper.command("test")
@click.option(
    "--lang",
    type=click.Choice(["go", "rust", "all"], case_sensitive=False),
    default="all",
    help="Language to test helpers for (default: all)",
)
def helper_test(lang: str) -> None:
    """Test helper binaries."""
    from flavor.helpers import HelperManager
    
    manager = HelperManager()
    
    language = None if lang == "all" else lang
    
    click.echo(f"🧪 Testing {lang} helpers...")
    
    results = manager.test_helpers(language=language)
    
    # Show results
    if results["passed"]:
        click.secho(f"✅ Passed: {len(results['passed'])}", fg="green")
        for name in results["passed"]:
            click.echo(f"  • {name}")
    
    if results["failed"]:
        click.secho(f"❌ Failed: {len(results['failed'])}", fg="red")
        for failure in results["failed"]:
            click.echo(f"  • {failure['name']}: {failure['error']}")
            if failure.get("stderr"):
                click.echo(f"    {failure['stderr']}")
    
    if results["skipped"]:
        click.echo(f"⏭️  Skipped: {len(results['skipped'])}")
        for name in results["skipped"]:
            click.echo(f"  • {name}")
    
    # Overall status
    if results["failed"]:
        click.secho("\n❌ Some tests failed", fg="red")
        raise click.Abort()
    elif results["passed"]:
        click.secho("\n✅ All tests passed", fg="green")
    else:
        click.echo("\n⚠️  No tests were run")


# 🖱️ ⌨️ 🕹️


# 📦🍜🖥️🪄
