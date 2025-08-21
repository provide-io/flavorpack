"""Unit tests for the PackagingOrchestrator."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from flavor.config import FlavorConfig
from flavor.exceptions import BuildError
from flavor.packaging.orchestrator import PackagingOrchestrator


@pytest.fixture
def mock_flavor_config() -> FlavorConfig:
    """Provides a default FlavorConfig object for tests."""
    return FlavorConfig.from_dict(
        config={
            "name": "test-package",
            "version": "1.0.0",
            "entry_point": "test_pkg.main:cli",
            "build": {},
            "execution": {},
        },
        project_defaults={},
    )


@pytest.fixture
def orchestrator(tmp_path: Path, mock_flavor_config: FlavorConfig) -> PackagingOrchestrator:
    """Provides a PackagingOrchestrator instance for tests."""
    return PackagingOrchestrator(
        package_integrity_key_path=None,
        public_key_path=None,
        output_flavor_path=str(tmp_path / "dist/test.psp"),
        flavor_config=mock_flavor_config,
        manifest_dir=tmp_path,
        show_progress=False,
    )


@pytest.fixture
def setup_payload_dir(tmp_path: Path) -> Path:
    """Creates a mock payload directory with necessary files for helpers."""
    payload_dir = tmp_path / "payload"
    bin_dir = payload_dir / "bin"
    wheels_dir = payload_dir / "wheels"
    bin_dir.mkdir(parents=True)
    wheels_dir.mkdir()
    # This `uv` file is required by `create_slot_tarballs`.
    (bin_dir / "uv").touch()
    return payload_dir


@patch("flavor.psp.format_2025.builder.PSPFBuilder")
@patch("flavor.packaging.orchestrator.PythonPackager")
@patch("flavor.packaging.orchestrator.find_launcher_executable")
@patch("flavor.packaging.orchestrator.PackagingOrchestrator._detect_launcher_type")
def test_python_builder_flow(
    mock_detect_launcher,
    mock_find_launcher,
    mock_python_packager,
    mock_pspf_builder,
    orchestrator: PackagingOrchestrator,
    setup_payload_dir: Path,
    tmp_path: Path,
):
    """Test the default Python builder flow is orchestrated correctly."""
    # --- Setup Mocks ---
    mock_find_launcher.return_value = Path("/path/to/flavor-rs-launcher")
    mock_detect_launcher.return_value = "rust"

    mock_packager_instance = mock_python_packager.return_value
    mock_packager_instance.prepare_artifacts.return_value = {
        "payload_dir": setup_payload_dir,
        "python_tgz": tmp_path / "python.tgz",
    }
    (tmp_path / "python.tgz").touch()

    mock_builder_instance = mock_pspf_builder.create.return_value
    mock_build_result = MagicMock()
    mock_build_result.success = True
    mock_builder_instance.metadata.return_value = mock_builder_instance
    mock_builder_instance.add_slot.return_value = mock_builder_instance
    mock_builder_instance.with_options.return_value = mock_builder_instance
    mock_builder_instance.with_keys.return_value = mock_builder_instance
    mock_builder_instance.build.return_value = mock_build_result

    # --- Execute ---
    orchestrator.build_package()

    # --- Assertions ---
    mock_python_packager.assert_called_once()
    mock_packager_instance.prepare_artifacts.assert_called_once()
    mock_pspf_builder.create.assert_called_once()
    mock_builder_instance.build.assert_called_once_with(Path(orchestrator.output_flavor_path))


@patch("flavor.packaging.orchestrator.find_launcher_executable")
@patch("flavor.packaging.orchestrator.find_builder_executable")
@patch("flavor.packaging.orchestrator.run_command")
@patch("flavor.packaging.orchestrator.PythonPackager")
@patch("flavor.packaging.orchestrator.PackagingOrchestrator._detect_launcher_type")
def test_external_builder_command_construction(
    mock_detect_launcher,
    mock_python_packager,
    mock_run_command,
    mock_find_builder,
    mock_find_launcher,
    orchestrator: PackagingOrchestrator,
    setup_payload_dir: Path,
    tmp_path: Path,
):
    """Verify the orchestrator calls the external builder with correct arguments."""
    # --- Setup Mocks ---
    mock_find_builder.return_value = Path("/path/to/flavor-rs-builder")
    mock_find_launcher.return_value = Path("/path/to/flavor-rs-launcher")
    mock_detect_launcher.return_value = "rust"

    mock_packager_instance = mock_python_packager.return_value
    mock_packager_instance.prepare_artifacts.return_value = {
        "payload_dir": setup_payload_dir,
        "python_tgz": tmp_path / "python.tgz",
    }
    (tmp_path / "python.tgz").touch()

    # --- Execute ---
    orchestrator.builder_bin = "/path/to/flavor-rs-builder"
    orchestrator.build_package()

    # --- Assertions ---
    mock_python_packager.assert_called_once()
    mock_packager_instance.prepare_artifacts.assert_called_once()
    mock_run_command.assert_called_once()

    call_args = mock_run_command.call_args[0][0]
    assert call_args[0] == "/path/to/flavor-rs-builder"
    assert "--manifest" in call_args
    assert "--output" in call_args
    assert orchestrator.output_flavor_path in call_args
    assert "--launcher-bin" in call_args
    assert "/path/to/flavor-rs-launcher" in call_args


@patch("flavor.packaging.orchestrator.find_launcher_executable")
@patch("flavor.packaging.orchestrator.find_builder_executable")
@patch("flavor.packaging.orchestrator.run_command", side_effect=BuildError("Build failed"))
@patch("flavor.packaging.orchestrator.PythonPackager")
def test_external_builder_error_handling(
    mock_python_packager,
    mock_run_command,
    mock_find_builder,
    mock_find_launcher,
    orchestrator: PackagingOrchestrator,
    setup_payload_dir: Path,
    tmp_path: Path,
):
    """Verify that BuildError from run_command is propagated correctly."""
    # --- Setup Mocks ---
    mock_find_builder.return_value = Path("/fake/builder")
    mock_find_launcher.return_value = Path("/fake/launcher")

    mock_packager_instance = mock_python_packager.return_value
    mock_packager_instance.prepare_artifacts.return_value = {
        "payload_dir": setup_payload_dir,
        "python_tgz": tmp_path / "python.tgz",
    }
    (tmp_path / "python.tgz").touch()

    # --- Execute & Assert ---
    orchestrator.builder_bin = "/fake/builder"
    with pytest.raises(BuildError, match="Build failed"):
        orchestrator.build_package()
