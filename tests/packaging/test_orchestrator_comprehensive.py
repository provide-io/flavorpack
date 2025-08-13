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
            output_flavor_path=str(tmp_path / "output.pspf"),
            build_config={
                "version": "1.0.0",
                "dependencies": [],
            },
            manifest_dir=tmp_path,
            package_name="test-package",
            entry_point="test.main:run",
            python_version="3.11",
        )

    def test_orchestrator_initialization(self, orchestrator, tmp_path) -> None:
        """Test orchestrator initializes with correct values."""
        assert orchestrator.package_integrity_key_path == str(tmp_path / "test.key")
        assert orchestrator.public_key_path == str(tmp_path / "test.pub")
        assert orchestrator.output_flavor_path == str(tmp_path / "output.pspf")
        assert orchestrator.package_name == "test-package"
        assert orchestrator.entry_point == "test.main:run"
        assert orchestrator.python_version == "3.11"

    @patch("flavor.packaging.orchestrator.PackagingOrchestrator._run_subprocess")
    @patch("flavor.packaging.python_packager.PythonPackager.prepare_artifacts")
    @patch("flavor.packaging.python_packager.PythonPackager.compute_signature")
    def test_build_package_flow(
        self, mock_sign, mock_prepare, mock_run, orchestrator, tmp_path
    ) -> None:
        """Test the overall flow of the build_package method."""
        # Setup mocks
        mock_prepare.return_value = {
            "payload_tgz": tmp_path / "payload.tgz",
            "python_tgz": tmp_path / "python.tgz",
            "payload_dir": tmp_path / "payload",
        }
        (tmp_path / "payload" / "bin").mkdir(parents=True)
        (tmp_path / "payload" / "bin" / "uv").touch()
        (tmp_path / "payload" / "wheels").mkdir()
        mock_sign.return_value = b"fakesig"
        mock_run.return_value = "Success"

        orchestrator.build_package()

        mock_prepare.assert_called_once()
        mock_sign.assert_called_once()
        
        # Check that the final build command was called
        final_build_call = mock_run.call_args_list[-1]
        args = final_build_call.args[0]
        assert "pspf-builder" in args[0]
        assert "--manifest" in args
        assert "--output" in args
        assert orchestrator.output_flavor_path in args

    @patch("flavor.packaging.orchestrator.subprocess.run")
    def test_build_error_handling(self, mock_run, orchestrator) -> None:
        """Test error handling when subprocess fails."""
        mock_run.side_effect = BuildError("Build failed!")

        with pytest.raises(BuildError) as exc_info:
            # We need to mock the python_packager part to isolate the subprocess call
            with patch("flavor.packaging.python_packager.PythonPackager"):
                 orchestrator.build_package()

        assert "Build failed!" in str(exc_info.value)
