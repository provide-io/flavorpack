#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""Embed platform-specific helpers into the Flavor package."""

import argparse
from pathlib import Path
import shutil
import sys


def embed_helpers(platform: str, helpers_dir: str, version: str) -> bool:
    """
    Embed platform-specific helpers into src/flavor/helpers.

    Args:
        platform: Target platform (e.g., darwin_arm64, linux_amd64)
        helpers_dir: Directory containing helper binaries
        version: Flavor version

    Returns:
        True if successful, False otherwise
    """
    helpers_path = Path(helpers_dir)
    if not helpers_path.exists():
        print(f"❌ Helpers directory not found: {helpers_path}")
        return False

    # Create target directory - use helpers/bin to avoid conflict with helpers.py
    target_dir = Path("src/flavor/helpers/bin")
    target_dir.mkdir(parents=True, exist_ok=True)

    # Helper binary names
    helper_names = [
        "flavor-go-builder",
        "flavor-go-launcher",
        "flavor-rs-builder",
        "flavor-rs-launcher",
    ]

    helpers_copied = 0
    for helper in helper_names:
        # Try different naming patterns
        patterns = [
            f"{helper}-{version}-{platform}",
            f"{helper}-{platform}",
            helper,
        ]

        for pattern in patterns:
            source = helpers_path / pattern
            if source.exists():
                # Determine target name
                target_name = helper
                if platform.startswith("windows"):
                    target_name += ".exe"

                target = target_dir / target_name

                # Copy the helper
                shutil.copy2(source, target)

                # Make executable (Unix-like systems)
                if not platform.startswith("windows"):
                    target.chmod(0o755)

                print(f"  ✓ Embedded {helper}")
                helpers_copied += 1
                break
        else:
            print(f"  ⚠️  Helper not found: {helper}")

    if helpers_copied == 0:
        print("❌ No helpers were embedded")
        return False

    # Create __init__.py for helpers/bin package
    init_file = target_dir / "__init__.py"
    init_file.write_text('''"""Embedded helper binaries for Flavor."""
import os
from pathlib import Path

from provide.foundation.platform import is_windows


def get_helpers_dir() -> Path:
    """Get the directory containing helper binaries."""
    return Path(__file__).parent


def get_helper_path(helper_name: str) -> Path:
    """Get the path to a specific helper binary."""
    helpers_dir = get_helpers_dir()

    # Add .exe extension on Windows
    if is_windows():
        helper_name = f"{helper_name}.exe"

    helper_path = helpers_dir / helper_name

    # Make executable if needed
    if helper_path.exists() and not os.access(helper_path, os.X_OK):
        try:
            helper_path.chmod(0o755)
        except:
            pass

    return helper_path


# Helper shortcuts
def get_go_builder() -> Path:
    """Get path to Go builder."""
    return get_helper_path('flavor-go-builder')


def get_go_launcher() -> Path:
    """Get path to Go launcher."""
    return get_helper_path('flavor-go-launcher')


def get_rs_builder() -> Path:
    """Get path to Rust builder."""
    return get_helper_path('flavor-rs-builder')


def get_rs_launcher() -> Path:
    """Get path to Rust launcher."""
    return get_helper_path('flavor-rs-launcher')
''')

    return True


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Embed helpers for platform-specific wheel")
    parser.add_argument("platform", help="Target platform (e.g., darwin_arm64)")
    parser.add_argument("helpers_dir", help="Directory containing helper binaries")
    parser.add_argument("version", help="Flavor version")

    args = parser.parse_args()

    success = embed_helpers(args.platform, args.helpers_dir, args.version)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()

# 🌶️📦🔚
