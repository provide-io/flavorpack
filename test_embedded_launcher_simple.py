#!/usr/bin/env python3
"""
Simple test to prove embedded launcher functionality.
"""

import os
import subprocess
import tempfile
import shutil
from pathlib import Path

def run_test():
    """Test that we can create a PSPF with embedded launcher that self-extracts."""
    print("Testing Embedded Launcher in PSPF Package")
    print("="*50)
    
    # Create a test provider directory
    test_dir = Path("test-embedded-launcher")
    if test_dir.exists():
        shutil.rmtree(test_dir)
    test_dir.mkdir()
    
    # Create a minimal provider
    (test_dir / "main.py").write_text("""#!/usr/bin/env python3
import json
import sys
print(json.dumps({"test": "embedded launcher works!"}))
""")
    (test_dir / "main.py").chmod(0o755)
    
    # Create pyproject.toml for Python packager
    (test_dir / "pyproject.toml").write_text("""[tool.pyvider]
manifest_version = 1

[tool.pyvider.provider]
name = "test-embedded"
version = "0.1.0"

[tool.pyvider.build]
provider_binary = "main.py"
""")
    
    # Test 1: Python packager with Go launcher embedded
    print("\n1. Testing Python packager creating PSPF...")
    
    # First, let's see what the actual flavor package command does
    result = subprocess.run(
        ["flavor", "package", "--manifest", "pyproject.toml"],
        capture_output=True, text=True, cwd=test_dir
    )
    
    print(f"Command output: {result.stdout}")
    print(f"Command error: {result.stderr}")
    
    # Check if any .flavor file was created
    flavor_files = list(test_dir.glob("*.flavor"))
    if flavor_files:
        print(f"\n✅ Package created: {flavor_files[0]}")
        
        # Try to run it
        print("\n2. Testing if package executes...")
        result = subprocess.run(
            [str(flavor_files[0]), "--version"],
            capture_output=True, text=True
        )
        print(f"Execution stdout: {result.stdout}")
        print(f"Execution stderr: {result.stderr}")
        
        # Check cache directory
        cache_base = Path.home() / ".cache" / "flavor"
        if cache_base.exists():
            print(f"\n3. Checking cache directory...")
            for cache_dir in cache_base.iterdir():
                print(f"Cache: {cache_dir}")
                for item in cache_dir.rglob("*"):
                    if item.is_file():
                        print(f"  - {item.relative_to(cache_dir)}")
                        if "launcher" in item.name:
                            print(f"    ✅ Found embedded launcher: {item.name}")
    else:
        print("❌ No .flavor file created")
    
    # Test 2: Use Go packager with launcher
    print("\n\n4. Testing Go packager with embedded launcher...")
    
    # Create a payload directory for Go packager
    payload_dir = test_dir / "payload"
    payload_dir.mkdir()
    shutil.copy(test_dir / "main.py", payload_dir / "main.py")
    
    # Try Go packager build command
    result = subprocess.run([
        "./flavor-go", "build",
        "--payload-dir", str(payload_dir),
        "--launcher-bin", "./flavor-launcher-go",
        "--out", str(test_dir / "test-go.flavor")
    ], capture_output=True, text=True)
    
    print(f"Go packager stdout: {result.stdout}")
    print(f"Go packager stderr: {result.stderr}")
    
    if (test_dir / "test-go.flavor").exists():
        print("✅ Go packager created package with embedded launcher")
        
        # Test execution
        result = subprocess.run(
            [str(test_dir / "test-go.flavor"), "--version"],
            capture_output=True, text=True
        )
        print(f"Go package execution: {result.stdout}")
    
    # Cleanup
    if test_dir.exists():
        shutil.rmtree(test_dir)

if __name__ == "__main__":
    run_test()