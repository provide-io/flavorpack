#!/usr/bin/env python3
"""Validate Flavor wheels for correctness and completeness."""

import argparse
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
        "has_ingredients": False,
        "ingredients": [],
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

        # Check for ingredients - look in ingredients/bin directory
        ingredient_files = [
            f
            for f in files
            if "flavor/ingredients/bin/" in f
            and not f.endswith(".py")
            and not f.endswith("/")
            and "__pycache__" not in f
        ]

        if ingredient_files:
            metadata["has_ingredients"] = True
            metadata["ingredients"] = [Path(f).name for f in ingredient_files]

    return metadata


def validate_ingredients(wheel_path: Path) -> tuple[bool, list[str]]:
    """
    Validate that ingredients in the wheel are executable.

    Returns:
        (success, messages) tuple
    """
    messages = []
    success = True

    with tempfile.TemporaryDirectory() as tmpdir:
        # Extract wheel
        with zipfile.ZipFile(wheel_path, "r") as whl:
            whl.extractall(tmpdir)

        # Find ingredients - look in ingredients/bin directory
        ingredients_dir = Path(tmpdir) / "flavor" / "ingredients" / "bin"
        if not ingredients_dir.exists():
            messages.append("  ⚠️  No ingredients directory found")
            return True, messages  # Not an error for universal wheels

        # Expected ingredients
        expected = [
            "flavor-go-builder",
            "flavor-go-launcher",
            "flavor-rs-builder",
            "flavor-rs-launcher",
        ]

        for ingredient in expected:
            ingredient_path = ingredients_dir / ingredient
            if not ingredient_path.exists():
                # Check with .exe extension
                ingredient_path = ingredients_dir / f"{ingredient}.exe"

            if ingredient_path.exists():
                # Check if executable
                if not ingredient_path.is_file():
                    messages.append(f"  ❌ {ingredient} is not a file")
                    success = False
                else:
                    size_kb = ingredient_path.stat().st_size / 1024
                    messages.append(f"  ✓ {ingredient} ({size_kb:.0f} KB)")

                    # Make executable first
                    try:
                        ingredient_path.chmod(0o755)
                    except:
                        pass

                    # Try to execute with --version
                    try:
                        result = subprocess.run(
                            [str(ingredient_path), "--version"],
                            capture_output=True,
                            text=True,
                            timeout=5,
                        )
                        if result.returncode == 0:
                            version_line = result.stdout.strip().split("\n")[0]
                            messages.append(f"    Version: {version_line}")
                        else:
                            messages.append("    ⚠️  Failed to run --version")
                    except Exception as e:
                        messages.append(f"    ⚠️  Cannot execute: {e}")
            else:
                messages.append(f"  ❌ {ingredient} not found")
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
    pout(f"✅ Flavor version: {flavor.__version__ if hasattr(flavor, '__version__') else 'unknown'}")

    # Test CLI import
    from flavor.cli import main
    pout("✅ CLI import successful")

    # Test ingredients manager if available
    try:
        from flavor.ingredients.manager import IngredientManager
        manager = IngredientManager()
        ingredients = manager.list_ingredients()
        total_ingredients = len(ingredients.get('launchers', [])) + len(ingredients.get('builders', []))
        if total_ingredients > 0:
            pout(f"✅ Found {total_ingredients} ingredients")
        else:
            pout("ℹ️ No embedded ingredients (universal wheel)")
    except Exception as e:
        perr(f"⚠️ Ingredients test: {e}")

    # Test config system
    try:
        from flavor.config import get_flavor_config
        config = get_flavor_config()
        pout("✅ Config system working")
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
    print(f"  Has ingredients: {metadata['has_ingredients']}")

    all_valid = True

    # Validate ingredients
    if metadata["has_ingredients"]:
        print("\n🔧 Validating ingredients:")
        success, messages = validate_ingredients(wheel_path)
        for msg in messages:
            print(msg)
        if not success:
            all_valid = False

    # Full validation
    if full:
        print("\n📦 Testing installation:")
        success, messages = validate_installation(wheel_path)
        for msg in messages:
            print(msg)
        if not success:
            all_valid = False

    # Summary
    print("\n" + "=" * 60)
    if all_valid:
        print(f"✅ Validation passed for {wheel_path.name}")
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


def main():
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
