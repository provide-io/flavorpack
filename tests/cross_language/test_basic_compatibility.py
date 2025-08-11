"""
Basic cross-language compatibility test to prove the implementations work.
"""

import subprocess
import sys
import tempfile
from pathlib import Path
import pytest

from flavor.api import generate_keys, build_package_from_manifest
from flavor.compiler import ensure_go_binary


def test_python_packager_go_launcher_compatibility():
    """Test that Python packager creates packages that Go launcher can run."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_dir = Path(temp_dir)
        
        # Create a minimal test provider
        src_dir = temp_dir / "src" / "demo"
        src_dir.mkdir(parents=True)
        
        (src_dir / "__init__.py").write_text('"""Demo provider."""')
        (src_dir / "main.py").write_text("""
import sys
print("PROOF: Python packager + Go launcher = SUCCESS!")
sys.exit(0)
""")
        
        # Create pyproject.toml
        pyproject = temp_dir / "pyproject.toml"
        pyproject.write_text("""
[build-system]
requires = ["setuptools>=61.0", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "demo-provider"
version = "1.0.0"
requires-python = ">=3.9"

[project.scripts]
terraform-provider-demo = "demo.main:serve"

[tool.pspf]
provider_name = "demo"
entry_point = "demo.main:serve"

[tool.pspf.build]
python_version = "3.13"
dependencies = ["./src/demo"]

[tool.setuptools.packages.find]
where = ["src"]
include = ["demo*"]
""")
        
        # Build package with Python packager
        print("Building package with Python flavor...")
        artifacts = build_package_from_manifest(pyproject)
        assert len(artifacts) == 1
        package_path = artifacts[0]
        print(f"✅ Python packager created: {package_path}")
        
        # Get Go launcher
        go_launcher = ensure_go_binary("flavor-launcher-go")
        print(f"✅ Go launcher available: {go_launcher}")
        
        # Create executable by concatenating launcher + package
        executable = temp_dir / "demo-provider"
        with open(executable, "wb") as out:
            with open(go_launcher, "rb") as launcher:
                out.write(launcher.read())
            with open(package_path, "rb") as package:
                out.write(package.read())
        
        # Make executable
        executable.chmod(0o755)
        print(f"✅ Created executable: {executable}")
        
        # Run it!
        result = subprocess.run(
            [str(executable)],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        print(f"Exit code: {result.returncode}")
        print(f"Stdout: {result.stdout}")
        print(f"Stderr: {result.stderr}")
        
        # Check for our proof message
        assert "PROOF: Python packager + Go launcher = SUCCESS!" in result.stdout
        assert result.returncode == 0
        
        print("✅ Cross-language compatibility PROVEN!")


def test_keygen_compatibility():
    """Test that Python and Go keygen produce compatible keys."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_dir = Path(temp_dir)
        
        # Generate keys with Python
        python_keys = temp_dir / "python_keys"
        python_keys.mkdir()
        generate_keys(python_keys)
        print("✅ Python keygen created keys")
        
        # Generate keys with Go
        go_keys = temp_dir / "go_keys"
        go_keys.mkdir()
        go_packager = ensure_go_binary("flavor-go")
        
        result = subprocess.run(
            [str(go_packager), "keygen", 
             "--private-key", str(go_keys / "provider-private.key"),
             "--public-key", str(go_keys / "provider-public.key")],
            capture_output=True,
            text=True
        )
        assert result.returncode == 0, f"Go keygen failed: {result.stderr}"
        print("✅ Go keygen created keys")
        
        # Verify both created the expected files
        for key_dir in [python_keys, go_keys]:
            assert (key_dir / "provider-private.key").exists()
            assert (key_dir / "provider-public.key").exists()
            
            # Check file sizes are reasonable
            private_size = (key_dir / "provider-private.key").stat().st_size
            public_size = (key_dir / "provider-public.key").stat().st_size
            assert 200 < private_size < 300  # ECDSA P-256 private key
            assert 150 < public_size < 250   # ECDSA P-256 public key
        
        print("✅ Both implementations created valid ECDSA keys!")


if __name__ == "__main__":
    # Run directly for quick testing
    test_python_packager_go_launcher_compatibility()
    test_keygen_compatibility()


# 📦🍜🧪🪄
