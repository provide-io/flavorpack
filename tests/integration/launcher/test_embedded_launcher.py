#!/usr/bin/env python3
"""
Test script to prove that packagers embed launchers and create self-extracting PSPFs.
"""

import hashlib
import os
from pathlib import Path
import shutil
import subprocess


def run_command(cmd, cwd=None):
    """Run a command and return output."""
    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=cwd)
    if result.returncode != 0:
        print(f"Error: {result.stderr}")
        raise RuntimeError(f"Command failed: {' '.join(cmd)}")
    return result.stdout


def file_hash(filepath):
    """Calculate SHA256 hash of a file."""
    sha256_hash = hashlib.sha256()
    with open(filepath, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()


def test_packager_with_embedded_launcher(packager_name, launcher_name) -> bool | None:
    """Test that a packager can embed a launcher and create a working PSPF."""
    print(f"\n{'=' * 60}")
    print(f"Testing {packager_name} packager with {launcher_name} launcher")
    print("=" * 60)

    # Create a test provider directory
    test_dir = Path(f"test-{packager_name}-{launcher_name}")
    test_dir.mkdir(exist_ok=True)

    # Change to the flavor directory
    os.chdir("/REDACTED_ABS_PATH")

    # Create a minimal provider manifest
    manifest_content = f"""
provider:
  name: test-embedded-{packager_name}-{launcher_name}
  version: 0.1.0
  description: Test provider with embedded launcher
  package_manifest_version: 1

build:
  python_path: python3
  build_command: echo "Built"

launcher:
  embedded: {launcher_name}
"""

    manifest_path = test_dir / "pyvider.toml"
    manifest_path.write_text(manifest_content)

    # Create a minimal Python provider
    provider_py = test_dir / "main.py"
    provider_py.write_text("""
#!/usr/bin/env python3
import sys
print("Test provider running!", file=sys.stderr)
print('{"version": "0.1.0"}')
""")

    # Make it executable
    provider_py.chmod(0o755)

    # Get packager path
    packager_path = (
        Path(f"./flavor-{packager_name}") if packager_name != "python" else "flavor"
    )
    launcher_path = Path(f"./flavor-launcher-{launcher_name}")

    # Build the PSPF package with embedded launcher
    output_file = f"test-{packager_name}-{launcher_name}.flavor"

    try:
        if packager_name == "python":
            # Python packager
            cmd = [
                "flavor",
                "package",
                "--manifest",
                str(manifest_path),
                "--output",
                output_file,
                "--launcher",
                str(launcher_path),
            ]
        else:
            # Go/Rust packagers
            cmd = [
                str(packager_path),
                "package",
                "--manifest",
                str(manifest_path),
                "--output",
                output_file,
                "--launcher",
                str(launcher_path),
            ]

        run_command(cmd, cwd=test_dir)
        print(f"Package created: {test_dir / output_file}")

        # Verify the package exists and has size
        package_path = test_dir / output_file
        if not package_path.exists():
            raise RuntimeError(f"Package not created: {package_path}")

        size_mb = package_path.stat().st_size / (1024 * 1024)
        print(f"Package size: {size_mb:.2f} MB")

        # Calculate hash
        package_hash = file_hash(package_path)
        print(f"Package hash: {package_hash[:16]}...")

        # Test that the package can be executed
        print("\nTesting package execution...")

        # Clear any cache
        cache_dir = Path.home() / ".cache" / "flavor" / package_hash[:16]
        if cache_dir.exists():
            shutil.rmtree(cache_dir)
            print(f"Cleared cache: {cache_dir}")

        # Execute the package
        env = os.environ.copy()
        env["FLAVOR_LOG_LEVEL"] = "trace"

        result = subprocess.run(
            [str(package_path), "--version"], capture_output=True, text=True, env=env
        )

        print(f"Exit code: {result.returncode}")
        print(f"Stdout: {result.stdout}")
        print(f"Stderr: {result.stderr}")

        # Check if it extracted the launcher
        if cache_dir.exists():
            print(f"\nCache directory created: {cache_dir}")
            # List contents
            for item in cache_dir.rglob("*"):
                if item.is_file():
                    print(f"  - {item.relative_to(cache_dir)}")

        # Verify the embedded launcher was used
        if "Test provider running!" in result.stderr:
            print(
                f"\n✅ SUCCESS: {packager_name} packager with {launcher_name} launcher works!"
            )
            return True
        else:
            print("\n❌ FAILED: Provider did not run correctly")
            return False

    finally:
        # Cleanup
        if test_dir.exists():
            shutil.rmtree(test_dir)


def main() -> None:
    """Run all packager/launcher combination tests."""
    print("Testing Embedded Launcher Functionality")
    print("=====================================")

    # Test combinations
    tests = [
        ("go", "go"),
        ("go", "rs"),
        ("rs", "go"),
        ("rs", "rs"),
        ("python", "go"),
        ("python", "rs"),
    ]

    results = []
    for packager, launcher in tests:
        try:
            success = test_packager_with_embedded_launcher(packager, launcher)
            results.append((packager, launcher, success))
        except Exception as e:
            print(f"\n❌ ERROR testing {packager}-{launcher}: {e}")
            results.append((packager, launcher, False))

    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    for packager, launcher, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status}: {packager} packager with {launcher} launcher")

    # Overall result
    all_passed = all(success for _, _, success in results)
    if all_passed:
        print("\n🎉 All tests passed!")
    else:
        print("\n⚠️  Some tests failed!")
        exit(1)


if __name__ == "__main__":
    main()
