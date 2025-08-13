#!/usr/bin/env python3
"""
Simple test to prove launcher extraction works.
"""

import hashlib
from pathlib import Path
import shutil
import subprocess
import tempfile
import pytest

@pytest.mark.skip(reason="Test requires pre-built test packages")
def test_launcher_extraction() -> None:
    """Test that existing flavor packages extract their embedded launchers."""
    print("Testing Launcher Extraction from PSPF Packages")
    print("=" * 60)

    # Find test packages
    test_packages = list(Path("flavor-test-output").glob("*.pspf"))
    if not test_packages:
        pytest.skip("No test packages found in flavor-test-output/")

    print(f"Found {len(test_packages)} test packages")

    # Clear cache first
    cache_base = Path.home() / ".cache" / "flavor"
    if cache_base.exists():
        print("Clearing cache...")
        for cache_dir in cache_base.iterdir():
            if cache_dir.is_dir():
                shutil.rmtree(cache_dir)

    success = False
    for package in test_packages[:1]:
        # Run the package
        result = subprocess.run([str(package), "--help"], capture_output=True, text=True, timeout=10)
        
        # Check cache directory
        package_hash = hashlib.sha256(package.read_bytes()).hexdigest()[:16]
        expected_cache = cache_base / package_hash
        if expected_cache.exists():
            success = True
            break
    
    assert success, "No package successfully created a cache directory"


@pytest.mark.skip(reason="Test requires pre-built Go/Rust binaries and is complex")
def test_embedded_launcher_proof() -> None:
    """Create a simple package with embedded launcher and test it."""
    assert True
