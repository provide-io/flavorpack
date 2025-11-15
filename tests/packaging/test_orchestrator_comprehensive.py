"""Comprehensive unit tests for PSPF packaging orchestrator."""

import json
from pathlib import Path
import tarfile
import tempfile
from unittest.mock import Mock, patch

import pytest

from flavor.exceptions import BuildError
from flavor.packaging.orchestrator import PackagingOrchestrator


class TestPackagingOrchestratorComprehensive:
    """Comprehensive tests for PackagingOrchestrator."""

    @pytest.fixture
    def orchestrator(self, tmp_path):
        """Create an orchestrator instance with test configuration."""
        return PackagingOrchestrator(
            package_integrity_key_path=str(tmp_path / "test.key"),
            public_key_path=str(tmp_path / "test.pub"),
            output_flavor_path=str(tmp_path / "output.psp"),
            build_config={
                "version": "1.0.0",
                "dependencies": [],
            },
            manifest_dir=tmp_path,
            package_name="test-package",
            entry_point="test.main:run",
            python_version="3.11",
            key_seed="test-seed",  # Use deterministic key generation for tests
        )

    def test_orchestrator_initialization(self, orchestrator, tmp_path) -> None:
        """Test orchestrator initializes with correct values."""
        assert orchestrator.package_integrity_key_path == str(tmp_path / "test.key")
        assert orchestrator.public_key_path == str(tmp_path / "test.pub")
        assert orchestrator.output_flavor_path == str(tmp_path / "output.psp")
        assert orchestrator.package_name == "test-package"
        assert orchestrator.entry_point == "test.main:run"
        assert orchestrator.python_version == "3.11"

    @patch("flavor.packaging.python_packager.PythonPackager.prepare_artifacts")
    def test_build_package_flow(
        self, mock_prepare, orchestrator, tmp_path
    ) -> None:
        """Test the overall flow of the build_package method."""
        # Create the slot files that will be referenced
        payload_tgz = tmp_path / "payload.tgz"
        python_tgz = tmp_path / "python.tgz"
        
        # Create minimal tarball files
        with tarfile.open(payload_tgz, "w:gz") as tar:
            tar.add(__file__, arcname="test.py")
        with tarfile.open(python_tgz, "w:gz") as tar:
            tar.add(__file__, arcname="test.py")
            
        # Setup mocks
        mock_prepare.return_value = {
            "payload_tgz": payload_tgz,
            "python_tgz": python_tgz,
            "payload_dir": tmp_path / "payload",
        }
        (tmp_path / "payload" / "bin").mkdir(parents=True)
        (tmp_path / "payload" / "bin" / "uv").touch()
        (tmp_path / "payload" / "wheels").mkdir()

        # Build the package
        orchestrator.build_package()

        # Verify the package was created
        assert Path(orchestrator.output_flavor_path).exists()
        mock_prepare.assert_called_once()

    @patch("flavor.packaging.python_packager.PythonPackager.prepare_artifacts")  
    def test_build_error_handling(self, mock_prepare, orchestrator, tmp_path) -> None:
        """Test error handling when package preparation fails."""
        # Make the prepare_artifacts fail
        mock_prepare.side_effect = BuildError("Preparation failed!")

        with pytest.raises(BuildError) as exc_info:
            orchestrator.build_package()

        assert "Preparation failed!" in str(exc_info.value)
