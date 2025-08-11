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
from flavor.compiler import ensure_go_binary



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
    
    # Go packager
    try:
        go_bin = ensure_go_binary("flavor-go")
        packagers["go"] = {
            "cmd": [str(go_bin)],
            "type": "payload"
        }
    except:
        pass
    
    # Rust packager
    rust_dir = Path(__file__).parent.parent.parent / "src/flavor/rust/flavor-packager-rs"
    rust_bin = rust_dir / "target/release/flavor-rs"
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
    
    # Go launcher
    try:
        go_launcher = ensure_go_binary("flavor-launcher-go")
        launchers["go"] = str(go_launcher)
    except:
        pass
    
    # Rust launcher
    rust_dir = Path(__file__).parent.parent.parent / "src/flavor/rust/flavor-launcher-rs"
    rust_launcher = rust_dir / "target/release/flavor-launcher-rs"
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
    print(json.dumps({
        "status": "running",
        "provider": "test_provider",
        "version": "1.0.0"
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
python_version = "3.13"
dependencies = ["./src/test_provider"]

[tool.setuptools.packages.find]
where = ["src"]
include = ["test_provider*"]
""")
    
    # Generate keys
    keys_dir = tmp_path / "keys"
    generate_keys(keys_dir)
    
    return tmp_path


def prepare_payload_for_go_rust(provider_dir, work_dir):
    """Prepare payload.tgz and other files for Go/Rust packagers."""
    # Create a Python environment and install the provider
    payload_dir = work_dir / "payload"
    
    # Create venv
    subprocess.run([
        "uv", "venv", str(payload_dir), "--python", "python3.13"
    ], check=True)
    
    # Install provider
    subprocess.run([
        "uv", "pip", "install",
        "--python", str(payload_dir / "bin/python"),
        "-e", str(provider_dir)
    ], check=True)
    
    # Create metadata inside the payload directory
    cache_metadata_dir = payload_dir / "metadata"
    cache_metadata_dir.mkdir()
    
    # Create config.json with full metadata
    config = {
        "provider_name": "test",
        "entry_point": "test_provider.main:main",
        "runtime": {
            "python_version": "3.13",
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
            "language_version": "3.13"
        },
        "runtime_requirements": {
            "python": "3.13",
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
    
    return payload_tgz


class TestAllFlavorCombinations:
    """Test all combinations of packagers and launchers."""
    
    def test_generate_all_flavors(self, test_provider, all_packagers, all_launchers):
        """Generate flavors using all packager and launcher combinations."""
        if not all_packagers:
            pytest.skip("No packagers available")
        if not all_launchers:
            pytest.skip("No launchers available")
        
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
                
                print(f"\n=== Building {combo} ===")
                
                try:
                    if packager_info["type"] == "manifest":
                        # Python packager doesn't support launcher selection yet
                        # It will use the default Go launcher
                        cmd = packager_info["cmd"] + [
                            "package",
                            "--manifest", str(test_provider / "pyproject.toml")
                        ]
                        
                        result = subprocess.run(
                            cmd,
                            capture_output=True,
                            text=True
                        )
                        
                        # Move the output file to the expected location
                        if result.returncode == 0:
                            # Find the output file - it could have different names
                            dist_dir = test_provider / "dist"
                            if dist_dir.exists():
                                for file in dist_dir.glob("*.flavor"):
                                    shutil.move(str(file), str(output_path))
                                    break
                    else:
                        # Go/Rust packager - needs payload.tgz
                        with tempfile.TemporaryDirectory() as work_dir:
                            work_dir = Path(work_dir)
                            prepare_payload_for_go_rust(test_provider, work_dir)
                            
                            cmd = packager_info["cmd"] + [
                                "build",
                                "--out", str(output_path),
                                "--payload-dir", str(work_dir / "payload"),
                                "--package-key", str(test_provider / "keys/provider-private.key"),
                                "--public-key", str(test_provider / "keys/provider-public.key"),
                                "--launcher-bin", launcher_path
                            ]
                            
                            result = subprocess.run(
                                cmd,
                                capture_output=True,
                                text=True,
                                cwd=work_dir
                            )
                    
                    if result.returncode == 0:
                        # Test the binary
                        test_result = subprocess.run(
                            [str(output_path)],
                            capture_output=True,
                            text=True,
                            timeout=10
                        )
                        
                        success = test_result.returncode == 0
                        if success:
                            try:
                                output_json = json.loads(test_result.stdout)
                                success = output_json.get("status") == "running"
                            except:
                                success = False
                        
                        results[combo] = {
                            "built": True,
                            "runs": success,
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
                        print(f"❌ {combo}: Build failed - {result.stderr[:100]}")
                
                except Exception as e:
                    results[combo] = {
                        "built": False,
                        "error": str(e)
                    }
                    print(f"❌ {combo}: Exception - {str(e)[:100]}")
        
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
                print(f"  {combo}: {status} ({size:.1f} MB)")
            else:
                print(f"  {combo}: ❌ Build failed")
        
        # At least one should work
        assert successful > 0, "No flavor combinations worked successfully"
        
        # Save results
        results_file = output_dir / "test_results.json"
        results_file.write_text(json.dumps(results, indent=2))
        
        return results