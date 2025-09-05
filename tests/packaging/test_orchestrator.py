"""Unit tests for the PackagingOrchestrator."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import attrs
import pytest

from flavor.config import FlavorConfig
from flavor.exceptions import BuildError
from flavor.packaging.orchestrator import PackagingOrchestrator


@pytest.fixture
def mock_flavor_config() -> FlavorConfig:
    """Provides a default FlavorConfig object for tests."""
    return FlavorConfig.from_dict(
        config={
            "build": {},
            "execution": {},
        },
        project_defaults={
            "name": "test-package",
            "version": "1.0.0",
            "entry_point": "test_pkg.main:cli",
        },
    )


@pytest.fixture
def orchestrator(
    tmp_path: Path, mock_flavor_config: FlavorConfig
) -> PackagingOrchestrator:
    """Provides a PackagingOrchestrator instance for tests."""
    return PackagingOrchestrator(
        package_integrity_key_path=None,
        public_key_path=None,
        output_flavor_path=str(tmp_path / "dist/test.psp"),
        build_config={
            **attrs.asdict(mock_flavor_config.build),
            "execution": attrs.asdict(mock_flavor_config.execution),
        },
        manifest_dir=tmp_path,
        package_name=mock_flavor_config.name,
        version=mock_flavor_config.version,
        entry_point=mock_flavor_config.entry_point,
        show_progress=False,
    )


@pytest.fixture
def setup_payload_dir(tmp_path: Path) -> Path:
    """Creates a mock payload directory with necessary files for ingredients."""
    payload_dir = tmp_path / "payload"
    bin_dir = payload_dir / "bin"
    wheels_dir = payload_dir / "wheels"
    bin_dir.mkdir(parents=True)
    wheels_dir.mkdir()
    (bin_dir / "uv").touch()
    return payload_dir


@patch("os.access", return_value=True)
@patch("pathlib.Path.exists", return_value=True)
@patch("flavor.psp.format_2025.builder.PSPFBuilder")
@patch("flavor.packaging.orchestrator.PythonPackager")
@patch("flavor.packaging.orchestrator.find_launcher_executable")
@patch("flavor.packaging.orchestrator.PackagingOrchestrator._detect_launcher_type")
def test_python_builder_flow(
    mock_detect_launcher,
    mock_find_launcher,
    mock_python_packager,
    mock_pspf_builder,
    mock_path_exists,
    mock_os_access,
    orchestrator: PackagingOrchestrator,
    setup_payload_dir: Path,
    tmp_path: Path,
):
    """Test the default Python builder flow is orchestrated correctly."""
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

    orchestrator.build_package()

    mock_python_packager.assert_called_once()
    mock_packager_instance.prepare_artifacts.assert_called_once()
    mock_pspf_builder.create.assert_called_once()
    mock_builder_instance.build.assert_called_once_with(
        Path(orchestrator.output_flavor_path)
    )


@patch("os.access", return_value=True)
@patch("pathlib.Path.exists", return_value=True)
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
    mock_path_exists,
    mock_os_access,
    orchestrator: PackagingOrchestrator,
    setup_payload_dir: Path,
    tmp_path: Path,
):
    """Verify the orchestrator calls the external builder with correct arguments."""
    mock_find_builder.return_value = Path("/path/to/flavor-rs-builder")
    mock_find_launcher.return_value = Path("/path/to/flavor-rs-launcher")
    mock_detect_launcher.return_value = "rust"

    mock_packager_instance = mock_python_packager.return_value
    mock_packager_instance.prepare_artifacts.return_value = {
        "payload_dir": setup_payload_dir,
        "python_tgz": tmp_path / "python.tgz",
    }
    (tmp_path / "python.tgz").touch()

    orchestrator.builder_bin = "/path/to/flavor-rs-builder"
    orchestrator.build_package()

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


@patch("os.access", return_value=True)
@patch("pathlib.Path.exists", return_value=True)
@patch("flavor.packaging.orchestrator.find_launcher_executable")
@patch("flavor.packaging.orchestrator.find_builder_executable")
@patch(
    "flavor.packaging.orchestrator.run_command", side_effect=BuildError("Build failed")
)
@patch("flavor.packaging.orchestrator.PythonPackager")
def test_external_builder_error_handling(
    mock_python_packager,
    mock_run_command,
    mock_find_builder,
    mock_find_launcher,
    mock_path_exists,
    mock_os_access,
    orchestrator: PackagingOrchestrator,
    setup_payload_dir: Path,
    tmp_path: Path,
):
    """Verify that BuildError from run_command is propagated correctly."""
    mock_find_builder.return_value = Path("/fake/builder")
    mock_find_launcher.return_value = Path("/fake/launcher")

    mock_packager_instance = mock_python_packager.return_value
    mock_packager_instance.prepare_artifacts.return_value = {
        "payload_dir": setup_payload_dir,
        "python_tgz": tmp_path / "python.tgz",
    }
    (tmp_path / "python.tgz").touch()

    orchestrator.builder_bin = "/fake/builder"
    with pytest.raises(BuildError, match="Failed to execute command"):
        orchestrator.build_package()


@patch("flavor.packaging.orchestrator.find_launcher_executable")
def test_launcher_not_found(mock_find_launcher, orchestrator: PackagingOrchestrator):
    """Test that a BuildError is raised if the launcher binary is not found."""
    mock_find_launcher.return_value.exists.return_value = False
    with pytest.raises(BuildError, match="Launcher binary not found"):
        orchestrator.build_package()


@patch("flavor.packaging.orchestrator.find_launcher_executable")
@patch("os.access", return_value=False)
def test_launcher_not_executable(
    mock_os_access,
    mock_find_launcher,
    orchestrator: PackagingOrchestrator,
    tmp_path: Path,
):
    """Test that a BuildError is raised if the launcher binary is not executable."""
    launcher_path = tmp_path / "launcher"
    launcher_path.touch()
    mock_find_launcher.return_value = launcher_path

    with pytest.raises(BuildError, match="Launcher binary not executable"):
        orchestrator.build_package()


@patch("flavor.packaging.orchestrator.run_command")
def test_launcher_type_detection(mock_run_command, orchestrator: PackagingOrchestrator):
    """Test the launcher type detection logic for Go and Rust."""
    mock_run_command.return_value.stdout = "flavor-go-launcher version 1.2.3"
    assert orchestrator._detect_launcher_type(Path("go-launcher")) == "go"

    mock_run_command.return_value.stdout = "flavor-rs-launcher 0.5.0"
    assert orchestrator._detect_launcher_type(Path("rs-launcher")) == "rust"

    mock_run_command.return_value.stdout = "some other launcher"
    assert orchestrator._detect_launcher_type(Path("unknown-launcher")) == "rust"
