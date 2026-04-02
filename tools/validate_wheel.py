#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""Validate Flavor wheels for correctness and completeness."""

import argparse
import builtins
import contextlib
from pathlib import Path
import subprocess
import sys
import tempfile
import zipfile


def get_wheel_metadata(wheel_path: Path) -> dict:
    """Extract metadata from a wheel file."""
    metadata = {
        "filename": wheel_path.name,
        "size_mb": wheel_path.stat().st_size / (1024 * 1024),
        "platform": "unknown",
        "python_version": "unknown",
        "has_helpers": False,
        "helpers": [],
        "file_count": 0,
    }

    # Parse wheel filename
    parts = wheel_path.stem.split("-")
    if len(parts) >= 5:
        metadata["platform"] = "-".join(parts[4:])
        metadata["python_version"] = parts[2]

    # Check wheel contents
    with zipfile.ZipFile(wheel_path, "r") as whl:
        files = whl.namelist()
        metadata["file_count"] = len(files)

        # Check for helpers - look in helpers/bin directory
        helper_files = [
            f
            for f in files
            if "flavor/helpers/bin/" in f
            and not f.endswith(".py")
            and not f.endswith("/")
            and "__pycache__" not in f
        ]

        if helper_files:
            metadata["has_helpers"] = True
            metadata["helpers"] = [Path(f).name for f in helper_files]

    return metadata


HELPER_FAMILIES = [
    "flavor-go-builder",
    "flavor-go-launcher",
    "flavor-rs-builder",
    "flavor-rs-launcher",
]


def _parse_wheel_platform(wheel_path: Path) -> str:
    """Parse and normalize the platform tag from a wheel filename."""
    parts = wheel_path.stem.split("-")
    # wheel stem: name-version-python-abi-platform
    # but name may contain hyphens, so take the last 3 parts
    if len(parts) < 3:
        return "unknown"
    platform_tag = parts[-1]  # last part is platform

    # Normalize to PSPF platform names
    if platform_tag == "any":
        return "any"
    if "x86_64" in platform_tag or "amd64" in platform_tag:
        if "win" in platform_tag:
            return "windows_amd64"
        return "linux_amd64" if "linux" in platform_tag else "darwin_amd64"
    if "aarch64" in platform_tag or "arm64" in platform_tag:
        if "win" in platform_tag:
            return "windows_arm64"
        if "linux" in platform_tag:
            return "linux_arm64"
        return "darwin_arm64"  # macosx_*_arm64
    return platform_tag  # fallback: return as-is


def _parse_wheel_version(wheel_path: Path) -> str:
    """Parse the wheel version from the wheel filename."""
    parts = wheel_path.stem.split("-")
    if len(parts) < 4:
        return "unknown"
    return parts[-4]


def _expected_helper_names(family: str, version: str, platform: str) -> set[str]:
    """Return the exact helper filename(s) allowed for a wheel helper family."""
    name = f"{family}-{version}-{platform}"
    if platform.startswith("windows_"):
        return {f"{name}.exe"}
    return {name}


def _is_helper_family_file(name: str) -> bool:
    """Return whether a filename belongs to a known helper family naming space."""
    return any(name == family or name.startswith(f"{family}-") for family in HELPER_FAMILIES)


def validate_helpers(wheel_path: Path) -> tuple[bool, list[str]]:  # noqa: C901
    """
    Validate that helpers in the wheel are correct for the wheel's platform.

    Returns:
        (success, messages) tuple
    """
    messages = []
    success = True
    platform = _parse_wheel_platform(wheel_path)
    wheel_version = _parse_wheel_version(wheel_path)

    with tempfile.TemporaryDirectory() as tmpdir:
        with zipfile.ZipFile(wheel_path, "r") as whl:
            for member in whl.namelist():
                if member.startswith("/") or ".." in member.split("/"):
                    raise ValueError(f"Unsafe path in wheel: {member}")
            whl.extractall(tmpdir)

        helpers_dir = Path(tmpdir) / "flavor" / "helpers" / "bin"

        if platform == "any":
            if helpers_dir.exists() and any(helpers_dir.iterdir()):
                messages.append("  ❌ Universal wheel contains native helper binaries (packaging defect)")
                return False, messages
            messages.append("  ✓ Universal wheel: no platform helpers expected")
            return True, messages

        if not helpers_dir.exists():
            messages.append(f"  ❌ No helpers directory found (expected helpers for {platform})")
            return False, messages

        all_files = [f for f in helpers_dir.iterdir() if f.is_file()]
        expected_matches: set[str] = set()

        for family in HELPER_FAMILIES:
            expected_names = _expected_helper_names(family, wheel_version, platform)
            matches = [f for f in all_files if f.name in expected_names]

            if not matches:
                names = ", ".join(sorted(expected_names))
                messages.append(f"  ❌ Expected helper not found: {names}")
                success = False
                continue

            if len(matches) > 1:
                names = ", ".join(f.name for f in matches)
                messages.append(f"  ❌ Multiple helpers matched for {family}: {names}")
                success = False
                continue

            helper_path = matches[0]
            expected_matches.add(helper_path.name)
            size_kb = helper_path.stat().st_size / 1024
            messages.append(f"  ✓ {helper_path.name} ({size_kb:.0f} KB)")

            # Only run --version if we're on the matching platform

            current = sys.platform
            can_run = (
                ("linux" in platform and current == "linux")
                or ("darwin" in platform and current == "darwin")
                or ("windows" in platform and current == "win32")
            )
            if can_run:
                with contextlib.suppress(builtins.BaseException):
                    helper_path.chmod(0o755)
                try:
                    result = subprocess.run(
                        [str(helper_path), "--version"],
                        capture_output=True,
                        text=True,
                        timeout=5,
                    )
                    if result.returncode == 0:
                        messages.append(f"    Version: {result.stdout.strip().split(chr(10))[0]}")
                    else:
                        messages.append("    ⚠️  Failed to run --version")
                except Exception as e:
                    messages.append(f"    ⚠️  Cannot execute: {e}")

        unexpected = [
            f.name for f in all_files if f.name not in expected_matches and _is_helper_family_file(f.name)
        ]
        if unexpected:
            names = ", ".join(sorted(unexpected))
            messages.append(f"  ❌ Unexpected helper(s) for {platform}: {names}")
            success = False

    return success, messages


def validate_installation(wheel_path: Path) -> tuple[bool, list[str]]:
    """
    Test installing the wheel in a fresh virtual environment.

    Returns:
        (success, messages) tuple
    """
    messages = []
    success = True

    with tempfile.TemporaryDirectory() as tmpdir:
        venv_dir = Path(tmpdir) / "venv"

        # Create virtual environment
        result = subprocess.run(
            [sys.executable, "-m", "venv", str(venv_dir)],
            capture_output=True,
            text=True,
        )

        if result.returncode != 0:
            messages.append(f"  ❌ Failed to create venv: {result.stderr}")
            return False, messages

        # Get pip path
        if sys.platform == "win32":
            pip = venv_dir / "Scripts" / "pip.exe"
            python = venv_dir / "Scripts" / "python.exe"
        else:
            pip = venv_dir / "bin" / "pip"
            python = venv_dir / "bin" / "python"

        # Install wheel - CRITICAL: use pip3 for proper installation
        result = subprocess.run(
            [
                str(pip),
                "install",
                str(wheel_path),
            ],  # pip3 is critical for proper wheel installation
            capture_output=True,
            text=True,
        )

        if result.returncode != 0:
            messages.append(f"  ❌ Installation failed: {result.stderr}")
            return False, messages

        messages.append("  ✓ Wheel installed successfully")

        # Test import
        test_script = """
import sys
import os
try:
    # Initialize foundation first
    from provide.foundation import pout, perr

    # Test basic import
    import flavor

    # Test CLI import
    from flavor.cli import main

    # Test helpers manager if available
    try:
        from flavor.helpers.manager import HelperManager
        manager = HelperManager()
        helpers = manager.list_helpers()
        total_helpers = len(helpers.get('launchers', [])) + len(helpers.get('builders', []))
        if total_helpers > 0:
            pout(f"INFO: {total_helpers} embedded helper(s) found")
        else:
            pout("INFO: No embedded helpers (universal wheel)")
    except Exception as e:
        perr(f"⚠️ Helpers test: {e}")

    # Test config system
    try:
        from flavor.config import get_flavor_config
        config = get_flavor_config()
    except Exception as e:
        perr(f"⚠️ Config test: {e}")

    pout("🎉 All import tests passed")
    sys.exit(0)
except Exception as e:
    import traceback
    try:
        from provide.foundation import perr
        perr(f"❌ Import error: {e}")
        perr(f"📋 Traceback: {traceback.format_exc()}")
    except:
        print(f"Import error: {e}")
        print(f"Traceback: {traceback.format_exc()}")
    sys.exit(1)
"""

        result = subprocess.run([str(python), "-c", test_script], capture_output=True, text=True)

        if result.returncode == 0:
            messages.append("  ✓ Import test passed")
            for line in result.stdout.strip().split("\n"):
                messages.append(f"    {line}")
        else:
            messages.append(f"  ❌ Import test failed: {result.stderr}")
            success = False

    return success, messages


def validate_wheel(wheel_path: Path, full: bool = False) -> bool:
    """
    Validate a Flavor wheel.

    Args:
        wheel_path: Path to the wheel file
        full: If True, perform full validation including installation test

    Returns:
        True if validation passed
    """
    if not wheel_path.exists():
        print(f"❌ Wheel not found: {wheel_path}")
        return False

    print(f"\n🔍 Validating: {wheel_path.name}")
    print("=" * 60)

    # Get metadata
    metadata = get_wheel_metadata(wheel_path)
    print("📊 Metadata:")
    print(f"  Size: {metadata['size_mb']:.2f} MB")
    print(f"  Platform: {metadata['platform']}")
    print(f"  Python: {metadata['python_version']}")
    print(f"  Files: {metadata['file_count']}")
    print(f"  Has helpers: {metadata['has_helpers']}")

    all_valid = True

    # Validate helpers
    if metadata["has_helpers"]:
        success, messages = validate_helpers(wheel_path)
        for msg in messages:
            print(msg)
        if not success:
            all_valid = False

    # Full validation
    if full:
        success, messages = validate_installation(wheel_path)
        for msg in messages:
            print(msg)
        if not success:
            all_valid = False

    # Summary
    print("\n" + "=" * 60)
    if all_valid:
        print(f"✅ All validations passed for {wheel_path.name}")
    else:
        print(f"❌ Validation failed for {wheel_path.name}")

    return all_valid


def validate_all_wheels(dist_dir: Path, full: bool = False) -> bool:
    """Validate all wheels in a directory."""
    wheels = list(dist_dir.glob("*.whl"))

    if not wheels:
        print(f"❌ No wheels found in {dist_dir}")
        return False

    print(f"Found {len(wheels)} wheel(s) to validate")

    all_valid = True
    for wheel in wheels:
        if not validate_wheel(wheel, full):
            all_valid = False

    return all_valid


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Validate Flavor wheels")
    parser.add_argument("wheel", nargs="?", type=Path, help="Path to wheel file to validate")
    parser.add_argument("--all", action="store_true", help="Validate all wheels in dist/")
    parser.add_argument(
        "--full",
        action="store_true",
        help="Perform full validation including installation test",
    )
    parser.add_argument(
        "--dist-dir",
        type=Path,
        default=Path("dist"),
        help="Directory containing wheels (default: dist)",
    )

    args = parser.parse_args()

    if args.all:
        success = validate_all_wheels(args.dist_dir, args.full)
    elif args.wheel:
        success = validate_wheel(args.wheel, args.full)
    else:
        parser.error("Either specify a wheel file or use --all")

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()

# 🌶️📦🔚
