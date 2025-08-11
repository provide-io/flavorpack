#!/usr/bin/env python3
"""
Comprehensive Flavor Integration Test Suite

This module provides end-to-end integration testing for the Flavor (Progressive Secure Package Format) system,
including package creation, extraction, terraform provider workflows, and cross-platform compatibility.
"""

import pytest
import subprocess
import tempfile
import shutil
import json
import time
import os
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any
import logging

from flavor.api import build_package_from_manifest
from flavor.packaging.keys import generate_key_pair

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class FlavorTestFramework:
    """Framework for comprehensive Flavor testing"""
    
    def __init__(self):
        self.project_root = Path("/REDACTED_ABS_PATH")
        self.terraform_provider_dir = self.project_root / "terraform-provider-pyvider"
        self.flavor_dir = self.project_root / "flavor"
        self.components_dir = self.project_root / "pyvider-components"
        
        # Test artifacts
        self.test_launchers = {
            "go": str(self.flavor_dir / "src" / "flavor" / "go" / "flavor-launcher" / "flavor-launcher-go"),
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
    async def configure(self, config): return self
    async def setup(self): pass
""")
        (src_dir / "__main__.py").write_text("""
import sys
from pyvider.cli import main
if __name__ == "__main__": sys.exit(main())
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

    def setup_test_environment(self) -> Dict[str, Path]:
        """Setup clean test environment"""
        test_dir = Path(tempfile.mkdtemp(prefix="flavor_integration_test_"))
        
        directories = {
            "test_root": test_dir,
            "cache": test_dir / "cache",
            "packages": test_dir / "packages",
            "terraform": test_dir / "terraform",
            "keys": test_dir / "keys",
            "logs": test_dir / "logs"
        }
        
        for dir_path in directories.values():
            dir_path.mkdir(parents=True, exist_ok=True)
            
        logger.info(f"Test environment created at: {test_dir}")
        return directories
    
    def cleanup_test_environment(self, test_dirs: Dict[str, Path]) -> None:
        """Clean up test environment"""
        try:
            shutil.rmtree(test_dirs["test_root"])
            logger.info(f"Test environment cleaned up: {test_dirs['test_root']}")
        except Exception as e:
            logger.warning(f"Failed to cleanup test environment: {e}")

    def build_flavor_package(self, test_dirs: Dict[str, Path], force_rebuild: bool = False) -> Path:
        """Build a fresh Flavor package for testing"""
        package_path = test_dirs["packages"] / "terraform-provider-pyvider_test"
        
        if package_path.exists() and not force_rebuild:
            logger.info(f"Using existing Flavor package: {package_path}")
            return package_path
            
        logger.info("Building fresh Flavor package...")
        
        # Clean and build
        cmd = [
            str(self.project_root / "tofusoup" / ".venv_darwin_arm64" / "bin" / "soup"),
            "package", "build"
        ]
        
        env = os.environ.copy()
        result = subprocess.run(
            cmd, 
            cwd=self.terraform_provider_dir,
            env=env,
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            raise RuntimeError(f"Failed to build Flavor package: {result.stderr}")
            
        # Copy built package to test location
        built_package = self.terraform_provider_dir / "dist" / "flavor" / "darwin_arm64" / "terraform-provider-pyvider_v0.0.1"
        shutil.copy2(built_package, package_path)
        
        logger.info(f"Flavor package built and copied to: {package_path}")
        return package_path

    def test_package_creation(self, test_dirs: Dict[str, Path]) -> Tuple[bool, str]:
        """Test Flavor package creation"""
        try:
            package_path = self.build_flavor_package(test_dirs, force_rebuild=True)
            
            # Verify package exists and has expected size
            if not package_path.exists():
                return False, "Package file not created"
                
            size_mb = package_path.stat().st_size / (1024 * 1024)
            if size_mb < 10:  # Expect at least 10MB
                return False, f"Package too small: {size_mb:.1f}MB"
                
            # Verify Flavor magic bytes
            with open(package_path, 'rb') as f:
                f.seek(-12, 2)  # Last 12 bytes
                magic = f.read()
                expected_magic = b'\xf0\x9f\x93\xa6FLAVOR\xf0\x9f\x93\xa6'
                if magic != expected_magic:
                    return False, f"Invalid magic bytes: {magic.hex()}"
                    
            logger.info(f"Package creation test PASSED: {size_mb:.1f}MB")
            return True, f"Package created successfully ({size_mb:.1f}MB)"
            
        except Exception as e:
            return False, f"Package creation failed: {str(e)}"

    def test_package_verification(self, test_dirs: Dict[str, Path]) -> Tuple[bool, str]:
        """Test Flavor package verification"""
        try:
            package_path = self.build_flavor_package(test_dirs)
            
            # Test with Python Flavor verifier
            cmd = [
                str(self.flavor_dir / ".venv_darwin_arm64" / "bin" / "flavor"),
                "verify", str(package_path)
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode != 0:
                return False, f"Verification failed: {result.stderr}"
                
            logger.info("Package verification test PASSED")
            return True, "Package verification successful"
            
        except subprocess.TimeoutExpired:
            return False, "Verification timed out"
        except Exception as e:
            return False, f"Verification error: {str(e)}"

    def test_launcher_extraction(self, launcher_type: str, test_dirs: Dict[str, Path]) -> Tuple[bool, str, float]:
        """Test Flavor extraction with specific launcher"""
        if launcher_type not in self.test_launchers:
            return False, f"Unknown launcher type: {launcher_type}", 0.0
            
        launcher_path = self.test_launchers[launcher_type]
        if not Path(launcher_path).exists():
            return False, f"Launcher not found: {launcher_path}", 0.0
            
        try:
            # Create test package by combining launcher + Flavor data
            package_path = self.build_flavor_package(test_dirs)
            test_package = test_dirs["packages"] / f"{launcher_type}_test_package"
            
            # Create test package using our proven method
            self._create_test_package(launcher_path, package_path, test_package)
            
            # Test extraction
            cache_dir = test_dirs["cache"] / f"{launcher_type}_cache"
            cache_dir.mkdir(exist_ok=True)
            
            start_time = time.perf_counter()
            
            cmd = [str(test_package), "--force-extract", "--cache-dir", str(cache_dir)]
            if launcher_type == "rust":
                cmd.append("--verbose")
                
            env = os.environ.copy()
            if launcher_type == "rust":
                env["RUST_LOG"] = "info"
                
            result = subprocess.run(cmd, capture_output=True, text=True, env=env, timeout=60)
            
            extraction_time = time.perf_counter() - start_time
            
            if result.returncode != 0:
                return False, f"Extraction failed: {result.stderr}", extraction_time
                
            # Verify extraction results
            python_exe = cache_dir / "cache" / "bin" / "python"
            if not python_exe.exists():
                return False, "Python executable not extracted", extraction_time
                
            logger.info(f"{launcher_type.title()} extraction test PASSED ({extraction_time:.2f}s)")
            return True, f"Extraction successful ({extraction_time:.2f}s)", extraction_time
            
        except subprocess.TimeoutExpired:
            return False, "Extraction timed out", 0.0
        except Exception as e:
            return False, f"Extraction error: {str(e)}", 0.0

    def _create_test_package(self, launcher_path: str, flavor_package_path: Path, output_path: Path) -> None:
        """Create test package by combining launcher with Flavor data"""
        # Copy launcher
        shutil.copy2(launcher_path, output_path)
        
        # Find and append Flavor data
        with open(flavor_package_path, 'rb') as flavor_file:
            flavor_file.seek(0, 2)
            file_size = flavor_file.tell()
            
            # Find Flavor data start by looking for magic and working backwards
            magic = b'\xf0\x9f\x93\xa6FLAVOR\xf0\x9f\x93\xa6'
            flavor_file.seek(-len(magic), 2)
            if flavor_file.read() != magic:
                raise ValueError("Invalid Flavor package")
                
            # Read footer to calculate Flavor data size  
            footer_size = 120 # Updated footer size
            flavor_file.seek(-(footer_size + len(magic)), 2)
            footer_data = flavor_file.read(footer_size)
            
            # Parse footer to find max offset (simplified)
            import struct
            max_offset = 0
            for i in range(0, 96, 16):  # 6 sections
                offset, size = struct.unpack('<QQ', footer_data[i:i+16])
                if size > 0:
                    max_offset = max(max_offset, offset + size)
                    
            flavor_size = max_offset + footer_size + len(magic)
            flavor_start = file_size - flavor_size
            
            # Append Flavor data to launcher
            flavor_file.seek(flavor_start)
            with open(output_path, 'ab') as output_file:
                shutil.copyfileobj(flavor_file, output_file)
                
        # Make executable
        output_path.chmod(0o755)

    def test_terraform_integration(self, test_dirs: Dict[str, Path]) -> Tuple[bool, str]:
        """Test terraform provider workflow with Flavor package"""
        try:
            package_path = self.build_flavor_package(test_dirs)
            
            # Create simple terraform configuration
            tf_dir = test_dirs["terraform"]
            tf_config = tf_dir / "main.tf"
            
            tf_content = '''
terraform {
  required_providers {
    pyvider = {
      source = "local/providers/pyvider"
      version = "0.0.1"
    }
  }
}

provider "pyvider" {
  endpoint = "test"
}

data "pyvider_file_info" "test" {
  filename = "/etc/hosts"
}

output "file_size" {
  value = data.pyvider_file_info.test.size
}
'''
            tf_config.write_text(tf_content)
            
            # Install provider locally
            provider_dir = tf_dir / ".terraform" / "providers" / "local" / "providers" / "pyvider" / "0.0.1" / "darwin_arm64"
            provider_dir.mkdir(parents=True, exist_ok=True)
            
            provider_binary = provider_dir / "terraform-provider-pyvider_v0.0.1"
            shutil.copy2(package_path, provider_binary)
            
            # Test terraform init
            result = subprocess.run(
                ["tofu", "init"],
                cwd=tf_dir,
                capture_output=True, 
                text=True,
                timeout=30
            )
            
            if result.returncode != 0:
                return False, f"Terraform init failed: {result.stderr}"
                
            # Test terraform plan
            result = subprocess.run(
                ["tofu", "plan"],
                cwd=tf_dir,
                capture_output=True, 
                text=True,
                timeout=60
            )
            
            if result.returncode != 0:
                return False, f"Terraform plan failed: {result.stderr}"
                
            logger.info("Terraform integration test PASSED")
            return True, "Terraform integration successful"
            
        except subprocess.TimeoutExpired:
            return False, "Terraform operation timed out"
        except Exception as e:
            return False, f"Terraform integration error: {str(e)}"

    def test_launch_context_detection(self, test_dirs: Dict[str, Path]) -> Tuple[bool, str]:
        """Test launch context detection in Flavor packages"""
        try:
            package_path = self.build_flavor_package(test_dirs)
            
            # Test launch context command
            result = subprocess.run(
                [str(package_path), "launch-context", "--format", "json"],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode != 0:
                return False, f"Launch context failed: {result.stderr}"
                
            # Parse and validate JSON response
            try:
                context_data = json.loads(result.stdout)
                if "method" not in context_data:
                    return False, "Launch context missing 'method' field"
                    
                if context_data["method"] != "flavor_package":
                    return False, f"Unexpected launch method: {context_data['method']}"
                    
            except json.JSONDecodeError as e:
                return False, f"Invalid JSON response: {e}"
                
            logger.info("Launch context detection test PASSED")
            return True, f"Launch context detected: {context_data['method']}"
            
        except subprocess.TimeoutExpired:
            return False, "Launch context detection timed out"
        except Exception as e:
            return False, f"Launch context error: {str(e)}"

    def run_performance_benchmarks(self, test_dirs: Dict[str, Path]) -> Dict[str, Dict[str, float]]:
        """Run performance benchmarks for all launchers"""
        results = {}
        
        for launcher_type in self.test_launchers:
            if Path(self.test_launchers[launcher_type]).exists():
                success, message, extraction_time = self.test_launcher_extraction(launcher_type, test_dirs)
                results[launcher_type] = {
                    "success": success,
                    "extraction_time": extraction_time,
                    "message": message
                }
                
        return results

# Test Functions (pytest compatible)

@pytest.fixture
def test_framework():
    """Pytest fixture for test framework"""
    framework = FlavorTestFramework()
    test_dirs = framework.setup_test_environment()
    
    yield framework, test_dirs
    
    framework.cleanup_test_environment(test_dirs)

def test_flavor_package_creation(test_framework):
    """Test Flavor package creation"""
    framework, test_dirs = test_framework
    success, message = framework.test_package_creation(test_dirs)
    assert success, f"Package creation failed: {message}"

def test_flavor_package_verification(test_framework):
    """Test Flavor package verification"""
    framework, test_dirs = test_framework
    success, message = framework.test_package_verification(test_dirs)
    assert success, f"Package verification failed: {message}"

@pytest.mark.parametrize("launcher_type", ["go", "rust"])
def test_launcher_extraction(test_framework, launcher_type):
    """Test extraction with different launchers"""
    framework, test_dirs = test_framework
    
    launcher_path = framework.test_launchers[launcher_type]
    if not Path(launcher_path).exists():
        pytest.skip(f"{launcher_type} launcher not found: {launcher_path}")
        
    success, message, extraction_time = framework.test_launcher_extraction(launcher_type, test_dirs)
    assert success, f"{launcher_type} extraction failed: {message}"
    assert extraction_time > 0, "Extraction time should be positive"

def test_terraform_integration(test_framework):
    """Test terraform provider integration"""
    framework, test_dirs = test_framework
    success, message = framework.test_terraform_integration(test_dirs)
    assert success, f"Terraform integration failed: {message}"

def test_launch_context_detection(test_framework):
    """Test launch context detection"""
    framework, test_dirs = test_framework
    success, message = framework.test_launch_context_detection(test_dirs)
    assert success, f"Launch context detection failed: {message}"

def test_performance_comparison(test_framework):
    """Test performance comparison between launchers"""
    framework, test_dirs = test_framework
    results = framework.run_performance_benchmarks(test_dirs)
    
    assert len(results) > 0, "No launcher benchmarks completed"
    
    for launcher_type, result in results.items():
        if result["success"]:
            logger.info(f"{launcher_type}: {result['message']}")

# Main execution for standalone testing
if __name__ == "__main__":
    framework = FlavorTestFramework()
    test_dirs = framework.setup_test_environment()
    
    try:
        print("=== Flavor Integration Test Suite ===")
        
        # Run all tests
        tests = [
            ("Package Creation", framework.test_package_creation),
            ("Package Verification", framework.test_package_verification), 
            ("Launch Context Detection", framework.test_launch_context_detection),
            ("Terraform Integration", framework.test_terraform_integration)
        ]
        
        for test_name, test_func in tests:
            print(f"\n--- {test_name} ---")
            success, message = test_func(test_dirs)
            print(f"Result: {'PASS' if success else 'FAIL'}")
            print(f"Details: {message}")
            
        # Run launcher tests
        print(f"\n--- Launcher Tests ---")
        for launcher_type in framework.test_launchers:
            if Path(framework.test_launchers[launcher_type]).exists():
                success, message, time_taken = framework.test_launcher_extraction(launcher_type, test_dirs)
                print(f"{launcher_type.title()}: {'PASS' if success else 'FAIL'} - {message}")
            else:
                print(f"{launcher_type.title()}: SKIP - Launcher not found")
                
        # Performance benchmarks
        print(f"\n--- Performance Benchmarks ---")
        perf_results = framework.run_performance_benchmarks(test_dirs)
        for launcher, result in perf_results.items():
            if result["success"]:
                print(f"{launcher.title()}: {result['extraction_time']:.2f}s")
                
    finally:
        framework.cleanup_test_environment(test_dirs)


# 📦🍜🧪🪄
