#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""Build platform-specific wheels with embedded helpers."""

import argparse
from collections.abc import Sequence
from pathlib import Path
import shutil
import subprocess
import sys
from typing import Any

# We'll import run_command directly without going through flavor.__init__
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


# Import just the subprocess utility to avoid circular imports
def run_command(cmd: Sequence[str] | str, **kwargs: Any) -> subprocess.CompletedProcess[str]:
    """Run a command and return the result."""
    # Use subprocess directly to avoid import issues during build
    result = subprocess.run(cmd, capture_output=True, text=True, **kwargs)
    return result


# Platform to wheel tag mapping
PLATFORM_TAGS = {
    "darwin_arm64": "macosx_11_0_arm64",
    "darwin_amd64": "macosx_10_9_x86_64",
    "linux_amd64": "manylinux_2_17_x86_64.manylinux2014_x86_64",
    "linux_arm64": "manylinux_2_17_aarch64.manylinux2014_aarch64",
    "windows_amd64": "win_amd64",
}

# All supported platforms
ALL_PLATFORMS = list(PLATFORM_TAGS.keys())


def get_project_root() -> Path:
    """Get the project root directory."""
    return Path(__file__).parent.parent


def get_version() -> str:
    """Get the current Flavor version from VERSION file or pyproject.toml."""
    root = get_project_root()

    # Try VERSION file first
    version_file = root / "VERSION"
    if version_file.exists():
        return version_file.read_text().strip()

    # Fall back to pyproject.toml
    pyproject_path = root / "pyproject.toml"
    with pyproject_path.open(encoding="utf-8") as f:
        for line in f:
            if line.startswith("version = "):
                return line.split('"')[1]
    return "0.3.0"  # Default fallback


def clean_build_artifacts() -> None:
    """Clean any existing build artifacts."""
    root = get_project_root()
    dirs_to_clean = [
        root / "build",
        root / "dist",
        root / "src/flavor.egg-info",
        root / "src/flavor/helpers/bin",
    ]

    for dir_path in dirs_to_clean:
        if dir_path.exists():
            shutil.rmtree(dir_path)
            print(f"  ✓ Cleaned {dir_path.relative_to(root)}")


def download_helpers(platform: str, version: str) -> Path | None:
    """
    Download helper artifacts for the specified platform.

    In CI, these would come from the helper pipeline.
    For local builds, assumes helpers are already built.
    """
    helpers_dir = get_project_root() / "helpers" / "bin"

    if not helpers_dir.exists():
        print(f"❌ Helpers directory not found: {helpers_dir}")
        print("  Run 'make build-helpers' first")
        return None

    # Check if platform-specific helpers exist
    required_helpers = [
        f"flavor-go-builder-{version}-{platform}",
        f"flavor-go-launcher-{version}-{platform}",
        f"flavor-rs-builder-{version}-{platform}",
        f"flavor-rs-launcher-{version}-{platform}",
    ]

    # Also check without version suffix
    alt_helpers = [
        f"flavor-go-builder-{platform}",
        f"flavor-go-launcher-{platform}",
        f"flavor-rs-builder-{platform}",
        f"flavor-rs-launcher-{platform}",
    ]

    # Check for generic helpers (no platform suffix)
    generic_helpers = [
        "flavor-go-builder",
        "flavor-go-launcher",
        "flavor-rs-builder",
        "flavor-rs-launcher",
    ]

    helpers_found = False
    for helper_set in [required_helpers, alt_helpers, generic_helpers]:
        if all((helpers_dir / h).exists() or (helpers_dir / f"{h}.exe").exists() for h in helper_set):
            helpers_found = True
            break

    if not helpers_found:
        print(f"⚠️  Platform-specific helpers not found for {platform}")
        print(f"  Looking in: {helpers_dir}")

        # List available helpers
        if helpers_dir.exists():
            print("  Available helpers:")
            for f in sorted(helpers_dir.iterdir()):
                if f.is_file():
                    print(f"    - {f.name}")

    return helpers_dir


def build_platform_wheel(platform: str, output_dir: Path) -> Path | None:
    """
    Build a platform-specific wheel with embedded helpers.

    Args:
        platform: Target platform
        output_dir: Directory to output the wheel

    Returns:
        Path to the built wheel, or None if failed
    """
    print(f"\n🎯 Building wheel for {platform}")

    version = get_version()
    root = get_project_root()

    # Get helpers directory
    helpers_dir = download_helpers(platform, version)
    if not helpers_dir:
        return None

    # Clean previous artifacts
    clean_build_artifacts()

    # Embed helpers
    embed_result = run_command(
        [
            sys.executable,
            str(root / "tools" / "embed_helpers.py"),
            platform,
            str(helpers_dir),
            version,
        ]
    )

    if embed_result.returncode != 0:
        print(f"❌ Failed to embed helpers: {embed_result.stderr}")
        return None

    # Build the wheel
    print("🔨 Building wheel...")

    # Create a custom setup.py that sets the platform tag
    wheel_tag = PLATFORM_TAGS[platform]
    setup_py = root / "setup.py"
    setup_py.write_text('''
"""Temporary setup.py for building platform-specific wheel."""
from setuptools import setup
from setuptools.dist import Distribution

class BinaryDistribution(Distribution):
    def has_ext_modules(self):
        return True

    def is_pure(self):
        return False

if __name__ == "__main__":
    setup(distclass=BinaryDistribution)
''')

    try:
        # Build using pip3 wheel - CRITICAL: must use pip3 for proper dependency resolution
        build_result = run_command(
            [
                "pip3",
                "wheel",  # Using pip3 is critical for wheel building
                "--no-deps",
                "--wheel-dir",
                str(output_dir),
                str(root),
            ]
        )

        if build_result.returncode != 0:
            print(f"❌ Wheel build failed: {build_result.stderr}")
            return None

        # Find the built wheel
        wheels = list(output_dir.glob("*.whl"))
        if not wheels:
            print("❌ No wheel was created")
            return None

        wheel_file = wheels[0]

        # Rename wheel with correct platform tag and Python version range
        wheel_name = wheel_file.name
        import re

        # Always rename to support Python 3.11-3.14
        match = re.match(r"([\w_]+)-([\d.]+)-(.*)\.whl", wheel_name)
        if match:
            pkg_name, pkg_version, _tags = match.groups()

            # Build new tags for Python 3.11-3.14 support
            # Use py311 for Python 3.11+ compatibility
            # Format: name-version-pyver-abi-platform
            new_name = f"{pkg_name}-{pkg_version}-py311-none-{wheel_tag}.whl"
            new_wheel = output_dir / new_name

            # Rename the wheel
            wheel_file.rename(new_wheel)
            wheel_file = new_wheel
            print(f"  ✓ Renamed for Python 3.11+ support: {new_name}")

        return wheel_file

    finally:
        # Clean up temporary setup.py
        if setup_py.exists():
            setup_py.unlink()

        # Clean embedded helpers
        helpers_pkg = root / "src" / "flavor" / "helpers" / "bin"
        if helpers_pkg.exists():
            shutil.rmtree(helpers_pkg)


def build_universal_wheel(output_dir: Path) -> Path | None:
    """Build a universal wheel without embedded helpers."""

    root = get_project_root()
    clean_build_artifacts()

    # Build using standard Python build
    build_result = run_command(
        [
            sys.executable,
            "-m",
            "build",
            "--wheel",
            "--outdir",
            str(output_dir),
            str(root),
        ]
    )

    if build_result.returncode != 0:
        print(f"❌ Universal wheel build failed: {build_result.stderr}")
        return None

    # Find the built wheel
    wheels = list(output_dir.glob("*.whl"))
    if wheels:
        return wheels[0]

    return None


def build_all_wheels(output_dir: Path) -> list[Path]:
    """Build wheels for all supported platforms."""
    wheels = []

    # Build platform-specific wheels
    for platform in ALL_PLATFORMS:
        wheel = build_platform_wheel(platform, output_dir)
        if wheel:
            wheels.append(wheel)

    # Build universal wheel as fallback
    universal = build_universal_wheel(output_dir)
    if universal:
        wheels.append(universal)

    return wheels


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Build platform-specific Flavor wheels with embedded helpers")
    parser.add_argument(
        "--platform",
        choices=[*ALL_PLATFORMS, "universal"],
        help="Target platform (or 'universal' for no helpers)",
    )
    parser.add_argument("--all", action="store_true", help="Build wheels for all platforms")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("dist"),
        help="Output directory for wheels (default: dist)",
    )

    args = parser.parse_args()

    # Validate arguments
    if not args.all and not args.platform:
        parser.error("Either --platform or --all must be specified")

    # Create output directory
    args.output_dir.mkdir(parents=True, exist_ok=True)

    # Build wheels
    if args.all:
        wheels = build_all_wheels(args.output_dir)

        print("\n" + "=" * 60)
        print("=" * 60)
        if wheels:
            for wheel in wheels:
                size = wheel.stat().st_size / (1024 * 1024)
                print(f"  - {wheel.name} ({size:.1f} MB)")
        else:
            print("❌ No wheels were built successfully")
            sys.exit(1)

    elif args.platform == "universal":
        wheel = build_universal_wheel(args.output_dir)
        if not wheel:
            sys.exit(1)

    else:
        wheel = build_platform_wheel(args.platform, args.output_dir)
        if not wheel:
            sys.exit(1)


if __name__ == "__main__":
    main()

# 🌶️📦🔚
