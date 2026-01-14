#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""Test slot substitution patterns in commands."""

import json
from pathlib import Path
import tempfile

import click
from provide.foundation.console import pout

from flavor.helpers import HelperManager
from flavor.package import build_package_from_manifest


@click.command("slot-test")
@click.option("--verbose", "-v", is_flag=True, help="Verbose output")
@click.option("--json-output", is_flag=True, help="Output results as JSON")
def slot_test_command(verbose: bool, json_output: bool) -> None:
    """Test {slot:N} substitution patterns."""
    if not json_output:
        pout("🎰 SLOT SUBSTITUTION TEST", color="cyan", bold=True)
        pout("=" * 60, color="cyan")

    helper_manager = HelperManager()
    test_cases = _slot_test_cases()
    results = [_execute_slot_test(helper_manager, case, verbose, json_output) for case in test_cases]
    _output_slot_results(results, json_output, verbose)


def _slot_test_cases() -> list[dict[str, str]]:
    """Return predefined slot substitution scenarios."""
    return [
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


def _execute_slot_test(
    helper_manager: HelperManager,
    test_case: dict[str, str],
    verbose: bool,
    json_output: bool,
) -> dict[str, str | None]:
    """Build and capture the result for a single slot substitution case."""
    if not json_output:
        pout(f"\n📌 Testing: {test_case['description']}", color="yellow")
        pout(f"   Pattern: {test_case['pattern']}")
        pout(f"   Command: {test_case['command']}")

    status = "✅ Passed"
    error: str | None = None

    with tempfile.TemporaryDirectory() as temp_dir_str:
        temp_dir = Path(temp_dir_str)
        slot0_script = temp_dir / "slot0.py"
        slot0_script.write_text(
            'import sys\nprint(f"Slot 0 executed: {sys.argv}")\n',
            encoding="utf-8",
        )

        slot1_config = temp_dir / "config.json"
        slot1_config.write_text('{"test": "config"}', encoding="utf-8")

        manifest = temp_dir / "pyproject.toml"
        manifest.write_text(
            f"""
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
""",
            encoding="utf-8",
        )

        try:
            launcher_path = helper_manager.get_helper("flavor-rs-launcher")
            build_result = build_package_from_manifest(
                manifest_path=manifest,
                output_dir=temp_dir,
                launcher_bin=launcher_path,
                key_seed="test123",
            )
            if not build_result.success:
                status = "❌ Failed"
                error = getattr(build_result, "error", "Unknown error")
        except Exception as exc:
            status = "❌ Failed"
            error = str(exc)

    if verbose and not json_output and error:
        pout(f"   Error: {error}", color="red")

    return {
        "name": test_case["name"],
        "pattern": test_case["pattern"],
        "command": test_case["command"],
        "description": test_case["description"],
        "status": status,
        "error": error,
    }


def _output_slot_results(results: list[dict[str, str | None]], json_output: bool, verbose: bool) -> None:
    """Emit slot test results."""
    if json_output:
        payload = {
            "test": "slot_substitution",
            "results": results,
            "summary": {
                "total": len(results),
                "failed": len([r for r in results if r["status"] != "✅ Passed"]),
            },
        }
        pout(json.dumps(payload, indent=2))
        return

    pout("\n📊 Results Summary:", color="cyan", bold=True)
    pout("─" * 40, color="cyan")
    for result in results:
        color = "green" if result["status"] == "✅ Passed" else "red"
        pout(f"  {result['status']} {result['description']}", color=color)

    total = len(results)
    passed = len([r for r in results if r["status"] == "✅ Passed"])
    pout("\n" + "─" * 40, color="cyan")
    if passed != total:
        pout(f"⚠️ {passed}/{total} tests passed", color="yellow", bold=True)

    if verbose:
        pout("\nDetailed Results:", color="cyan")
        for result in results:
            pout(f"\n{result['name']}:")
            pout(f"  Pattern: {result['pattern']}")
            pout(f"  Status: {result['status']}")
            if result.get("error"):
                pout(f"  Error: {result['error']}")


# 🌶️📦🔚
