#!/usr/bin/env python3
"""Test cross-language verification - all languages should verify packages from each other."""

import subprocess
import tempfile
from pathlib import Path
import json
import os

# Helper binaries
PYTHON_BUILDER = "workenv/flavor_darwin_arm64/bin/flavor"
GO_BUILDER = "helpers/bin/flavor-go-builder"
RUST_BUILDER = "helpers/bin/flavor-rs-builder"

def create_test_manifest(temp_dir: Path) -> Path:
    """Create a test manifest for building."""
    manifest = {
        "name": "test-verify",
        "version": "1.0.0",
        "launcher": "go",
        "command": "echo 'Hello from test'",
        "slots": [
            {
                "path": str(temp_dir / "test.txt"),
                "name": "test",
                "encoding": "gzip",
                "purpose": "payload",
                "lifecycle": "persistent"
            }
        ]
    }
    
    # Create test file
    (temp_dir / "test.txt").write_text("Test content for verification")
    
    # Write manifest
    manifest_path = temp_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2))
    return manifest_path

def build_with_python(manifest_path: Path, output_path: Path, launcher: str = "go", key_seed: str = "test123"):
    """Build with Python builder."""
    # Create pyproject.toml from manifest
    manifest_data = json.loads(manifest_path.read_text())
    pyproject = f"""[project]
name = "{manifest_data['name']}"
version = "{manifest_data['version']}"

[tool.flavor]
name = "{manifest_data['name']}"
launcher = "{launcher}"
"""
    pyproject_path = manifest_path.parent / "pyproject.toml"
    pyproject_path.write_text(pyproject)
    
    cmd = [
        PYTHON_BUILDER, "package",
        "--manifest", str(pyproject_path),
        "--output", str(output_path),
        "--launcher", launcher,
        "--key-seed", key_seed,
        "--no-verify"  # We'll verify separately
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Python build failed: {result.stderr}")
        return False
    return True

def build_with_go(manifest_path: Path, output_path: Path, launcher: str = "go", key_seed: str = "test123"):
    """Build with Go builder."""
    cmd = [
        GO_BUILDER,
        "--manifest", str(manifest_path),
        "--output", str(output_path),
        "--launcher", launcher,
        "--key-seed", key_seed
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Go build failed: {result.stderr}")
        return False
    return True

def build_with_rust(manifest_path: Path, output_path: Path, launcher: str = "rust", key_seed: str = "test123"):
    """Build with Rust builder."""
    cmd = [
        RUST_BUILDER,
        "--manifest", str(manifest_path),
        "--output", str(output_path),
        "--launcher", launcher,
        "--key-seed", key_seed
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Rust build failed: {result.stderr}")
        return False
    return True

def verify_with_python(package_path: Path) -> bool:
    """Verify with Python."""
    from flavor.psp.format_2025 import PSPFReader
    try:
        with PSPFReader(package_path) as reader:
            result = reader.verify_integrity()
            return result['valid']
    except Exception as e:
        print(f"Python verification error: {e}")
        return False

def verify_with_go(package_path: Path) -> bool:
    """Verify with Go (using launcher CLI mode)."""
    env = os.environ.copy()
    env["FLAVOR_LAUNCHER_CLI"] = "true"
    cmd = [str(package_path), "verify"]
    result = subprocess.run(cmd, capture_output=True, text=True, env=env)
    return result.returncode == 0

def verify_with_rust(package_path: Path) -> bool:
    """Verify with Rust (using launcher CLI mode)."""
    env = os.environ.copy()
    env["FLAVOR_LAUNCHER_CLI"] = "true"
    cmd = [str(package_path), "verify"]
    result = subprocess.run(cmd, capture_output=True, text=True, env=env)
    return result.returncode == 0

def main():
    """Test cross-language verification."""
    
    builders = {
        "Python": build_with_python,
        "Go": build_with_go,
        "Rust": build_with_rust
    }
    
    verifiers = {
        "Python": verify_with_python,
        "Go": verify_with_go,
        "Rust": verify_with_rust
    }
    
    launchers = {
        "Python": "rust",  # Python uses rust launcher by default
        "Go": "go",
        "Rust": "rust"
    }
    
    results = []
    
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Test all builder -> verifier combinations
        for builder_name, build_func in builders.items():
            for verifier_name, verify_func in verifiers.items():
                
                # Create manifest
                manifest_path = create_test_manifest(temp_path)
                
                # Build package
                package_path = temp_path / f"test_{builder_name.lower()}_{verifier_name.lower()}.pspf"
                launcher = launchers[builder_name]
                
                print(f"\nTesting {builder_name} builder -> {verifier_name} verifier (launcher: {launcher})")
                
                if not build_func(manifest_path, package_path, launcher=launcher, key_seed="test123"):
                    results.append((builder_name, verifier_name, "BUILD_FAILED"))
                    continue
                
                if not package_path.exists():
                    results.append((builder_name, verifier_name, "NO_OUTPUT"))
                    continue
                
                # For Go/Rust verification, we need the package to have the right launcher
                if verifier_name in ["Go", "Rust"]:
                    # Rebuild with appropriate launcher for CLI verification
                    if verifier_name == "Go" and launcher != "go":
                        # Need Go launcher for Go CLI verification
                        package_path = temp_path / f"test_{builder_name.lower()}_go_launcher.pspf"
                        if not build_func(manifest_path, package_path, launcher="go", key_seed="test123"):
                            results.append((builder_name, verifier_name, "REBUILD_FAILED"))
                            continue
                    elif verifier_name == "Rust" and launcher != "rust":
                        # Need Rust launcher for Rust CLI verification
                        package_path = temp_path / f"test_{builder_name.lower()}_rust_launcher.pspf"
                        if not build_func(manifest_path, package_path, launcher="rust", key_seed="test123"):
                            results.append((builder_name, verifier_name, "REBUILD_FAILED"))
                            continue
                
                # Verify package
                if verify_func(package_path):
                    results.append((builder_name, verifier_name, "✅ PASS"))
                    print(f"  ✅ Verification successful")
                else:
                    results.append((builder_name, verifier_name, "❌ FAIL"))
                    print(f"  ❌ Verification failed")
    
    # Print results matrix
    print("\n" + "="*60)
    print("CROSS-LANGUAGE VERIFICATION MATRIX")
    print("="*60)
    print(f"{'Builder':<10} -> {'Verifier':<10} : Result")
    print("-"*60)
    
    for builder, verifier, result in results:
        print(f"{builder:<10} -> {verifier:<10} : {result}")
    
    # Check if all passed
    passed = sum(1 for _, _, r in results if "PASS" in r)
    total = len(results)
    
    print("-"*60)
    print(f"TOTAL: {passed}/{total} passed")
    
    if passed == total:
        print("✅ All cross-language verifications passed!")
        return 0
    else:
        print("❌ Some verifications failed")
        return 1

if __name__ == "__main__":
    exit(main())