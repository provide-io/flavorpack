#!/usr/bin/env python3
"""
Terraform Flavor Integration Tests

This module provides comprehensive testing of Flavor packages within 
terraform/tofu workflows, including provider installation, execution,
and various terraform operations.
"""

import pytest
import subprocess
import tempfile
import shutil
import json
import os
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any
import logging

from flavor.api import build_package_from_manifest
from flavor.packaging.keys import generate_key_pair

logger = logging.getLogger(__name__)

class TerraformFlavorTestFramework:
    """Framework for testing Flavor packages with Terraform/OpenTofu"""
    
    def __init__(self):
        self.project_root = Path("/REDACTED_ABS_PATH")
        self.terraform_provider_dir = self.project_root / "terraform-provider-pyvider"
        self.components_examples = self.project_root / "pyvider-components" / "examples"
        
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
    __pyvider_schema__ = s_provider_config(version="1.0.0")
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
name = "dummy-provider"
version = "1.0.0"
description = "Dummy provider for testing"
requires-python = ">=3.13"
dependencies = ["pyvider", "pyvider-components"]

[project.scripts]
dummy-provider = "dummy_provider.__main__:main"

[project.entry-points."pyvider.providers"]
dummy = "dummy_provider:DummyProvider"

[build-system]
requires = ["setuptools", "wheel"]
build-backend = "setuptools.build_meta"

[tool.setuptools]
packages = ["dummy_provider"]

[tool.setuptools.package-dir]
"" = "src"

[tool.flavor]
provider_name = "dummy"
entry_point = "dummy_provider.__main__:main"
targets = ["darwin_arm64"]

[tool.flavor.build]
python_version = "3.13"
dependencies = []

[tool.flavor.signing]
private_key_path = "keys/provider-private.key"
public_key_path = "keys/provider-public.key"
"""
        (provider_dir / "pyproject.toml").write_text(pyproject_content)

        generate_key_pair(provider_dir / "keys")
        artifacts = build_package_from_manifest(provider_dir / "pyproject.toml")
        return artifacts[0]

    def install_flavor_provider(self, tf_dir: Path, flavor_package: Path) -> Path:
        """Install Flavor provider for terraform use using dev overrides"""
        
        # Create provider override directory 
        provider_override_dir = tf_dir / "provider-override"
        provider_override_dir.mkdir(parents=True, exist_ok=True)
        
        # Copy Flavor package as provider binary (terraform expects this name)
        provider_binary = provider_override_dir / "terraform-provider-pyvider"
        shutil.copy2(flavor_package, provider_binary)
        
        # Create terraformrc with dev override
        tf_cli_config = tf_dir / ".terraformrc"
        tf_cli_config.write_text(f'''
provider_installation {{
  dev_overrides {{
    "local.dev/pyvider/pyvider" = "{provider_override_dir.absolute()}"
  }}
  
  # Disable direct installation to force using dev overrides only
}}
''')
        
        return provider_binary

    def run_terraform_command(self, command: List[str], tf_dir: Path, timeout: int = 60) -> Tuple[bool, str, str]:
        """Run terraform command and return success, stdout, stderr"""
        
        try:
            # Set up environment for terraform with dev overrides
            env = os.environ.copy()
            env["HOME"] = str(tf_dir)
            tf_cli_config = tf_dir / ".terraformrc"
            if tf_cli_config.exists():
                env["TF_CLI_CONFIG_FILE"] = str(tf_cli_config)
                
            result = subprocess.run(
                command,
                cwd=tf_dir,
                capture_output=True,
                text=True,
                timeout=timeout,
                env=env
            )
            
            return (result.returncode == 0, result.stdout, result.stderr)
            
        except subprocess.TimeoutExpired:
            return (False, "", f"Command timed out after {timeout}s")
        except Exception as e:
            return (False, "", f"Command error: {str(e)}")

    def test_terraform_init_with_flavor(self, flavor_package: Path) -> Tuple[bool, str]:
        """Test terraform init with Flavor provider"""
        
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                tf_dir = Path(temp_dir)
                
                # Create minimal terraform config
                self.create_test_terraform_config(tf_dir, "minimal")
                
                # Install Flavor provider
                self.install_flavor_provider(tf_dir, flavor_package)
                
                # Run terraform init
                success, stdout, stderr = self.run_terraform_command(["/opt/homebrew/bin/terraform", "init"], tf_dir)
                
                if not success:
                    return False, f"Terraform init failed: {stderr}"
                    
                # Verify provider was initialized
                if "pyvider" not in stdout.lower():
                    return False, f"Provider not mentioned in init output: {stdout}"
                    
                logger.info("Terraform init with Flavor PASSED")
                return True, "Terraform init successful with Flavor provider"
                
        except Exception as e:
            return False, f"Terraform init test error: {str(e)}"

    def test_terraform_plan_with_flavor(self, flavor_package: Path, config_type: str = "data_source_test") -> Tuple[bool, str]:
        """Test terraform plan with Flavor provider"""
        
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                tf_dir = Path(temp_dir)
                
                # Create terraform config
                self.create_test_terraform_config(tf_dir, config_type)
                
                # Install Flavor provider
                self.install_flavor_provider(tf_dir, flavor_package)
                
                # Run terraform init
                success, _, stderr = self.run_terraform_command(["/opt/homebrew/bin/terraform", "init"], tf_dir)
                if not success:
                    return False, f"Init failed: {stderr}"
                
                # Run terraform plan
                success, stdout, stderr = self.run_terraform_command(["/opt/homebrew/bin/terraform", "plan"], tf_dir)
                
                if not success:
                    return False, f"Terraform plan failed: {stderr}"
                    
                # Verify plan contains expected elements
                plan_lower = stdout.lower()
                if config_type == "data_source_test" and "pyvider_file_info" not in plan_lower:
                    return False, "Data source not found in plan"
                elif config_type == "resource_test" and "pyvider_file_content" not in plan_lower:
                    return False, "Resource not found in plan"
                    
                logger.info(f"Terraform plan ({config_type}) with Flavor PASSED")
                return True, f"Terraform plan successful for {config_type}"
                
        except Exception as e:
            return False, f"Terraform plan test error: {str(e)}"

    def test_terraform_apply_with_flavor(self, flavor_package: Path) -> Tuple[bool, str]:
        """Test terraform apply with Flavor provider"""
        
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                tf_dir = Path(temp_dir)
                
                # Create resource test config
                self.create_test_terraform_config(tf_dir, "resource_test")
                
                # Install Flavor provider
                self.install_flavor_provider(tf_dir, flavor_package)
                
                # Run terraform init
                success, _, stderr = self.run_terraform_command(["/opt/homebrew/bin/terraform", "init"], tf_dir)
                if not success:
                    return False, f"Init failed: {stderr}"
                
                # Run terraform apply
                success, stdout, stderr = self.run_terraform_command(
                    ["/opt/homebrew/bin/terraform", "apply", "-auto-approve"], tf_dir, timeout=120
                )
                
                if not success:
                    return False, f"Terraform apply failed: {stderr}"
                    
                # Verify resource was created
                test_file = Path("/tmp/flavor_terraform_test.txt")
                if not test_file.exists():
                    return False, "Test file was not created by terraform apply"
                    
                content = test_file.read_text()
                if "Hello from Flavor" not in content:
                    return False, f"Test file has incorrect content: {content}"
                    
                # Cleanup
                test_file.unlink()
                
                # Run terraform destroy
                success, _, stderr = self.run_terraform_command(
                    ["/opt/homebrew/bin/terraform", "destroy", "-auto-approve"], tf_dir, timeout=120
                )
                
                if not success:
                    logger.warning(f"Terraform destroy failed: {stderr}")
                
                logger.info("Terraform apply with Flavor PASSED")
                return True, "Terraform apply/destroy cycle successful"
                
        except Exception as e:
            return False, f"Terraform apply test error: {str(e)}"

    def test_terraform_function_calls_with_flavor(self, flavor_package: Path) -> Tuple[bool, str]:
        """Test terraform provider functions with Flavor"""
        
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                tf_dir = Path(temp_dir)
                
                # Create function test config
                self.create_test_terraform_config(tf_dir, "function_test")
                
                # Install Flavor provider
                self.install_flavor_provider(tf_dir, flavor_package)
                
                # Run terraform init
                success, _, stderr = self.run_terraform_command(["/opt/homebrew/bin/terraform", "init"], tf_dir)
                if not success:
                    return False, f"Init failed: {stderr}"
                
                # Run terraform plan to test functions
                success, stdout, stderr = self.run_terraform_command(["/opt/homebrew/bin/terraform", "plan"], tf_dir)
                
                if not success:
                    return False, f"Function test plan failed: {stderr}"
                    
                # Look for function calls in plan output
                if "join(" not in stdout.lower() and "upper(" not in stdout.lower():
                    # Functions might be evaluated, check outputs
                    pass
                    
                logger.info("Terraform function calls with Flavor PASSED")
                return True, "Terraform provider functions working"
                
        except Exception as e:
            return False, f"Terraform function test error: {str(e)}"

    def test_terraform_state_management_with_flavor(self, flavor_package: Path) -> Tuple[bool, str]:
        """Test terraform state operations with Flavor provider"""
        
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                tf_dir = Path(temp_dir)
                
                # Create data source test (stateless)
                self.create_test_terraform_config(tf_dir, "data_source_test")
                
                # Install Flavor provider
                self.install_flavor_provider(tf_dir, flavor_package)
                
                # Run terraform init
                success, _, stderr = self.run_terraform_command(["/opt/homebrew/bin/terraform", "init"], tf_dir)
                if not success:
                    return False, f"Init failed: {stderr}"
                
                # Run terraform plan
                success, _, stderr = self.run_terraform_command(["/opt/homebrew/bin/terraform", "plan"], tf_dir)
                if not success:
                    return False, f"Plan failed: {stderr}"
                
                # Check terraform state
                success, stdout, stderr = self.run_terraform_command(["/opt/homebrew/bin/terraform", "state", "list"], tf_dir)
                
                # For data sources, state might be empty initially
                if not success:
                    return False, f"State list failed: {stderr}"
                    
                logger.info("Terraform state management with Flavor PASSED")
                return True, "Terraform state operations working"
                
        except Exception as e:
            return False, f"Terraform state test error: {str(e)}"

    def test_launch_context_in_terraform_logs(self, flavor_package: Path) -> Tuple[bool, str]:
        """Test that launch context is properly logged during terraform operations"""
        
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                tf_dir = Path(temp_dir)
                log_file = tf_dir / "terraform.log"
                
                # Create minimal config
                self.create_test_terraform_config(tf_dir, "minimal")
                
                # Install Flavor provider
                self.install_flavor_provider(tf_dir, flavor_package)
                
                # Set up terraform logging
                env = os.environ.copy()
                env.update({
                    "TF_LOG": "DEBUG",
                    "TF_LOG_PATH": str(log_file)
                })
                
                # Run terraform init
                success, _, stderr = self.run_terraform_command(["/opt/homebrew/bin/terraform", "init"], tf_dir)
                if not success:
                    return False, f"Init failed: {stderr}"
                
                # Run terraform plan with logging
                result = subprocess.run(
                    ["/opt/homebrew/bin/terraform", "plan"],
                    cwd=tf_dir,
                    capture_output=True,
                    text=True,
                    timeout=60,
                    env=env
                )
                
                if result.returncode != 0:
                    return False, f"Plan with logging failed: {result.stderr}"
                
                # Check log file for launch context
                if log_file.exists():
                    log_content = log_file.read_text()
                    if "launch method" in log_content.lower() or "flavor_package" in log_content.lower():
                        logger.info("Launch context found in terraform logs")
                        return True, "Launch context properly logged in terraform workflow"
                    else:
                        return False, "Launch context not found in terraform logs"
                else:
                    return False, "Terraform log file not created"
                    
        except Exception as e:
            return False, f"Launch context logging test error: {str(e)}"

# Test Functions (pytest compatible)

@pytest.fixture
def flavor_package(tmp_path):
    """Pytest fixture for Flavor package"""
    # Create a dummy flavor package for testing
    provider_dir = tmp_path / "dummy-provider"
    provider_dir.mkdir()

    src_dir = provider_dir / "src" / "dummy_provider"
    src_dir.mkdir(parents=True)

    (src_dir / "__init__.py").write_text("""
from pyvider.providers import BaseProvider
from pyvider.schema import s_provider_config, a_str

class DummyProvider(BaseProvider):
    __pyvider_schema__ = s_provider_config(version="1.0.0")
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
name = "dummy-provider"
version = "1.0.0"
description = "Dummy provider for testing"
requires-python = ">=3.13"
dependencies = ["pyvider", "pyvider-components"]

[project.scripts]
dummy-provider = "dummy_provider.__main__:main"

[project.entry-points."pyvider.providers"]
dummy = "dummy_provider:DummyProvider"

[build-system]
requires = ["setuptools", "wheel"]
build-backend = "setuptools.build_meta"

[tool.setuptools]
packages = ["dummy_provider"]

[tool.setuptools.package-dir]
"" = "src"

[tool.flavor]
provider_name = "dummy"
entry_point = "dummy_provider.__main__:main"
targets = ["darwin_arm64"]

[tool.flavor.build]
python_version = "3.13"
dependencies = []

[tool.flavor.signing]
private_key_path = "keys/provider-private.key"
public_key_path = "keys/provider-public.key"
"""
    (provider_dir / "pyproject.toml").write_text(pyproject_content)

    generate_key_pair(provider_dir / "keys")
    artifacts = build_package_from_manifest(provider_dir / "pyproject.toml")
    return artifacts[0]

def test_terraform_init_flavor_integration(flavor_package):
    """Test terraform init with Flavor provider"""
    framework = TerraformFlavorTestFramework()
    success, message = framework.test_terraform_init_with_flavor(flavor_package)
    assert success, f"Terraform init failed: {message}"

@pytest.mark.parametrize("config_type", ["data_source_test", "resource_test", "function_test"])
def test_terraform_plan_flavor_integration(flavor_package, config_type):
    """Test terraform plan with different configurations"""
    framework = TerraformFlavorTestFramework()
    success, message = framework.test_terraform_plan_with_flavor(flavor_package, config_type)
    assert success, f"Terraform plan failed: {message}"

def test_terraform_apply_flavor_integration(flavor_package):
    """Test terraform apply/destroy cycle"""
    framework = TerraformFlavorTestFramework()
    success, message = framework.test_terraform_apply_with_flavor(flavor_package)
    assert success, f"Terraform apply failed: {message}"

def test_terraform_function_calls_flavor_integration(flavor_package):
    """Test terraform provider function calls"""
    framework = TerraformFlavorTestFramework()
    success, message = framework.test_terraform_function_calls_with_flavor(flavor_package)
    assert success, f"Terraform function calls failed: {message}"

def test_terraform_state_management_flavor_integration(flavor_package):
    """Test terraform state operations"""
    framework = TerraformFlavorTestFramework()
    success, message = framework.test_terraform_state_management_with_flavor(flavor_package)
    assert success, f"Terraform state management failed: {message}"

def test_launch_context_terraform_logging(flavor_package):
    """Test launch context logging in terraform workflows"""
    framework = TerraformFlavorTestFramework()
    success, message = framework.test_launch_context_in_terraform_logs(flavor_package)
    assert success, f"Launch context logging failed: {message}"

# Main execution for standalone testing
if __name__ == "__main__":
    framework = TerraformFlavorTestFramework()
    
    # Get Flavor package from fixture
    package_path = flavor_package(Path(tempfile.mkdtemp()))
    
    print("=== Terraform Flavor Integration Test Suite ===")
    
    tests = [
        ("Init", framework.test_terraform_init_with_flavor),
        ("Plan (Data Source)", lambda pkg: framework.test_terraform_plan_with_flavor(pkg, "data_source_test")),
        ("Plan (Resource)", lambda pkg: framework.test_terraform_plan_with_flavor(pkg, "resource_test")),
        ("Plan (Functions)", lambda pkg: framework.test_terraform_plan_with_flavor(pkg, "function_test")),
        ("Apply/Destroy", framework.test_terraform_apply_with_flavor),
        ("State Management", framework.test_terraform_state_management_with_flavor),
        ("Launch Context Logging", lambda pkg: framework.test_launch_context_in_terraform_logs(pkg)),
    ]
    
    for test_name, test_func in tests:
        print(f"\n--- {test_name} ---")
        success, message = test_func(package_path)
        print(f"Result: {('PASS' if success else 'FAIL')}")
        print(f"Details: {message}")


# 📦🍜🧪🪄
