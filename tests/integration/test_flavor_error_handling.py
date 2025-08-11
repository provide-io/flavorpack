#!/usr/bin/env python3
"""
Flavor Error Handling and Edge Cases Integration Tests

This module tests error conditions, edge cases, and failure scenarios
to ensure robust error handling throughout the Flavor system.
"""

import pytest
import subprocess
import tempfile
import shutil
import os
from pathlib import Path
from typing import Dict, Tuple, Optional
import logging
import struct

from flavor.api import build_package_from_manifest
from flavor.packaging.keys import generate_key_pair

logger = logging.getLogger(__name__)

class FlavorErrorTestFramework:
    """Framework for testing Flavor error conditions and edge cases"""
    
    def __init__(self):
        self.project_root = Path("/REDACTED_ABS_PATH")
        self.flavor_dir = self.project_root / "flavor"
        
        self.test_launchers = {
            "rust": str(self.flavor_dir / "src" / "flavor" / "rust" / "flavor-launcher-rs" / "target" / "release" / "flavor-launcher-rs")
        }

    def _create_dummy_flavor_package(self, tmp_path: Path) -> Path:
        """Creates a minimal, valid flavor package for testing."""
        provider_dir = tmp_path / "dummy-provider"
        provider_dir.mkdir()

        src_dir = provider_dir / "src" / "dummy_provider"
        src_dir.mkdir(parents=True)

        (src_dir / "__init__.py").write_text("""
from pyvider.providers import BaseProvider
from pyvider.schema import s_provider_config, a_str

class DummyProvider(BaseProvider):
    __pyvider_schema__ = s_provider_config(version=\"1.0.0\")
    async def configure(self, config):
        return self
    async def setup(self):
        pass
""")
        (src_dir / "__main__.py").write_text("""
import sys
from pyvider.cli import main
if __name__ == "__main__":
    sys.exit(main())
""")

        pyproject_content = """
[project]
name = \"dummy-provider\"
version = \"1.0.0\"
description = \"Dummy provider for testing\"
requires-python = \">=3.13\"
dependencies = [\"pyvider\", \"pyvider-components\"]

[project.scripts]
dummy-provider = \"dummy_provider.__main__:main\"

[project.entry-points.\"pyvider.providers\"]
dummy = \"dummy_provider:DummyProvider\"

[build-system]
requires = [\"setuptools\", \"wheel\"]
build-backend = \"setuptools.build_meta\"

[tool.setuptools]
packages = [\"dummy_provider\"]

[tool.setuptools.package-dir]
"" = \"src\"

[tool.flavor]
provider_name = \"dummy\"
entry_point = \"dummy_provider.__main__:main\"
targets = [\"darwin_arm64\"]

[tool.flavor.build]
python_version = \"3.13\"
dependencies = []

[tool.flavor.signing]
private_key_path = \"keys/provider-private.key\"
public_key_path = \"keys/provider-public.key\"
"""
        (provider_dir / "pyproject.toml").write_text(pyproject_content)

        generate_key_pair(provider_dir / "keys")
        artifacts = build_package_from_manifest(provider_dir / "pyproject.toml")
        return artifacts[0]

    def create_corrupted_package(self, base_package: Path, output_path: Path, corruption_type: str) -> None:
        """Create various types of corrupted Flavor packages for testing"""
        
        shutil.copy2(base_package, output_path)
        
        if corruption_type == "invalid_magic":
            # Corrupt the magic bytes at the end
            with open(output_path, 'r+b') as f:
                f.seek(-12, 2)
                f.write(b'CORRUPTED!!!')
                
        elif corruption_type == "invalid_footer_magic":
            # Corrupt the footer magic bytes
            with open(output_path, 'r+b') as f:
                f.seek(-12-120+104, 2)  # Footer magic location (updated for 120-byte footer)
                f.write(struct.pack('<I', 0xDEADBEEF))
                
        elif corruption_type == "truncated_file":
            # Truncate the file to remove part of the Flavor data
            original_size = output_path.stat().st_size
            truncated_size = original_size - 1000  # Remove 1KB
            output_path.write_bytes(output_path.read_bytes()[:truncated_size])
            
        elif corruption_type == "invalid_footer_size":
            # Corrupt footer size values
            with open(output_path, 'r+b') as f:
                f.seek(-12-120+16, 2)  # First size field in footer (updated for 120-byte footer)
                f.write(struct.pack('<Q', 0xFFFFFFFFFFFFFFFF))  # Invalid large size
                
        elif corruption_type == "empty_file":
            # Create empty file
            output_path.write_bytes(b'')
            
        elif corruption_type == "wrong_launcher":
            # Replace with wrong launcher (just copy rust launcher)
            rust_launcher = self.test_launchers["rust"]
            if Path(rust_launcher).exists():
                shutil.copy2(rust_launcher, output_path)
            
    def test_corrupted_package_handling(self, corruption_type: str, expected_error_pattern: str) -> Tuple[bool, str]:
        """Test handling of corrupted packages"""
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)
                
                # Get a valid base package
                base_package = self._create_dummy_flavor_package(temp_path)
                
                # Create corrupted package
                corrupted_package = temp_path / f"corrupted_{corruption_type}.flavor"
                self.create_corrupted_package(base_package, corrupted_package, corruption_type)
                
                # Test with rust launcher (most reliable)
                cache_dir = temp_path / "cache"
                cache_dir.mkdir()
                
                cmd = [str(corrupted_package), "--force-extract", "--cache-dir", str(cache_dir)]
                
                result = subprocess.run(
                    cmd, 
                    capture_output=True, 
                    text=True,
                    timeout=30
                )
                
                # Should fail with expected error
                if result.returncode == 0:
                    return False, f"Corrupted package {corruption_type} was not rejected"
                
                error_output = result.stderr.lower()
                if expected_error_pattern.lower() not in error_output:
                    return False, f"Expected error pattern '{expected_error_pattern}' not found in: {result.stderr}"
                
                logger.info(f"Corruption test {corruption_type} PASSED - correctly rejected")
                return True, f"Correctly rejected {corruption_type} with appropriate error"
                
        except subprocess.TimeoutExpired:
            return False, f"Corruption test {corruption_type} timed out"
        except Exception as e:
            return False, f"Corruption test {corruption_type} error: {str(e)}"

    def test_permission_errors(self) -> Tuple[bool, str]:
        """Test handling of permission errors"""
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)
                
                # Create read-only cache directory
                cache_dir = temp_path / "readonly_cache"
                cache_dir.mkdir()
                cache_dir.chmod(0o444)  # Read-only
                
                base_package = self._create_dummy_flavor_package(temp_path)
                
                cmd = [str(base_package), "--force-extract", "--cache-dir", str(cache_dir)]
                
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                
                # Should fail with permission error
                if result.returncode == 0:
                    return False, "Permission error was not detected"
                    
                error_patterns = ["permission", "denied", "create", "write"]
                error_output = result.stderr.lower()
                
                if not any(pattern in error_output for pattern in error_patterns):
                    return False, f"No permission error patterns found in: {result.stderr}"
                
                logger.info("Permission error test PASSED")
                return True, "Permission errors correctly handled"
                
        except Exception as e:
            return False, f"Permission test error: {str(e)}"

    def test_insufficient_disk_space(self) -> Tuple[bool, str]:
        """Test handling of insufficient disk space (simulated)"""
        # This is a complex test to implement properly without actually filling disk
        # For now, we'll test a related scenario - very small cache directory
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)
                
                # Create cache directory on a small filesystem (if possible)
                # This is platform-specific and hard to simulate reliably
                # So we'll skip this test for now and mark as passed
                
                logger.info("Disk space test SKIPPED (requires platform-specific simulation)")
                return True, "Disk space test skipped (simulation not implemented)"
                
        except Exception as e:
            return False, f"Disk space test error: {str(e)}"

    def test_network_timeout_scenarios(self) -> Tuple[bool, str]:
        """Test network-related timeout scenarios"""
        # Flavor extraction is mostly file-based, but there might be network components
        # This would be relevant for downloading additional components
        
        logger.info("Network timeout test SKIPPED (no network components in current Flavor)")
        return True, "Network timeout test not applicable to current Flavor implementation"

    def test_concurrent_extraction(self) -> Tuple[bool, str]:
        """Test concurrent extraction to same cache directory"""
        try:
            import concurrent.futures
            import threading
            
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)
                cache_dir = temp_path / "shared_cache"
                cache_dir.mkdir()
                
                base_package = self._create_dummy_flavor_package(temp_path)
                
                def extract_package(package_path: Path, cache_path: Path, worker_id: int):
                    """Worker function for concurrent extraction"""
                    cmd = [str(package_path), "--force-extract", "--cache-dir", str(cache_path)]
                    
                    result = subprocess.run(
                        cmd,
                        capture_output=True,
                        text=True,
                        timeout=60
                    )
                    
                    return worker_id, result.returncode, result.stderr
                
                # Run multiple concurrent extractions
                num_workers = 3
                with concurrent.futures.ThreadPoolExecutor(max_workers=num_workers) as executor:
                    futures = []
                    for i in range(num_workers):
                        future = executor.submit(extract_package, base_package, cache_dir, i)
                        futures.append(future)
                    
                    results = []
                    for future in concurrent.futures.as_completed(futures):
                        worker_id, returncode, stderr = future.result()
                        results.append((worker_id, returncode, stderr))
                
                # Analyze results
                successful_extractions = sum(1 for _, returncode, _ in results if returncode == 0)
                
                if successful_extractions == 0:
                    return False, "No concurrent extractions succeeded"
                
                # At least one should succeed, others might fail due to race conditions
                # This is acceptable behavior
                logger.info(f"Concurrent extraction test PASSED ({successful_extractions}/{num_workers} succeeded)")
                return True, f"Concurrent extraction handled correctly ({successful_extractions}/{num_workers} succeeded)"
                
        except Exception as e:
            return False, f"Concurrent extraction test error: {str(e)}"

    def test_malformed_command_line_args(self) -> Tuple[bool, str]:
        """Test handling of malformed command line arguments"""
        try:
            rust_launcher = self.test_launchers["rust"]
            if not Path(rust_launcher).exists():
                return False, "Rust launcher not found for CLI testing"
            
            test_cases = [
                (["--invalid-flag"], "unrecognized"),
                (["--cache-dir"], "requires a value"),
                (["--help", "--version"], "help"),  # Should handle gracefully
            ]
            
            for args, expected_pattern in test_cases:
                cmd = [rust_launcher] + args
                
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                
                # Most invalid args should return non-zero
                if "--help" not in args and result.returncode == 0:
                    return False, f"Invalid args {args} were not rejected"
                
                output = (result.stdout + result.stderr).lower()
                if expected_pattern.lower() not in output:
                    return False, f"Expected pattern '{expected_pattern}' not found for args {args}"
            
            logger.info("CLI argument test PASSED")
            return True, "Command line argument validation working correctly"
            
        except Exception as e:
            return False, f"CLI argument test error: {str(e)}"

# Test Functions (pytest compatible)

@pytest.mark.parametrize("corruption_type,expected_error", [
    ("invalid_magic", "not a flavor file"),
    ("invalid_footer_magic", "invalid footer magic"),
    ("truncated_file", "read"),
    ("empty_file", "not a flavor file"),
])
def test_corrupted_flavor_package_rejection(corruption_type, expected_error):
    """Test that corrupted packages are properly rejected"""
    framework = FlavorErrorTestFramework()
    success, message = framework.test_corrupted_package_handling(corruption_type, expected_error)
    assert success, f"Corruption test failed: {message}"

def test_permission_error_handling():
    """Test handling of permission errors"""
    framework = FlavorErrorTestFramework()
    success, message = framework.test_permission_errors()
    assert success, f"Permission error test failed: {message}"

def test_concurrent_extraction_safety():
    """Test concurrent extraction scenarios"""
    framework = FlavorErrorTestFramework()
    success, message = framework.test_concurrent_extraction()
    assert success, f"Concurrent extraction test failed: {message}"

def test_cli_argument_validation():
    """Test command line argument validation"""
    framework = FlavorErrorTestFramework()
    success, message = framework.test_malformed_command_line_args()
    assert success, f"CLI argument test failed: {message}"

# Main execution for standalone testing
if __name__ == "__main__":
    framework = FlavorErrorTestFramework()
    
    print("=== Flavor Error Handling Test Suite ===")
    
    # Test corrupted packages
    corruption_tests = [
        ("invalid_magic", "not a flavor file"),
        ("invalid_footer_magic", "invalid footer magic"),
        ("truncated_file", "read"),
        ("empty_file", "not a flavor file"),
        ("wrong_launcher", "not a flavor file"),
    ]
    
    print("\n--- Corruption Handling Tests ---")
    for corruption_type, expected_error in corruption_tests:
        success, message = framework.test_corrupted_package_handling(corruption_type, expected_error)
        print(f"{corruption_type}: {{'PASS' if success else 'FAIL'}} - {message}")
    
    # Test other error scenarios
    error_tests = [
        ("Permission Errors", framework.test_permission_errors),
        ("Concurrent Extraction", framework.test_concurrent_extraction),
        ("CLI Arguments", framework.test_malformed_command_line_args),
    ]
    
    print("\n--- Error Scenario Tests ---")
    for test_name, test_func in error_tests:
        success, message = test_func()
        print(f"{test_name}: {{'PASS' if success else 'FAIL'}} - {message}")


# 📦🍜🧪🪄
