"""Verify PSPF package integrity"""

import json
import os
from pathlib import Path
import sys

import click


@click.command("verify")
@click.argument("package_path", required=False)
@click.option("--json", "output_json", is_flag=True, help="Output results as JSON")
@click.option("--output-file", "-o", type=click.Path(), help="Write output to file")
def verify_command(package_path, output_json, output_file) -> None:
    """🔍 Verify PSPF package integrity"""

    if not output_json:
        click.secho("=" * 60, fg="cyan")
        click.secho("🔍 PSPF PACKAGE VERIFICATION", fg="cyan", bold=True)
        click.secho("=" * 60, fg="cyan")

    # Determine package path
    if not package_path:
        # Try to use current executable
        package_path = sys.argv[0]
        if not package_path.endswith(".psp"):
            # Try FLAVOR_ORIGINAL_COMMAND
            package_path = os.environ.get("FLAVOR_ORIGINAL_COMMAND", package_path)

    package_file = Path(package_path)

    if not output_json:
        click.echo(f"\n📦 Package: {package_file}")

    # Result object for JSON output
    result_obj = {
        "package": str(package_file),
        "exists": package_file.exists(),
        "verification": None,
        "basic_info": None,
    }

    if not package_file.exists():
        result_obj["error"] = f"Package file not found: {package_file}"
        if output_json:
            output = json.dumps(result_obj, indent=2)
            if output_file:
                with open(output_file, "w") as f:
                    f.write(output)
            else:
                print(output)
        else:
            click.secho(f"❌ Package file not found: {package_file}", fg="red")
        return

    # Check if flavor module is available
    try:
        from flavor.psp.format_2025 import PSPFReader
        from flavor.verification import FlavorVerifier

        if not output_json:
            click.echo("✅ Flavor verification module available")
            click.echo("\n🔐 Verifying package integrity...")

        try:
            result = FlavorVerifier.verify_package(package_file)
            result_obj["verification"] = result

            if output_json:
                # JSON output
                output = json.dumps(result_obj, indent=2)
                if output_file:
                    with open(output_file, "w") as f:
                        f.write(output)
                else:
                    print(output)
            else:
                # Human-readable output
                click.secho("\n📋 Verification Results:", fg="green")
                click.echo(f"  Format: {result.get('format', 'unknown')}")
                click.echo(f"  Version: {result.get('version', 'unknown')}")
                click.echo(f"  Launcher Size: {result.get('launcher_size', 0) / 1024:.1f} KB")

                if "package" in result:
                    pkg = result["package"]
                    click.echo(f"  Package: {pkg.get('name', 'unknown')} v{pkg.get('version', 'unknown')}")

                if "slots" in result:
                    click.echo(f"  Slots: {len(result['slots'])}")

                # Signature verification
                if result.get("signature_valid"):
                    click.secho("\n✅ Signature verification: PASSED", fg="green")
                else:
                    click.secho("\n❌ Signature verification: FAILED", fg="red")

                # Additional checks
                click.secho("\n🔍 Additional Checks:", fg="yellow")

                # Check index checksum
                if "index_checksum_valid" in result:
                    if result["index_checksum_valid"]:
                        click.echo("  ✅ Index checksum valid")
                    else:
                        click.echo("  ❌ Index checksum invalid")

                # Check metadata
                if "metadata" in result:
                    click.echo("  ✅ Metadata present")
                else:
                    click.echo("  ⚠️ Metadata not found")

        except Exception as e:
            result_obj["error"] = str(e)
            if output_json:
                output = json.dumps(result_obj, indent=2)
                if output_file:
                    with open(output_file, "w") as f:
                        f.write(output)
                else:
                    print(output)
            else:
                click.secho(f"❌ Verification failed: {e}", fg="red")

    except ImportError:
        # Basic checks without flavor module
        size = package_file.stat().st_size
        basic_info = {
            "file_size_mb": size / (1024 * 1024),
            "readable": os.access(package_file, os.R_OK),
            "executable": os.access(package_file, os.X_OK),
            "magic_found": False,
        }

        # Check magic bytes
        try:
            with open(package_file, "rb") as f:
                data = f.read(1024 * 1024)  # Read first MB
                basic_info["magic_found"] = b"PSPF2025" in data
        except Exception as e:
            basic_info["read_error"] = str(e)

        result_obj["basic_info"] = basic_info
        result_obj["warning"] = "Flavor verification module not available, running basic checks only"

        if output_json:
            output = json.dumps(result_obj, indent=2)
            if output_file:
                with open(output_file, "w") as f:
                    f.write(output)
            else:
                print(output)
        else:
            click.secho("⚠️ Flavor verification module not available", fg="yellow")
            click.echo("  Running basic checks only...")
            click.echo("\n📊 Basic Information:")
            click.echo(f"  File Size: {basic_info['file_size_mb']:.2f} MB")
            click.echo(f"  Readable: {'Yes' if basic_info['readable'] else 'No'}")
            click.echo(f"  Executable: {'Yes' if basic_info['executable'] else 'No'}")

            if basic_info["magic_found"]:
                click.echo("  ✅ PSPF2025 magic found")
            else:
                click.echo("  ⚠️ PSPF2025 magic not found in first MB")

            if "read_error" in basic_info:
                click.echo(f"  ❌ Could not read file: {basic_info['read_error']}")
