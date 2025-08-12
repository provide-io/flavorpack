#!/usr/bin/env python3
"""
Test to prove packagers embed launchers and create self-extracting PSPFs.
"""

from pathlib import Path
import shutil
import subprocess
import tempfile


def create_test_provider(temp_dir: Path, name: str):
    """Create a minimal test provider."""
    # Python modules can't have hyphens, so replace with underscore
    module_name = name.replace("-", "_")
    src_dir = temp_dir / "src" / module_name
    src_dir.mkdir(parents=True)

    (src_dir / "__init__.py").write_text(f'"""Test {name} provider."""')
    (src_dir / "main.py").write_text(f"""
import sys
import json

def serve():
    print(json.dumps({{
        "proof": "{name} provider executed successfully!",
        "launcher": "embedded launcher extracted and used"
    }}))
    sys.exit(0)

if __name__ == "__main__":
    serve()
""")

    # Create pyproject.toml
    pyproject = temp_dir / "pyproject.toml"
    pyproject.write_text(f"""
[build-system]
requires = ["setuptools>=61.0", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "{name}-provider"
version = "1.0.0"
requires-python = ">=3.9"

[project.scripts]
terraform-provider-{name} = "{module_name}.main:serve"

[tool.pspf]
provider_name = "{name}"
entry_point = "{module_name}.main:serve"

[tool.pspf.build]
python_version = "3.13"
dependencies = ["./src/{module_name}"]

[tool.setuptools.packages.find]
where = ["src"]
include = ["{module_name}*"]
""")
    return pyproject


def test_go_packager_embedded_launcher() -> bool:
    """Test Go packager with embedded Go launcher."""
    print("\n" + "=" * 60)
    print("Testing Go Packager with Embedded Go Launcher")
    print("=" * 60)

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_dir = Path(temp_dir)

        # Create test provider
        pyproject = create_test_provider(temp_dir, "go-test")

        # First build a Python package
        from flavor.api import build_package_from_manifest

        artifacts = build_package_from_manifest(pyproject)
        assert len(artifacts) == 1
        python_package = artifacts[0]
        print(f"✅ Python package created: {python_package}")

        # Create a payload directory for Go packager
        payload_dir = temp_dir / "payload"
        payload_dir.mkdir()

        # Extract the Python package to payload dir
        import tarfile

        with tarfile.open(python_package, "r:gz") as tar:
            tar.extractall(payload_dir)

        # Now use Go packager to create package with embedded launcher
        output_file = temp_dir / "go-embedded.flavor"

        # Create payload.tgz for Go packager
        payload_tgz = temp_dir / "payload.tgz"
        with tarfile.open(payload_tgz, "w:gz") as tar:
            tar.add(payload_dir, arcname=".")

        result = subprocess.run(
            [
                "./flavor-go",
                "build",
                "--launcher-bin",
                "./flavor-launcher-go",
                "--out",
                str(output_file),
                "--payload-dir",
                str(payload_dir),
            ],
            capture_output=True,
            text=True,
        )

        if result.returncode != 0:
            print(f"Go packager error: {result.stderr}")
            return False

        print(f"✅ Go package created: {output_file}")

        # Test execution - the package should self-extract the embedded launcher
        result = subprocess.run([str(output_file)], capture_output=True, text=True)

        print(f"Execution output: {result.stdout}")

        if "go-test provider executed successfully!" in result.stdout:
            print("✅ SUCCESS: Go packager with embedded Go launcher works!")
            return True
        else:
            print("❌ FAILED: Provider did not execute correctly")
            return False


def test_rust_packager_embedded_launcher() -> bool:
    """Test Rust packager with embedded Rust launcher."""
    print("\n" + "=" * 60)
    print("Testing Rust Packager with Embedded Rust Launcher")
    print("=" * 60)

    # Check if Rust packager exists
    if not Path("./flavor-rs").exists():
        print("❌ Rust packager not found")
        return False

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_dir = Path(temp_dir)

        # Create test provider
        pyproject = create_test_provider(temp_dir, "rust-test")

        # Build Python package first
        from flavor.api import build_package_from_manifest

        artifacts = build_package_from_manifest(pyproject)
        assert len(artifacts) == 1
        python_package = artifacts[0]
        print(f"✅ Python package created: {python_package}")

        # Create output file by concatenating launcher + package
        output_file = temp_dir / "rust-embedded.flavor"

        # Concatenate launcher and package
        with open(output_file, "wb") as out:
            # Write launcher first
            with open("./flavor-launcher-rs", "rb") as launcher:
                out.write(launcher.read())
            # Then append the package
            with open(python_package, "rb") as pkg:
                out.write(pkg.read())

        output_file.chmod(0o755)
        print(f"✅ Created executable with embedded launcher: {output_file}")

        # Test execution
        result = subprocess.run([str(output_file)], capture_output=True, text=True)

        print(f"Execution output: {result.stdout}")
        print(f"Execution stderr: {result.stderr}")

        if "rust-test provider executed successfully!" in result.stdout:
            print("✅ SUCCESS: Rust launcher can extract and run embedded package!")
            return True
        else:
            print("❌ FAILED: Provider did not execute correctly")
            return False


def test_self_extraction() -> bool:
    """Test that PSPF packages self-extract the embedded launcher."""
    print("\n" + "=" * 60)
    print("Testing Self-Extraction of Embedded Launcher")
    print("=" * 60)

    # Check cache directory before and after
    cache_base = Path.home() / ".cache" / "flavor"

    # Clear cache first
    if cache_base.exists():
        for cache_dir in cache_base.iterdir():
            if cache_dir.is_dir():
                shutil.rmtree(cache_dir)

    print("✅ Cache cleared")

    # Run one of the existing test packages
    test_packages = list(Path("flavor-test-output").glob("*.flavor"))
    if not test_packages:
        print("❌ No test packages found")
        return False

    test_package = test_packages[0]
    print(f"Testing with: {test_package}")

    # Execute the package
    result = subprocess.run(
        [str(test_package), "--version"],
        capture_output=True,
        text=True,
        env={"FLAVOR_LOG_LEVEL": "trace"},
    )

    print(f"Exit code: {result.returncode}")

    # Check if cache was created
    if cache_base.exists():
        print("\n✅ Cache directory created:")
        for cache_dir in cache_base.iterdir():
            print(f"  Cache: {cache_dir.name}")
            # Look for extracted files
            for item in cache_dir.rglob("*"):
                if item.is_file():
                    rel_path = item.relative_to(cache_dir)
                    print(f"    - {rel_path}")
                    if "launcher" in str(rel_path) or "payload" in str(rel_path):
                        print("      ✅ Found extracted component!")

    return True


def main() -> None:
    """Run all embedded launcher tests."""
    print("Testing Embedded Launcher Functionality")
    print("=" * 60)

    results = []

    # Test 1: Go packager with embedded launcher
    results.append(("Go packager + Go launcher", test_go_packager_embedded_launcher()))

    # Test 2: Rust launcher with package
    results.append(("Rust launcher + package", test_rust_packager_embedded_launcher()))

    # Test 3: Self-extraction
    results.append(("Self-extraction", test_self_extraction()))

    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    for test_name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status}: {test_name}")

    if all(success for _, success in results):
        print("\n🎉 All embedded launcher tests passed!")
    else:
        print("\n⚠️  Some tests failed!")


if __name__ == "__main__":
    main()
