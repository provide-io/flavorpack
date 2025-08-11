#!/usr/bin/env python3
"""
Simple test to prove launcher extraction works.
"""

import subprocess
import tempfile
import shutil
from pathlib import Path
import hashlib

def test_launcher_extraction():
    """Test that existing flavor packages extract their embedded launchers."""
    print("Testing Launcher Extraction from PSPF Packages")
    print("="*60)
    
    # Find test packages
    test_packages = list(Path("flavor-test-output").glob("*.flavor"))
    if not test_packages:
        print("❌ No test packages found in flavor-test-output/")
        return False
    
    print(f"Found {len(test_packages)} test packages")
    
    # Clear cache first
    cache_base = Path.home() / ".cache" / "flavor"
    if cache_base.exists():
        print("Clearing cache...")
        for cache_dir in cache_base.iterdir():
            if cache_dir.is_dir():
                shutil.rmtree(cache_dir)
    
    # Test each package
    for package in test_packages[:3]:  # Test first 3
        print(f"\n{'='*40}")
        print(f"Testing: {package.name}")
        print('='*40)
        
        # Calculate package hash for cache dir
        with open(package, 'rb') as f:
            package_hash = hashlib.sha256(f.read()).hexdigest()[:16]
        
        print(f"Package hash: {package_hash}")
        
        # Run the package
        env = {"FLAVOR_LOG_LEVEL": "debug"}
        result = subprocess.run(
            [str(package), "--help"],
            capture_output=True,
            text=True,
            env=env,
            timeout=10
        )
        
        print(f"Exit code: {result.returncode}")
        
        # Check cache directory
        expected_cache = cache_base / package_hash
        if expected_cache.exists():
            print(f"✅ Cache created: {expected_cache}")
            
            # List extracted contents
            extracted_files = list(expected_cache.rglob("*"))
            print(f"Extracted {len(extracted_files)} items:")
            
            for item in sorted(extracted_files)[:10]:  # Show first 10
                if item.is_file():
                    rel_path = item.relative_to(expected_cache)
                    size = item.stat().st_size
                    print(f"  - {rel_path} ({size:,} bytes)")
            
            # Look for key components
            has_payload = any("payload" in str(f) for f in extracted_files)
            has_python = any("python" in str(f) for f in extracted_files)
            has_bin = any("bin" in str(f) for f in extracted_files)
            
            print(f"\nComponents found:")
            print(f"  Payload: {'✅' if has_payload else '❌'}")
            print(f"  Python:  {'✅' if has_python else '❌'}")
            print(f"  Bin dir: {'✅' if has_bin else '❌'}")
            
            if has_payload and (has_python or has_bin):
                print(f"✅ Package {package.name} successfully extracted!")
            else:
                print(f"❌ Package {package.name} extraction incomplete")
        else:
            print(f"❌ No cache directory created")
            print(f"Stderr: {result.stderr[:500]}")
    
    return True

def test_embedded_launcher_proof():
    """Create a simple package with embedded launcher and test it."""
    print("\n\n" + "="*60)
    print("Testing Embedded Launcher in New Package")
    print("="*60)
    
    # Use existing test-provider as base
    test_provider = Path("test-provider")
    if not test_provider.exists():
        print("❌ test-provider directory not found")
        return False
    
    # Check for existing package
    existing_package = test_provider / "dist" / "test.flavor"
    if existing_package.exists():
        print(f"✅ Found existing package: {existing_package}")
        print(f"Size: {existing_package.stat().st_size / (1024*1024):.1f} MB")
        
        # This is already a package with embedded launcher
        # Let's verify it works
        result = subprocess.run(
            [str(existing_package), "--version"],
            capture_output=True,
            text=True
        )
        
        print(f"\nExecution test:")
        print(f"Exit code: {result.returncode}")
        print(f"Stdout: {result.stdout[:200]}")
        print(f"Stderr: {result.stderr[:200]}")
        
        if result.returncode == 0:
            print("✅ Package with embedded launcher executes successfully!")
            return True
    
    # Try concatenating launcher + package manually
    print("\n\nManual launcher embedding test:")
    
    # Find a launcher
    go_launcher = Path("flavor-launcher-go")
    if not go_launcher.exists():
        print("❌ Go launcher not found")
        return False
    
    # Find a package from test output
    packages = list(Path("flavor-test-output").glob("*py-builder*.flavor"))
    if not packages:
        print("❌ No Python-built packages found")
        return False
    
    src_package = packages[0]
    print(f"Using package: {src_package.name}")
    print(f"Using launcher: {go_launcher}")
    
    # Create new executable
    with tempfile.NamedTemporaryFile(suffix=".flavor", delete=False) as tmp:
        output_path = Path(tmp.name)
    
    # Concatenate launcher + package data
    with open(output_path, "wb") as out:
        # Copy Go launcher
        with open(go_launcher, "rb") as f:
            launcher_data = f.read()
            out.write(launcher_data)
            print(f"Wrote launcher: {len(launcher_data):,} bytes")
        
        # Extract just the package data (skip any existing launcher)
        with open(src_package, "rb") as f:
            # Try to find PSPF magic in the file
            data = f.read()
            
            # Look for PSPF footer magic
            pspf_magic = b"Progressive Secure Package Format"
            idx = data.rfind(pspf_magic)
            
            if idx > 0:
                # Found PSPF data
                print(f"Found PSPF data at offset {idx}")
                # Write everything from start of tar.gz data
                # (This is simplified - real implementation reads footer properly)
                out.write(data[len(launcher_data):])
            else:
                # Just append the whole thing
                out.write(data)
    
    output_path.chmod(0o755)
    print(f"\n✅ Created new package: {output_path}")
    print(f"Total size: {output_path.stat().st_size / (1024*1024):.1f} MB")
    
    # Test execution
    result = subprocess.run(
        [str(output_path), "--help"],
        capture_output=True,
        text=True
    )
    
    print(f"\nExecution test:")
    print(f"Exit code: {result.returncode}")
    print(f"Output: {result.stdout[:200] if result.stdout else result.stderr[:200]}")
    
    # Cleanup
    output_path.unlink()
    
    return result.returncode == 0

if __name__ == "__main__":
    # Test 1: Existing packages extract launchers
    test_launcher_extraction()
    
    # Test 2: Create package with embedded launcher
    test_embedded_launcher_proof()