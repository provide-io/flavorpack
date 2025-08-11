"""
Shared fixtures and configuration for cross-language tests.
"""

import os
import pytest
import subprocess
from pathlib import Path


def pytest_addoption(parser):
    """Add command-line options for cross-language testing."""
    parser.addoption(
        "--skip-rust",
        action="store_true",
        default=False,
        help="Skip Rust implementation tests"
    )
    parser.addoption(
        "--skip-go", 
        action="store_true",
        default=False,
        help="Skip Go implementation tests"
    )
    parser.addoption(
        "--force-rebuild",
        action="store_true", 
        default=False,
        help="Force rebuild of all binaries before testing"
    )


@pytest.fixture(scope="session", autouse=True)
def ensure_binaries_built(request):
    """Ensure all binaries are built before running tests."""
    if request.config.getoption("--force-rebuild"):
        # Clean and rebuild everything
        flavor_root = Path(__file__).parent.parent.parent
        
        # Clean Go binaries
        go_bin_dir = Path.home() / ".cache" / "flavor" / "bin"
        if go_bin_dir.exists():
            import shutil
            shutil.rmtree(go_bin_dir)
        
        # Clean Rust binaries
        rust_dirs = [
            flavor_root / "src" / "flavor" / "rust" / "flavor-launcher-rs",
            flavor_root / "src" / "flavor" / "rust" / "flavor-packager-rs"
        ]
        for rust_dir in rust_dirs:
            target_dir = rust_dir / "target"
            if target_dir.exists():
                import shutil
                shutil.rmtree(target_dir)


@pytest.fixture(scope="session")
def skip_rust(request):
    """Check if Rust tests should be skipped."""
    return request.config.getoption("--skip-rust")


@pytest.fixture(scope="session")
def skip_go(request):
    """Check if Go tests should be skipped."""
    return request.config.getoption("--skip-go")


@pytest.fixture(scope="session") 
def implementation_matrix(skip_rust, skip_go):
    """Get the matrix of implementations to test."""
    impls = {
        "packagers": ["python"],
        "launchers": []
    }
    
    if not skip_go:
        impls["packagers"].append("go")
        impls["launchers"].append("go")
    
    if not skip_rust:
        # Check if Rust is available
        if subprocess.run(["which", "cargo"], capture_output=True).returncode == 0:
            impls["packagers"].append("rust")
            impls["launchers"].append("rust")
    
    return impls


# Environment setup
@pytest.fixture(autouse=True)
def setup_test_environment():
    """Set up environment for testing."""
    # Ensure we don't pick up user's flavor config
    os.environ["FLAVOR_CONFIG_DIR"] = "/tmp/flavor-test-config"
    
    # Set consistent Python version for builds
    os.environ["FLAVOR_PYTHON_VERSION"] = "3.13"
    
    # Disable any caching that might interfere with tests
    os.environ["FLAVOR_NO_CACHE"] = "1"
    
    yield
    
    # Cleanup
    for key in ["FLAVOR_CONFIG_DIR", "FLAVOR_PYTHON_VERSION", "FLAVOR_NO_CACHE"]:
        os.environ.pop(key, None)


# 📦🍜🧪🪄
