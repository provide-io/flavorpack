#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""Verify PSPF package integrity."""

from __future__ import annotations

import json
import os
from pathlib import Path
import sys
from typing import Any

import click
from provide.foundation.console import pout


@click.command("verify")
@click.argument("package_path", required=False, type=click.Path(path_type=Path))
@click.option("--json", "output_json", is_flag=True, help="Output results as JSON")
@click.option("--output-file", "-o", type=click.Path(path_type=Path), help="Write output to file")
def verify_command(
    package_path: Path | None,
    output_json: bool,
    output_file: Path | None,
) -> None:
    """Verify PSPF package integrity."""
    package_file = _resolve_package_path(package_path)
    result = {"package": str(package_file), "exists": package_file.exists()}

    if not package_file.exists():
        result["error"] = f"Package file not found: {package_file}"
        _render_result(result, output_json, output_file)
        return

    verification = _verify_with_flavor(package_file)
    if verification is not None:
        result.update(verification)
    else:
        result.update(_basic_verification(package_file))

    _render_result(result, output_json, output_file)


def _resolve_package_path(package_path: Path | None) -> Path:
    """Determine which package to verify."""
    if package_path:
        return package_path

    executable = Path(sys.argv[0])
    if executable.suffix == ".psp":
        return executable

    original = os.environ.get("FLAVOR_ORIGINAL_COMMAND")
    if original:
        return Path(original)

    return executable


def _verify_with_flavor(package_file: Path) -> dict[str, Any] | None:
    """Attempt verification using the Flavor module; return None if unavailable."""
    try:
        from flavor.verification import FlavorVerifier
    except ImportError:
        return None

    try:
        result = FlavorVerifier.verify_package(package_file)
    except Exception as exc:
        return {"error": f"Verification failed: {exc}"}

    return {"verification": result}


def _basic_verification(package_file: Path) -> dict[str, Any]:
    """Perform coarse checks when flavor.verification is unavailable."""
    file_size = package_file.stat().st_size
    info = {
        "file_size_mb": file_size / (1024 * 1024),
        "readable": os.access(package_file, os.R_OK),
        "executable": os.access(package_file, os.X_OK),
        "magic_found": False,
    }

    try:
        with package_file.open("rb") as handle:
            info["magic_found"] = b"PSPF2025" in handle.read(1024 * 1024)
    except Exception as exc:
        info["read_error"] = str(exc)

    return {
        "basic_info": info,
        "warning": "Flavor verification module not available; running basic checks only.",
    }


def _render_result(result: dict[str, Any], output_json: bool, output_file: Path | None) -> None:
    """Emit verification results as JSON or human-readable text."""
    if output_json:
        _render_json_result(result, output_file)
    else:
        _render_text_result(result)


def _render_json_result(result: dict[str, Any], output_file: Path | None) -> None:
    """Emit verification payload as JSON."""
    payload = json.dumps(result, indent=2)
    if output_file:
        output_file.write_text(payload, encoding="utf-8")
    else:
        print(payload)


def _render_text_result(result: dict[str, Any]) -> None:
    """Emit verification payload as human-readable text."""
    pout("=" * 60, color="cyan")
    pout("🔍 PSPF PACKAGE VERIFICATION", color="cyan", bold=True)
    pout("=" * 60, color="cyan")

    if "error" in result:
        pout(f"❌ {result['error']}", color="red")
        return

    verification = result.get("verification")
    if verification:
        pout("\n📋 Verification Results:", color="green")
        pout(f"  Format: {verification.get('format', 'unknown')}")
        pout(f"  Version: {verification.get('version', 'unknown')}")
        launcher_size = verification.get("launcher_size", 0)
        pout(f"  Launcher Size: {launcher_size / 1024:.1f} KB")

        package_meta = verification.get("package", {})
        if package_meta:
            pout(f"  Package: {package_meta.get('name', 'unknown')} v{package_meta.get('version', 'unknown')}")

        slots = verification.get("slots")
        if slots is not None:
            pout(f"  Slots: {len(slots)}")

        pout("\n🔍 Additional Checks:", color="yellow")
        if not verification.get("signature_valid", True):
            pout("  ❌ Signature verification: FAILED")
        if "index_checksum_valid" in verification and not verification["index_checksum_valid"]:
            pout("  ❌ Index checksum invalid")
        if not verification.get("metadata"):
            pout("  ⚠️ Metadata not found")
        return

    basic_info = result.get("basic_info", {})
    pout("⚠️ Flavor verification module not available", color="yellow")
    pout("  Running basic checks only...")
    pout("\n📊 Basic Information:")
    pout(f"  File Size: {basic_info.get('file_size_mb', 0):.2f} MB")
    pout(f"  Readable: {'Yes' if basic_info.get('readable') else 'No'}")
    pout(f"  Executable: {'Yes' if basic_info.get('executable') else 'No'}")
    if not basic_info.get("magic_found"):
        pout("  ⚠️ PSPF2025 magic not found in first MB")
    if "read_error" in basic_info:
        pout(f"  ❌ Could not read file: {basic_info['read_error']}")


# 🌶️📦🔚
