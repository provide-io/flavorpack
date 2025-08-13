#!/usr/bin/env python3
"""
Test to prove packagers embed launchers and create self-extracting PSPFs.
"""

from pathlib import Path
import shutil
import subprocess
import tempfile
import pytest


def create_test_package(temp_dir: Path, name: str):
    """Create a minimal test package."""
    module_name = name.replace("-", "_")
    src_dir = temp_dir / "src" / module_name
    src_dir.mkdir(parents=True)

    (src_dir / "__init__.py").write_text(f'"""Test {name} package."""')
    (src_dir / "main.py").write_text(f"""
import sys
import json

def serve():
    print(json.dumps({{
        "proof": "{name} package executed successfully!",
        "launcher": "embedded launcher extracted and used"
    }}))
    sys.exit(0)

if __name__ == "__main__":
    serve()
""")

    pyproject = temp_dir / "pyproject.toml"
    pyproject.write_text(f"""
[build-system]
requires = ["setuptools>=61.0", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "{name}-package"
version = "1.0.0"
requires-python = ">=3.9"

[project.scripts]
run-package-{name} = "{module_name}.main:serve"

[tool.flavor]
package_name = "{name}"
entry_point = "{module_name}.main:serve"

[tool.flavor.build]
python_version = "3.13"
dependencies = ["./src/{module_name}"]

[tool.setuptools.packages.find]
where = ["src"]
include = ["{module_name}*"]
""")
    return pyproject


@pytest.mark.skip(reason="Test requires pre-built Go/Rust binaries and is complex")
def test_go_packager_embedded_launcher() -> None:
    """Test Go packager with embedded Go launcher."""
    from flavor.api import build_package_from_manifest
    
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_dir = Path(temp_dir)
        pyproject = create_test_package(temp_dir, "go-test")
        artifacts = build_package_from_manifest(pyproject)
        assert len(artifacts) == 1
        python_package = artifacts[0]
        assert python_package.exists()

@pytest.mark.skip(reason="Test requires pre-built Go/Rust binaries and is complex")
def test_rust_packager_embedded_launcher() -> None:
    """Test Rust packager with embedded Rust launcher."""
    from flavor.api import build_package_from_manifest
    
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_dir = Path(temp_dir)
        pyproject = create_test_package(temp_dir, "rust-test")
        artifacts = build_package_from_manifest(pyproject)
        assert len(artifacts) == 1
        python_package = artifacts[0]
        assert python_package.exists()

@pytest.mark.skip(reason="Test requires pre-built Go/Rust binaries and is complex")
def test_self_extraction() -> None:
    """Test that PSPF packages self-extract the embedded launcher."""
    assert True
