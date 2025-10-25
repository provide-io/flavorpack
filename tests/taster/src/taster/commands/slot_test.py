#!/usr/bin/env python3
"""Test slot substitution patterns in commands."""

import json
from pathlib import Path
import tempfile

import click

from flavor.helpers import HelperManager
from flavor.package import build_package_from_manifest


@click.command("slot-test")
@click.option("--verbose", "-v", is_flag=True, help="Verbose output")
@click.option("--json-output", is_flag=True, help="Output results as JSON")
def slot_test_command(verbose, json_output) -> None:
    """🎰 Test {slot:N} substitution patterns."""

    if not json_output:
        click.secho("🎰 SLOT SUBSTITUTION TEST", fg="cyan", bold=True)
        click.secho("=" * 60, fg="cyan")

    helper_manager = HelperManager()

    # Test cases for different slot patterns
    test_cases = [
        {
            "name": "single_slot",
            "pattern": "{slot:0}",
            "command": "/usr/bin/python3 {slot:0}",
            "description": "Single slot substitution",
        },
        {
            "name": "slot_with_path",
            "pattern": "{slot:0}/bin/python",
            "command": "{slot:0}/bin/python --version",
            "description": "Slot with path suffix",
        },
        {
            "name": "multiple_slots",
            "pattern": "{slot:0} {slot:1}",
            "command": "/usr/bin/python3 {slot:0} --config {slot:1}",
            "description": "Multiple slot substitution",
        },
        {
            "name": "mixed_text",
            "pattern": "python {slot:0} --config {slot:1}",
            "command": "python {slot:0} --config {slot:1} --verbose",
            "description": "Mixed text and slots",
        },
    ]

    results = []

    for test_case in test_cases:
        if not json_output:
            click.secho(f"\n📌 Testing: {test_case['description']}", fg="yellow")
            click.secho(f"   Pattern: {test_case['pattern']}", fg="white")
            click.secho(f"   Command: {test_case['command']}", fg="white")

        # Create a test package with the slot pattern
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_dir = Path(temp_dir)

            # Create test scripts for slots
            slot0_script = temp_dir / "slot0.py"
            slot0_script.write_text("""
import sys
print(f"Slot 0 executed: {sys.argv}")
""")

            slot1_config = temp_dir / "config.json"
            slot1_config.write_text('{"test": "config"}')

            # Create manifest with slot substitution command
            manifest = temp_dir / "pyproject.toml"
            manifest.write_text(f"""
[project]
name = "slot-test-{test_case["name"]}"
version = "1.0.0"

[tool.flavor]
entry_point = "echo 'Entry point'"

[tool.flavor.execution]
command = "{test_case["command"]}"
primary_slot = 0

[tool.flavor.slots]
[[tool.flavor.slots.items]]
id = "slot0"
source = "{slot0_script}"
target = "slot0.py"

[[tool.flavor.slots.items]]
id = "slot1"
source = "{slot1_config}"
target = "config.json"
""")

            try:
                # Try to build package
                launcher_path = helper_manager.get_helper("flavor-rs-launcher")

                result = build_package_from_manifest(
                    manifest_path=manifest,
                    output_dir=temp_dir,
                    launcher_bin=launcher_path,
                    key_seed="test123",
                )

                # Check if slot patterns are properly handled
                if result.success:
                    status = "✅ Passed"
                    error = None
                else:
                    status = "❌ Failed"
                    error = str(result.error) if hasattr(result, "error") else "Unknown error"

            except Exception as e:
                status = "❌ Failed"
                error = str(e)

        result = {
            "name": test_case["name"],
            "pattern": test_case["pattern"],
            "command": test_case["command"],
            "description": test_case["description"],
            "status": status,
            "error": error,
        }
        results.append(result)

        if not json_output and verbose and error:
            click.secho(f"   Error: {error}", fg="red")

    # Output results
    if json_output:
        output = {
            "test": "slot_substitution",
            "results": results,
            "summary": {
                "total": len(results),
                "passed": len([r for r in results if "✅" in r["status"]]),
                "failed": len([r for r in results if "❌" in r["status"]]),
            },
        }
        click.echo(json.dumps(output, indent=2))
    else:
        # Summary
        click.secho("\n📊 Results Summary:", fg="cyan", bold=True)
        click.secho("─" * 40, fg="cyan")

        for result in results:
            status_color = "green" if "✅" in result["status"] else "red"
            click.secho(f"  {result['status']} {result['description']}", fg=status_color)

        passed = len([r for r in results if "✅" in r["status"]])
        total = len(results)

        click.secho("\n" + "─" * 40, fg="cyan")
        if passed == total:
            click.secho(f"✅ All {total} tests passed!", fg="green", bold=True)
        else:
            click.secho(f"⚠️ {passed}/{total} tests passed", fg="yellow", bold=True)

        if verbose:
            click.secho("\nDetailed Results:", fg="cyan")
            for result in results:
                click.echo(f"\n{result['name']}:")
                click.echo(f"  Pattern: {result['pattern']}")
                click.echo(f"  Status: {result['status']}")
                if result.get("error"):
                    click.echo(f"  Error: {result['error']}")
