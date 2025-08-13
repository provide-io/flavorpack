"""
Test that generates all flavor combinations from all packagers and launchers.
"""

import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import tarfile
import tempfile

import pytest

from flavor.api import generate_keys


def build_go_binary(cmd_path):
    """Build a Go binary if it doesn't exist."""
    binary_path = cmd_path / Path(cmd_path.name)
    if not binary_path.exists():
        try:
            subprocess.run(
                ["go", "build", "-o", str(binary_path), "."],
                cwd=cmd_path,
                check=True,
                capture_output=True
            )
        except subprocess.CalledProcessError:
            return None
    return binary_path if binary_path.exists() else None


def get_platform_info():
    """Get platform information for directory naming (Terraform-style)."""
    system = platform.system().lower()
    # Use Terraform-style OS names (darwin, linux, windows)
    
    machine = platform.machine().lower()
    if machine == "x86_64":
        machine = "amd64"
    elif machine == "aarch64":
        machine = "arm64"
    
    return f"{system}_{machine}"


@pytest.fixture(scope="module")
def all_packagers():
    """Get all available packagers."""
    packagers = {}
    
    # Python packager
    packagers["python"] = {
        "cmd": [sys.executable, "-m", "flavor"],
        "type": "manifest"
    }
    
    # Go packager (pspf-builder)
    go_cmd_path = Path(__file__).parent.parent.parent / "src/flavor/go/cmd/pspf-builder"
    go_bin = build_go_binary(go_cmd_path)
    if go_bin:
        packagers["go"] = {
            "cmd": [str(go_bin)],
            "type": "payload"
        }
    
    # Rust packager
    rust_dir = Path(__file__).parent.parent.parent / "src/flavor/rust/pspf-builder-rs"
    rust_bin = rust_dir / "target/release/pspf-builder-rs"
    if rust_bin.exists():
        packagers["rust"] = {
            "cmd": [str(rust_bin)],
            "type": "payload"
        }
    elif shutil.which("cargo"):
        # Try to build it
        try:
            subprocess.run(
                ["cargo", "build", "--release"],
                cwd=rust_dir,
                check=True,
                capture_output=True
            )
            if rust_bin.exists():
                packagers["rust"] = {
                    "cmd": [str(rust_bin)],
                    "type": "payload"
                }
        except:
            pass
    
    return packagers


@pytest.fixture(scope="module")
def all_launchers():
    """Get all available launchers."""
    launchers = {}
    
    # Go launcher (pspf-launcher)
    go_launcher_path = Path(__file__).parent.parent.parent / "src/flavor/go/cmd/pspf-launcher"
    go_launcher = build_go_binary(go_launcher_path)
    if go_launcher:
        launchers["go"] = str(go_launcher)
    
    # Rust launcher
    rust_dir = Path(__file__).parent.parent.parent / "src/flavor/rust/pspf-launcher-rs"
    rust_launcher = rust_dir / "target/release/pspf-launcher-rs"
    if rust_launcher.exists():
        launchers["rust"] = str(rust_launcher)
    elif shutil.which("cargo"):
        # Try to build it
        try:
            subprocess.run(
                ["cargo", "build", "--release"],
                cwd=rust_dir,
                check=True,
                capture_output=True
            )
            if rust_launcher.exists():
                launchers["rust"] = str(rust_launcher)
        except:
            pass
    
    return launchers


@pytest.fixture
def test_provider(tmp_path):
    """Create a test provider structure."""
    # Create source
    src_dir = tmp_path / "src/test_provider"
    src_dir.mkdir(parents=True)
    
    (src_dir / "__init__.py").write_text('"""Test provider package."""')
    (src_dir / "main.py").write_text("""
import json
import sys

def main():
    # Capture and print arguments to verify they're passed through
    args = sys.argv[1:] if len(sys.argv) > 1 else []
    print(json.dumps({
        "status": "running",
        "provider": "test_provider",
        "version": "1.0.0",
        "args": args,
        "argc": len(args)
    }))
    sys.exit(0)

if __name__ == "__main__":
    main()
""")
    
    # Create pyproject.toml
    (tmp_path / "pyproject.toml").write_text("""
[build-system]
requires = ["setuptools>=61.0"]
build-backend = "setuptools.build_meta"

[project]
name = "test-provider"
version = "1.0.0"
requires-python = ">=3.9"

[project.scripts]
test-provider = "test_provider.main:main"

[tool.flavor]
provider_name = "test"
entry_point = "test_provider.main:main"

[tool.flavor.build]
python_version = "3.11"
dependencies = ["./src/test_provider"]

[tool.setuptools.packages.find]
where = ["src"]
include = ["test_provider*"]
""")
    
    # Use the test keys from the project root
    project_root = Path(__file__).parent.parent.parent
    test_keys_dir = project_root / "test-keys"
    
    # Create symlink to test keys in the expected location
    keys_dir = tmp_path / "keys"
    if not keys_dir.exists():
        keys_dir.mkdir(parents=True)
        # Copy the test keys instead of generating new ones
        shutil.copy2(test_keys_dir / "flavor-private.key", keys_dir / "flavor-private.key")
        shutil.copy2(test_keys_dir / "flavor-public.key", keys_dir / "flavor-public.key")
    
    return tmp_path


def prepare_payload_for_go_rust(provider_dir, work_dir):
    """Prepare payload.tgz and other files for Go/Rust packagers."""
    # Create a Python environment and install the provider
    payload_dir = work_dir / "payload"
    
    # Create venv
    subprocess.run([
        "uv", "venv", str(payload_dir), "--python", "python3.11"
    ], check=True)
    
    # Install provider (non-editable for proper packaging)
    subprocess.run([
        "uv", "pip", "install",
        "--python", str(payload_dir / "bin/python"),
        str(provider_dir)
    ], check=True)
    
    # Create metadata inside the payload directory
    cache_metadata_dir = payload_dir / "metadata"
    cache_metadata_dir.mkdir()
    
    # Create config.json with full metadata
    config = {
        "provider_name": "test",
        "entry_point": "test_provider.main:main",
        "runtime": {
            "python_version": "3.11",
            "uv_version": "0.4.0"
        },
        "package": {
            "name": "test-provider",
            "version": "1.0.0"
        }
    }
    (cache_metadata_dir / "config.json").write_text(json.dumps(config, indent=2))
    
    # Create pspf.json
    pspf_metadata = {
        "format_version": "1.0.0",
        "created_at": "2025-08-09T00:00:00Z",
        "package_info": {
            "name": "test-provider",
            "version": "1.0.0",
            "language": "python",
            "language_version": "3.11"
        },
        "runtime_requirements": {
            "python": "3.11",
            "uv": "0.4.0"
        }
    }
    (cache_metadata_dir / "pspf.json").write_text(json.dumps(pspf_metadata, indent=2))
    
    # Create payload.tgz with gzip -9
    payload_tgz = work_dir / "payload.tgz"
    with tarfile.open(payload_tgz, "w:gz", compresslevel=9) as tar:
        tar.add(payload_dir, arcname="cache")
    
    # Copy UV binary if needed
    uv_bin = shutil.which("uv")
    if uv_bin:
        shutil.copy2(uv_bin, work_dir / "uv")
    
    # Pre-compute signature for Go/Rust builders
    import hashlib
    hasher = hashlib.sha256()
    with open(payload_tgz, "rb") as f:
        while chunk := f.read(8192):
            hasher.update(chunk)
    payload_hash = hasher.digest()
    
    # Get project root for key paths
    project_root = Path(__file__).parent.parent.parent
    private_key_path = project_root / "test-keys/flavor-private.key"
    
    # Sign using openssl (simplified for test)
    result = subprocess.run([
        "openssl", "dgst", "-sha256", "-sign", str(private_key_path)
    ], input=payload_hash, capture_output=True, check=True)
    
    signature_path = work_dir / "signature.bin"
    signature_path.write_bytes(result.stdout)
    
    return payload_tgz


class TestAllFlavorCombinations:
    """Test all combinations of packagers and launchers."""
    
    def test_generate_all_flavors(self, test_provider, all_packagers, all_launchers):
        """Generate flavors using all packager and launcher combinations."""
        if not all_packagers:
            pytest.skip("No packagers available")
        if not all_launchers:
            pytest.skip("No launchers available")
        
        # Get project root for key paths
        project_root = Path(__file__).parent.parent.parent
        
        # Determine output directory
        workenv_dir = Path.cwd() / "workenv"
        if not workenv_dir.exists():
            workenv_dir = Path.cwd()
        
        platform_dir = get_platform_info()
        output_dir = workenv_dir / "flavors" / platform_dir
        output_dir.mkdir(parents=True, exist_ok=True)
        
        results = {}
        
        for packager_name, packager_info in all_packagers.items():
            for launcher_name, launcher_path in all_launchers.items():
                combo = f"{packager_name}-packager_{launcher_name}-launcher"
                output_path = output_dir / f"test-provider_{combo}"
                
                # Remove existing file if it exists
                if output_path.exists():
                    output_path.unlink()
                
                print(f"\n=== Building {combo} ===")
                
                try:
                    if packager_info["type"] == "manifest":
                        # Python packager supports launcher selection and output path
                        cmd = packager_info["cmd"] + [
                            "package",
                            "--manifest", str(test_provider / "pyproject.toml"),
                            "--launcher", launcher_name,
                            "--output", str(output_path)
                        ]
                        
                        result = subprocess.run(
                            cmd,
                            capture_output=True,
                            text=True
                        )
                    else:
                        # Go/Rust packager - needs manifest.json
                        with tempfile.TemporaryDirectory() as work_dir:
                            work_dir = Path(work_dir)
                            prepare_payload_for_go_rust(test_provider, work_dir)
                            
                            # Create manifest.json for pspf-builder
                            manifest_data = {
                                "name": "test-provider",
                                "version": "1.0.0",
                                "description": "Test provider",
                                "command": "{cache}/bin/python3 -m test_provider.main",
                                "environment": {
                                    "PYTHONPATH": "{cache}/lib/python3.11/site-packages"
                                },
                                "slots": [
                                    {
                                        "name": "payload",
                                        "path": str(work_dir / "payload.tgz"),
                                        "compression": "gzip",
                                        "purpose": "payload",
                                        "lifecycle": "persistent",
                                        "extract_to": "."
                                    }
                                ]
                            }
                            
                            manifest_path = work_dir / "manifest.json"
                            with open(manifest_path, "w") as f:
                                json.dump(manifest_data, f, indent=2)
                            
                            # Copy the launcher to the working directory for pspf-builder
                            if packager_name in ["go", "rust"]:
                                # Map launcher names to expected filenames
                                launcher_map = {
                                    "go": "pspf-launcher",
                                    "rust": "pspf-launcher-rust",
                                    "python": "pspf-launcher-python",
                                    "node": "pspf-launcher-node"
                                }
                                launcher_filename = launcher_map.get(launcher_name, "pspf-launcher")
                                launcher_copy = work_dir / launcher_filename
                                shutil.copy2(launcher_path, launcher_copy)
                                # Make it executable
                                launcher_copy.chmod(0o755)
                            
                            cmd = packager_info["cmd"] + [
                                "--manifest", str(manifest_path),
                                "--output", str(output_path),
                                "--launcher", launcher_name
                            ]
                            
                            result = subprocess.run(
                                cmd,
                                capture_output=True,
                                text=True,
                                cwd=work_dir
                            )
                    
                    if result.returncode == 0:
                        # Make the output file executable
                        output_path.chmod(0o755)
                        
                        # Test the binary without args
                        test_result = subprocess.run(
                            [str(output_path)],
                            capture_output=True,
                            text=True,
                            timeout=10
                        )
                        
                        # Test with arguments to ensure they're passed through
                        test_args_result = subprocess.run(
                            [str(output_path), "--test-arg", "value", "positional"],
                            capture_output=True,
                            text=True,
                            timeout=10
                        )
                        
                        success = test_result.returncode == 0
                        args_passed = False
                        
                        if success:
                            try:
                                output_json = json.loads(test_result.stdout)
                                success = output_json.get("status") == "running"
                                
                                # Check if args were passed through correctly
                                if test_args_result.returncode == 0:
                                    args_output = json.loads(test_args_result.stdout)
                                    passed_args = args_output.get("args", [])
                                    args_passed = (
                                        "--test-arg" in passed_args and
                                        "value" in passed_args and
                                        "positional" in passed_args
                                    )
                                    if not args_passed:
                                        print(f"   ⚠️  Args not passed correctly: {passed_args}")
                            except:
                                success = False
                        
                        results[combo] = {
                            "built": True,
                            "runs": success,
                            "args_passed": args_passed,
                            "path": str(output_path),
                            "size": output_path.stat().st_size if output_path.exists() else 0
                        }
                        
                        print(f"✅ {combo}: Built and {'runs' if success else 'FAILS TO RUN'}")
                        if not success:
                            print(f"   Exit code: {test_result.returncode}")
                            print(f"   Stdout: {test_result.stdout[:200]}")
                            print(f"   Stderr: {test_result.stderr[:200]}")
                    else:
                        results[combo] = {
                            "built": False,
                            "error": result.stderr
                        }
                        print(f"❌ {combo}: Build failed")
                        print(f"   Command: {' '.join(cmd)}")
                        print(f"   Stderr: {result.stderr}")
                        print(f"   Stdout: {result.stdout}")
                
                except Exception as e:
                    results[combo] = {
                        "built": False,
                        "error": str(e)
                    }
                    print(f"❌ {combo}: Exception - {str(e)}")
        
        # Summary
        print("\n=== SUMMARY ===")
        print(f"Output directory: {output_dir}")
        print(f"Total combinations: {len(all_packagers) * len(all_launchers)}")
        
        successful = sum(1 for r in results.values() if r.get("built") and r.get("runs"))
        built = sum(1 for r in results.values() if r.get("built"))
        
        print(f"Successfully built: {built}")
        print(f"Successfully run: {successful}")
        
        for combo, result in results.items():
            if result.get("built"):
                status = "✅ Runs" if result.get("runs") else "⚠️  Built but fails"
                size = result.get("size", 0) / (1024 * 1024)
                args_status = " (args ✓)" if result.get("args_passed") else " (args ✗)"
                print(f"  {combo}: {status}{args_status} ({size:.1f} MB)")
            else:
                print(f"  {combo}: ❌ Build failed")
        
        # At least one should work
        assert successful > 0, "No flavor combinations worked successfully"
        
        # Save results
        results_file = output_dir / "test_results.json"
        results_file.write_text(json.dumps(results, indent=2))
        
        return results