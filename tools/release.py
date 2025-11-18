#!/usr/bin/env python3
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
    with pyproject.open(encoding="utf-8") as f:
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
    result = run(
        [sys.executable, "-m", "pytest", "tests/", "-q", "--tb=short"],
        cwd=get_project_root(),
    )

    if result.returncode != 0:
        print("❌ Tests failed")
        return False

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

    return True


def build_wheels(platforms: list[str] | None = None) -> list[Path]:
    """Build release wheels."""

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

    if push:
        result = run(["git", "push", "origin", tag])
        if result.returncode != 0:
            print(f"❌ Failed to push tag {tag}")
            return False

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

    return True


def create_release_notes(version: str, wheels: list[Path]) -> str:
    """Generate release notes."""
    notes = f"""# Flavor v{version}

Released: {datetime.now().strftime("%Y-%m-%d")}


"""

    for wheel in wheels:
        size_mb = wheel.stat().st_size / (1024 * 1024)
        notes += f"- `{wheel.name}` ({size_mb:.1f} MB)\n"

    notes += """
## 🎯 Installation

```bash
pip install flavor
```


- macOS (ARM64, x86_64)
- Linux (ARM64, x86_64)
- Windows (x86_64)

## 📝 Changes

See [CHANGELOG.md](CHANGELOG.md) for detailed changes.
"""

    return notes


def _print_release_banner(version: str) -> None:
    print(
        f"""
╔══════════════════════════════════════╗
║     Flavor Release Process v{version:8s} ║
╚══════════════════════════════════════╝
"""
    )


def _prompt_continue(message: str) -> bool:
    response = input(f"{message} Continue? (y/N): ")
    return response.lower() == "y"


def _require_clean_git_state(args: argparse.Namespace) -> bool:
    if args.dry_run:
        return True

    branch = check_branch()
    print(f"📍 Current branch: {branch}")

    if branch not in ["main", "master", "develop"] and not _prompt_continue("⚠️  Not on main branch."):
        print("Aborted")
        return False

    if not check_git_status() and not _prompt_continue("⚠️  Working directory not clean."):
        print("Aborted")
        return False

    return True


def _run_pre_release_checks(args: argparse.Namespace) -> bool:
    if not args.skip_tests and not run_tests():
        print("\n❌ Release aborted due to test failures")
        return False

    if not args.skip_helpers and not build_helpers():
        print("\n❌ Release aborted due to helper build failure")
        return False

    return True


def _build_release_wheels(args: argparse.Namespace) -> list[Path]:
    wheels = build_wheels(args.platforms)
    if not wheels:
        print("\n❌ No wheels were built")
        return []

    for wheel in wheels:
        print(f"  - {wheel.name}")

    return wheels


def _maybe_validate_wheels(args: argparse.Namespace, wheels: list[Path]) -> bool:
    if args.skip_validation:
        return True

    if not validate_wheels(wheels):
        print("\n❌ Release aborted due to validation failure")
        return False

    return True


def _write_release_notes(version: str, wheels: list[Path]) -> Path:
    notes = create_release_notes(version, wheels)
    notes_file = get_project_root() / "dist" / f"RELEASE-{version}.md"
    notes_file.write_text(notes)
    print(f"\n📝 Release notes written to {notes_file}")
    return notes_file


def _maybe_create_git_tag(args: argparse.Namespace, version: str) -> None:
    if (args.tag or args.push_tag) and not create_git_tag(version, args.push_tag):
        print("\n⚠️  Failed to create/push git tag")


def _maybe_upload_to_pypi(args: argparse.Namespace, wheels: list[Path]) -> bool:
    if args.no_upload:
        return True

    if not upload_to_pypi(wheels, args.test_pypi):
        print("\n❌ Release failed during upload")
        return False

    return True


def _print_release_success(version: str, args: argparse.Namespace) -> None:
    destination = (
        "Uploaded to TestPyPI"
        if args.test_pypi
        else "Uploaded to PyPI"
        if not args.no_upload
        else "Wheels built locally"
    )
    print(
        f"""
╔══════════════════════════════════════╗
║         Release Complete! 🎉         ║
╚══════════════════════════════════════╝

Version {version} has been released!

{destination}

Next steps:
1. Test installation: pip install {"--index-url https://test.pypi.org/simple/ " if args.test_pypi else ""}flavor=={version}
2. Create GitHub release with notes from dist/RELEASE-{version}.md
3. Announce the release
"""
    )


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

    version = args.version or get_current_version()
    _print_release_banner(version)

    if not _require_clean_git_state(args):
        return 1

    if not _run_pre_release_checks(args):
        return 1

    wheels = _build_release_wheels(args)
    if not wheels:
        return 1

    if not _maybe_validate_wheels(args, wheels):
        return 1

    _write_release_notes(version, wheels)

    if args.dry_run:
        print("\n🌟 Dry run complete!")
        print("  To perform actual release, run without --dry-run")
        return 0

    _maybe_create_git_tag(args, version)

    if not _maybe_upload_to_pypi(args, wheels):
        return 1

    _print_release_success(version, args)
    return 0


if __name__ == "__main__":
    sys.exit(main())

# 🌶️📦🔚
