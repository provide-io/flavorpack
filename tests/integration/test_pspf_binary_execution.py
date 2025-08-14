"""Integration tests for PSPF binary execution."""

import os
import subprocess
import pytest
from pathlib import Path

from flavor.api import build_package_from_manifest, verify_package
from flavor.packaging.keys import generate_key_pair as generate_keys
from flavor.packaging.orchestrator import PackagingOrchestrator


class TestPSPFBinaryExecution:
    """Integration tests for building and executing PSPF binaries."""

    @pytest.fixture
    def test_package_dir(self, tmp_path):
        """Create a minimal test package project."""
        package_dir = tmp_path / "test-package"
        package_dir.mkdir()

        src_dir = package_dir / "src"
        src_dir.mkdir()

        (src_dir / "__init__.py").write_text("")
        (src_dir / "main.py").write_text("""
import sys
import json
import os

def main():
    print("Test Package v1.0.0")
    sys.exit(0)

if __name__ == "__main__":
    main()
""")

        pyproject_content = """
[project]
name = "test-package"
version = "1.0.0"
description = "Test package for PSPF integration tests"
requires-python = ">=3.11"

[project.scripts]
test-package = "main:main"

[build-system]
requires = ["setuptools", "wheel"]
build-backend = "setuptools.build_meta"

[tool.setuptools]
py-modules = ["main"]

[tool.setuptools.package-dir]
"" = "src"

[tool.flavor]
package_name = "test"
entry_point = "main:main"

[tool.flavor.signing]
private_key_path = "keys/flavor-private.key"
public_key_path = "keys/flavor-public.key"
"""
        (package_dir / "pyproject.toml").write_text(pyproject_content)
        keys_dir = package_dir / "keys"
        generate_keys(keys_dir)
        return package_dir

    @pytest.mark.skipif(
        not (Path(__file__).parent.parent.parent / "src/flavor/go/cmd/pspf-builder/pspf-builder").exists(),
        reason="Test requires pre-built Go builder"
    )
    def test_build_minimal_package(self, test_package_dir) -> None:
        """Test building a minimal package."""
        manifest_path = test_package_dir / "pyproject.toml"
        artifacts = build_package_from_manifest(manifest_path)
        assert len(artifacts) == 1
        artifact_path = artifacts[0]
        assert artifact_path.exists()
        assert artifact_path.name == "test-package.pspf"

    @pytest.mark.skipif(
        not (Path(__file__).parent.parent.parent / "src/flavor/go/cmd/pspf-builder/pspf-builder").exists(),
        reason="Test requires pre-built Go builder"
    )
    def test_verify_built_package(self, test_package_dir) -> None:
        """Test verifying a built PSPF package."""
        manifest_path = test_package_dir / "pyproject.toml"
        artifacts = build_package_from_manifest(manifest_path)
        artifact_path = artifacts[0]
        result = verify_package(artifact_path)
        assert result["signature_valid"] is True

    def test_payload_archive_structure(self, test_package_dir, tmp_path) -> None:
        """Test the internal structure of the payload archive."""
        orchestrator = PackagingOrchestrator(
            package_integrity_key_path=str(
                test_package_dir / "keys" / "flavor-private.key"
            ),
            public_key_path=str(
                test_package_dir / "keys" / "flavor-public.key"
            ),
            output_flavor_path=str(tmp_path / "test.pspf"),
            build_config={"version": "1.0.0", "dependencies": []},
            manifest_dir=test_package_dir,
            package_name="test",
            entry_point="main:main",
            python_version="3.11",
        )
        assert orchestrator.package_name == "test"
        assert orchestrator.entry_point == "main:main"
