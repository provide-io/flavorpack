"""
Cross-language compatibility tests for flavor packagers.

Tests that flavor (Python), flavor-go, and flavor-rs all produce
identical packages given the same inputs.
"""

import hashlib
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
import pytest
import shutil

from flavor.api import generate_keys
from flavor.compiler import ensure_go_binary


@pytest.fixture(scope="module")
def test_provider_dir(tmp_path_factory):
    """Create a test provider directory with all necessary files."""
    provider_dir = tmp_path_factory.mktemp("test_provider")
    
    # Create source directory and module
    src_dir = provider_dir / "src" / "test_provider"
    src_dir.mkdir(parents=True)
    
    # Create __init__.py
    (src_dir / "__init__.py").write_text('"""Test provider package."""')
    
    # Create main.py with entry point
    (src_dir / "main.py").write_text("""
def serve():
    print("Test provider v1.0.0 running!")
    
if __name__ == "__main__":
    serve()
""")
    
    # Create pyproject.toml
    pyproject_content = """
[build-system]
requires = ["setuptools>=61.0", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "test-provider"
version = "1.0.0"
description = "Test provider for cross-language compatibility"
requires-python = ">=3.9"
dependencies = ["attrs>=23.1.0"]

[project.scripts]
terraform-provider-test = "test_provider.main:serve"

[tool.pspf]
provider_name = "test"
entry_point = "test_provider.main:serve"

[tool.pspf.metadata]
provider_name = "test"
description = "Test provider for cross-language compatibility"

[tool.pspf.build]
python_version = "3.13"
dependencies = ["./src/test_provider", "attrs"]

[tool.setuptools.packages.find]
where = ["src"]
include = ["test_provider*"]
"""
    (provider_dir / "pyproject.toml").write_text(pyproject_content.strip())
    
    # Generate keys
    keys_dir = provider_dir / "keys"
    keys_dir.mkdir()
    generate_keys(keys_dir)
    
    # Update pyproject.toml with key paths
    pyproject = (provider_dir / "pyproject.toml").read_text()
    pyproject += f"""
[tool.pspf.signing]
private_key_path = "{keys_dir / 'provider-private.key'}"
public_key_path = "{keys_dir / 'provider-public.key'}"
curve = "P-256"
"""
    (provider_dir / "pyproject.toml").write_text(pyproject)
    
    return provider_dir


@pytest.fixture(scope="module")
def packager_binaries(request):
    """Ensure all packager binaries are available."""
    binaries = {}
    skip_rust = request.config.getoption("--skip-rust", False)
    skip_go = request.config.getoption("--skip-go", False)
    
    # Python flavor is available via module
    binaries["python"] = [sys.executable, "-m", "flavor"]
    
    # Ensure Go packager is built
    if not skip_go:
        go_packager = ensure_go_binary("flavor-go")
        binaries["go"] = [str(go_packager)]
    
    # Build Rust packager if Rust is available and not skipped
    if not skip_rust:
        rust_dir = Path(__file__).parent.parent.parent / "src" / "flavor" / "rust" / "flavor-packager-rs"
        if shutil.which("cargo") and rust_dir.exists():
            try:
                # Build Rust packager
                subprocess.run(
                    ["cargo", "build", "--release"],
                    cwd=rust_dir,
                    check=True,
                    capture_output=True
                )
                rust_binary = rust_dir / "target" / "release" / "flavor-rs"
                if rust_binary.exists():
                    binaries["rust"] = [str(rust_binary)]
            except subprocess.CalledProcessError:
                # Rust build failed, skip it
                pass
    
    return binaries


def compute_package_checksum(package_path):
    """Compute SHA256 checksum of a package file."""
    sha256 = hashlib.sha256()
    with open(package_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            sha256.update(chunk)
    return sha256.hexdigest()


def extract_package_metadata(package_path):
    """Extract metadata from a package without full extraction."""
    # This would need to be implemented based on the PSPF format
    # For now, return basic file info
    return {
        "size": os.path.getsize(package_path),
        "checksum": compute_package_checksum(package_path)
    }


class TestPackagerCompatibility:
    """Test that all packagers produce identical output."""
    
    def test_all_packagers_produce_same_package(self, test_provider_dir, packager_binaries):
        """Test that Python, Go, and Rust packagers produce identical packages."""
        if len(packager_binaries) < 2:
            pytest.skip("Need at least 2 packager implementations to compare")
        
        packages = {}
        
        for name, cmd in packager_binaries.items():
            with tempfile.TemporaryDirectory() as output_dir:
                output_dir = Path(output_dir)
                
                # Run packager
                if name == "python":
                    # Python flavor uses different command structure
                    full_cmd = cmd + ["package", "--manifest", str(test_provider_dir / "pyproject.toml")]
                else:
                    # Go and Rust packagers
                    full_cmd = cmd + [
                        "build",
                        "--out", str(output_dir / "test.flavor"),
                        "--payload-dir", str(test_provider_dir),
                        "--package-key", str(test_provider_dir / "keys" / "provider-private.key"),
                        "--public-key", str(test_provider_dir / "keys" / "provider-public.key"),
                        "--launcher-bin", str(ensure_go_binary("flavor-launcher-go"))
                    ]
                
                result = subprocess.run(
                    full_cmd,
                    cwd=test_provider_dir,
                    capture_output=True,
                    text=True
                )
                
                assert result.returncode == 0, f"{name} packager failed: {result.stderr}"
                
                # Find the output package
                if name == "python":
                    package_path = test_provider_dir / "dist" / "test.flavor"
                else:
                    package_path = output_dir / "test.flavor"
                
                assert package_path.exists(), f"{name} packager didn't create package"
                
                # Store package metadata
                packages[name] = {
                    "path": package_path,
                    "metadata": extract_package_metadata(package_path)
                }
        
        # Compare all packages
        checksums = {name: pkg["metadata"]["checksum"] for name, pkg in packages.items()}
        sizes = {name: pkg["metadata"]["size"] for name, pkg in packages.items()}
        
        # All checksums should be identical
        unique_checksums = set(checksums.values())
        assert len(unique_checksums) == 1, f"Packagers produced different packages: {checksums}"
        
        # Sizes might vary slightly due to timestamps, but should be very close
        size_values = list(sizes.values())
        max_size_diff = max(size_values) - min(size_values)
        assert max_size_diff < 1000, f"Package sizes vary too much: {sizes}"
    
    def test_packager_verify_commands(self, test_provider_dir, packager_binaries):
        """Test that all packagers can verify packages from any packager."""
        if len(packager_binaries) < 2:
            pytest.skip("Need at least 2 packager implementations to test cross-verification")
        
        # First, create packages with each packager
        packages = {}
        for name, cmd in packager_binaries.items():
            with tempfile.TemporaryDirectory() as output_dir:
                output_dir = Path(output_dir)
                
                if name == "python":
                    full_cmd = cmd + ["package", "--manifest", str(test_provider_dir / "pyproject.toml")]
                    subprocess.run(full_cmd, cwd=test_provider_dir, check=True, capture_output=True)
                    package_path = test_provider_dir / "dist" / "test.flavor"
                    # Copy to temp location
                    temp_package = output_dir / f"test_{name}.flavor"
                    shutil.copy2(package_path, temp_package)
                    packages[name] = temp_package
                else:
                    output_path = output_dir / f"test_{name}.flavor"
                    full_cmd = cmd + [
                        "build",
                        "--out", str(output_path),
                        "--payload-dir", str(test_provider_dir),
                        "--package-key", str(test_provider_dir / "keys" / "provider-private.key"),
                        "--public-key", str(test_provider_dir / "keys" / "provider-public.key"),
                        "--launcher-bin", str(ensure_go_binary("flavor-launcher-go"))
                    ]
                    subprocess.run(full_cmd, cwd=test_provider_dir, check=True, capture_output=True)
                    packages[name] = output_path
        
        # Now verify each package with each packager
        for creator_name, package_path in packages.items():
            for verifier_name, cmd in packager_binaries.items():
                if verifier_name == "python":
                    verify_cmd = cmd + ["verify", str(package_path)]
                else:
                    verify_cmd = cmd + ["verify", str(package_path)]
                
                result = subprocess.run(
                    verify_cmd,
                    capture_output=True,
                    text=True
                )
                
                assert result.returncode == 0, (
                    f"{verifier_name} packager failed to verify package "
                    f"created by {creator_name}: {result.stderr}"
                )


class TestPackagerConsistency:
    """Test that each packager is internally consistent."""
    
    @pytest.mark.parametrize("packager_name", ["python", "go", "rust"])
    def test_packager_deterministic(self, test_provider_dir, packager_binaries, packager_name):
        """Test that running the same packager twice produces identical output."""
        if packager_name not in packager_binaries:
            pytest.skip(f"{packager_name} packager not available")
        
        cmd = packager_binaries[packager_name]
        checksums = []
        
        for i in range(2):
            with tempfile.TemporaryDirectory() as output_dir:
                output_dir = Path(output_dir)
                
                if packager_name == "python":
                    full_cmd = cmd + ["package", "--manifest", str(test_provider_dir / "pyproject.toml")]
                    subprocess.run(full_cmd, cwd=test_provider_dir, check=True, capture_output=True)
                    package_path = test_provider_dir / "dist" / "test.flavor"
                else:
                    package_path = output_dir / "test.flavor"
                    full_cmd = cmd + [
                        "build",
                        "--out", str(package_path),
                        "--payload-dir", str(test_provider_dir),
                        "--package-key", str(test_provider_dir / "keys" / "provider-private.key"),
                        "--public-key", str(test_provider_dir / "keys" / "provider-public.key"),
                        "--launcher-bin", str(ensure_go_binary("flavor-launcher-go"))
                    ]
                    subprocess.run(full_cmd, cwd=test_provider_dir, check=True, capture_output=True)
                
                checksums.append(compute_package_checksum(package_path))
        
        # Both runs should produce identical output
        assert checksums[0] == checksums[1], (
            f"{packager_name} packager is not deterministic: {checksums}"
        )


# 📦🍜🧪🪄
