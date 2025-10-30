#!/usr/bin/env python3
#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
"""Orchestrate the Flavor release process."""
import argparse
from datetime import datetime
from pathlib import Path
import sys

# Import run_command from flavor.utils
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
from provide.foundation.process import run


def get_project_root() -> Path:
    """Get the project root directory."""
    return Path(__file__).parent.parent


def get_current_version() -> str:
    """Get current version from pyproject.toml."""
    pyproject = get_project_root() / "pyproject.toml"
    with open(pyproject) as f:
        for line in f:
            if line.startswith("version = "):
                return line.split('"')[1]
    return "0.0.0"


def check_git_status() -> bool:
    """Check if git working directory is clean."""
    result = run(["git", "status", "--porcelain"])
    if result.stdout.strip():
        print("⚠️  Git working directory is not clean:")
        print(result.stdout)
        return False
    return True


def check_branch() -> str:
    """Get current git branch."""
    result = run(["git", "rev-parse", "--abbrev-ref", "HEAD"])
    return result.stdout.strip()


def run_tests() -> bool:
    """Run test suite."""
    print("\n🧪 Running tests...")
    result = run(
        [sys.executable, "-m", "pytest", "tests/", "-q", "--tb=short"],
        cwd=get_project_root(),
    )

    if result.returncode != 0:
        print("❌ Tests failed")
        return False

    print("✅ Tests passed")
    return True


def build_helpers() -> bool:
    """Build helper binaries."""
    print("\n🔨 Building helpers...")
    helpers_dir = get_project_root() / "helpers"

    # Check if build script exists
    build_script = helpers_dir / "build.sh"
    if not build_script.exists():
        print("⚠️  helpers/build.sh not found, skipping helper build")
        return True

    result = run(["./build.sh"], cwd=helpers_dir)
    if result.returncode != 0:
        print("❌ Helper build failed")
        return False

    print("✅ Helpers built successfully")
    return True


def build_wheels(platforms: list[str] | None = None) -> list[Path]:
    """Build release wheels."""
    print("\n📦 Building wheels...")

    build_cmd = [sys.executable, "tools/build_wheel.py"]

    if platforms:
        wheels = []
        for platform in platforms:
            result = run([*build_cmd, "--platform", platform], cwd=get_project_root())
            if result.returncode == 0:
                # Find the built wheel
                dist_dir = get_project_root() / "dist"
                platform_wheels = list(dist_dir.glob(f"*{platform}*.whl"))
                wheels.extend(platform_wheels)
        return wheels
    else:
        result = run([*build_cmd, "--all"], cwd=get_project_root())

        if result.returncode != 0:
            print("❌ Wheel build failed")
            return []

        dist_dir = get_project_root() / "dist"
        return list(dist_dir.glob("*.whl"))


def validate_wheels(wheels: list[Path]) -> bool:
    """Validate built wheels."""
    print("\n🔍 Validating wheels...")

    for wheel in wheels:
        result = run(
            [sys.executable, "tools/validate_wheel.py", str(wheel)],
            cwd=get_project_root(),
        )

        if result.returncode != 0:
            print(f"❌ Validation failed for {wheel.name}")
            return False

    print("✅ All wheels validated successfully")
    return True


def create_git_tag(version: str, push: bool = False) -> bool:
    """Create and optionally push a git tag."""
    tag = f"v{version}"

    # Check if tag already exists
    result = run(["git", "tag", "-l", tag])
    if result.stdout.strip():
        print(f"⚠️  Tag {tag} already exists")
        return False

    # Create tag
    result = run(["git", "tag", "-a", tag, "-m", f"Release {version}"])

    if result.returncode != 0:
        print(f"❌ Failed to create tag {tag}")
        return False

    print(f"✅ Created tag {tag}")

    if push:
        result = run(["git", "push", "origin", tag])
        if result.returncode != 0:
            print(f"❌ Failed to push tag {tag}")
            return False
        print(f"✅ Pushed tag {tag}")

    return True


def upload_to_pypi(wheels: list[Path], test: bool = False) -> bool:
    """Upload wheels to PyPI."""
    print(f"\n📤 Uploading to {'Test' if test else ''}PyPI...")

    # Check if twine is installed
    result = run([sys.executable, "-m", "pip", "show", "twine"])
    if result.returncode != 0:
        print("❌ twine is not installed. Run: pip install twine")
        return False

    # Upload wheels
    cmd = [sys.executable, "-m", "twine", "upload"]
    if test:
        cmd.extend(["--repository", "testpypi"])
    cmd.extend([str(w) for w in wheels])

    result = run(cmd)
    if result.returncode != 0:
        print(f"❌ Upload to {'Test' if test else ''}PyPI failed")
        return False

    print(f"✅ Successfully uploaded to {'Test' if test else ''}PyPI")
    return True


def create_release_notes(version: str, wheels: list[Path]) -> str:
    """Generate release notes."""
    notes = f"""# Flavor v{version}

Released: {datetime.now().strftime("%Y-%m-%d")}

## 📦 Wheels

"""

    for wheel in wheels:
        size_mb = wheel.stat().st_size / (1024 * 1024)
        notes += f"- `{wheel.name}` ({size_mb:.1f} MB)\n"

    notes += """
## 🎯 Installation

```bash
pip install flavor
```

## 🔧 Platform Support

- macOS (ARM64, x86_64)
- Linux (ARM64, x86_64)
- Windows (x86_64)

## 📝 Changes

See [CHANGELOG.md](CHANGELOG.md) for detailed changes.
"""

    return notes


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Orchestrate Flavor release process")
    parser.add_argument("--version", help="Version to release (default: from pyproject.toml)")
    parser.add_argument(
        "--platforms",
        nargs="+",
        choices=[
            "darwin_arm64",
            "darwin_amd64",
            "linux_amd64",
            "linux_arm64",
        ],
        help="Specific platforms to build (default: all)",
    )
    parser.add_argument("--skip-tests", action="store_true", help="Skip running tests")
    parser.add_argument("--skip-helpers", action="store_true", help="Skip building helpers")
    parser.add_argument("--skip-validation", action="store_true", help="Skip wheel validation")
    parser.add_argument("--test-pypi", action="store_true", help="Upload to TestPyPI instead of PyPI")
    parser.add_argument("--no-upload", action="store_true", help="Don't upload to PyPI")
    parser.add_argument("--tag", action="store_true", help="Create git tag for release")
    parser.add_argument("--push-tag", action="store_true", help="Push git tag to origin")
    parser.add_argument("--dry-run", action="store_true", help="Perform dry run (no uploads or tags)")

    args = parser.parse_args()

    # Get version
    version = args.version or get_current_version()

    print(f"""
╔══════════════════════════════════════╗
║     Flavor Release Process v{version:8s} ║
╚══════════════════════════════════════╝
""")

    # Check git status
    if not args.dry_run:
        branch = check_branch()
        print(f"📍 Current branch: {branch}")

        if branch not in ["main", "master", "develop"]:
            response = input("⚠️  Not on main branch. Continue? (y/N): ")
            if response.lower() != "y":
                print("Aborted")
                return 1

        if not check_git_status():
            response = input("⚠️  Working directory not clean. Continue? (y/N): ")
            if response.lower() != "y":
                print("Aborted")
                return 1

    # Run tests
    if not args.skip_tests and not run_tests():
        print("\n❌ Release aborted due to test failures")
        return 1

    # Build helpers
    if not args.skip_helpers and not build_helpers():
        print("\n❌ Release aborted due to helper build failure")
        return 1

    # Build wheels
    wheels = build_wheels(args.platforms)
    if not wheels:
        print("\n❌ No wheels were built")
        return 1

    print(f"\n✅ Built {len(wheels)} wheel(s):")
    for wheel in wheels:
        print(f"  - {wheel.name}")

    # Validate wheels
    if not args.skip_validation and not validate_wheels(wheels):
        print("\n❌ Release aborted due to validation failure")
        return 1

    # Create release notes
    notes = create_release_notes(version, wheels)
    notes_file = get_project_root() / "dist" / f"RELEASE-{version}.md"
    notes_file.write_text(notes)
    print(f"\n📝 Release notes written to {notes_file}")

    if args.dry_run:
        print("\n🌟 Dry run complete!")
        print("  To perform actual release, run without --dry-run")
        return 0

    # Create git tag
    if (args.tag or args.push_tag) and not create_git_tag(version, args.push_tag):
        print("\n⚠️  Failed to create/push git tag")

    # Upload to PyPI
    if not args.no_upload and not upload_to_pypi(wheels, args.test_pypi):
        print("\n❌ Release failed during upload")
        return 1

    print(f"""
╔══════════════════════════════════════╗
║         Release Complete! 🎉         ║
╚══════════════════════════════════════╝

Version {version} has been released!

{"Uploaded to TestPyPI" if args.test_pypi else "Uploaded to PyPI" if not args.no_upload else "Wheels built locally"}

Next steps:
1. Test installation: pip install {"--index-url https://test.pypi.org/simple/ " if args.test_pypi else ""}flavor=={version}
2. Create GitHub release with notes from dist/RELEASE-{version}.md
3. Announce the release
""")

    return 0


if __name__ == "__main__":
    sys.exit(main())
# 🌶️📦🔚
