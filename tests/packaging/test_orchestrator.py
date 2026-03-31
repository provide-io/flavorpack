#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""Unit tests for the PackagingOrchestrator."""

from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import attrs
import pytest

from flavor.config import FlavorConfig
from flavor.exceptions import BuildError
from flavor.packaging.orchestrator import PackagingOrchestrator


@pytest.fixture
def mock_flavor_config() -> FlavorConfig:
    """Provides a default FlavorConfig object for tests."""
    return FlavorConfig.from_pyproject_dict(
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
def orchestrator(tmp_path: Path, mock_flavor_config: FlavorConfig) -> PackagingOrchestrator:
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
    """Creates a mock payload directory with necessary files for helpers."""
    payload_dir = tmp_path / "payload"
    bin_dir = payload_dir / "bin"
    wheels_dir = payload_dir / "wheels"
    bin_dir.mkdir(parents=True)
    wheels_dir.mkdir()
    (bin_dir / "uv").touch()
    return payload_dir


@patch("os.access", return_value=True)
@patch("pathlib.Path.exists", return_value=True)
@patch("flavor.psp.format_2025.pspf_builder.PSPFBuilder")
@patch("flavor.packaging.orchestrator.PythonPackager")
@patch("flavor.packaging.orchestrator.find_launcher_executable")
@patch("flavor.packaging.orchestrator.PackagingOrchestrator._detect_launcher_type")
def test_python_builder_flow(
    mock_detect_launcher: MagicMock,
    mock_find_launcher: MagicMock,
    mock_python_packager: MagicMock,
    mock_pspf_builder: MagicMock,
    mock_path_exists: MagicMock,
    mock_os_access: MagicMock,
    orchestrator: PackagingOrchestrator,
    setup_payload_dir: Path,
    tmp_path: Path,
) -> None:
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

    # Set up mock to create the output file as a side effect
    def create_mock_file(output_path: Path) -> MagicMock:
        """Side effect to create mock output file."""
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(b"mock package content" * 1000)
        return mock_build_result

    mock_builder_instance.build.side_effect = create_mock_file

    orchestrator.build_package()

    mock_python_packager.assert_called_once()
    mock_packager_instance.prepare_artifacts.assert_called_once()
    mock_pspf_builder.create.assert_called_once()
    mock_builder_instance.build.assert_called_once_with(Path(orchestrator.output_flavor_path))


@patch("os.access", return_value=True)
@patch("pathlib.Path.exists", return_value=True)
@patch("flavor.packaging.orchestrator.find_launcher_executable")
@patch("flavor.packaging.orchestrator.find_builder_executable")
@patch("flavor.packaging.orchestrator.run")
@patch("flavor.packaging.orchestrator.PythonPackager")
@patch("flavor.packaging.orchestrator.PackagingOrchestrator._detect_launcher_type")
def test_external_builder_command_construction(
    mock_detect_launcher: MagicMock,
    mock_python_packager: MagicMock,
    mock_run: MagicMock,
    mock_find_builder: MagicMock,
    mock_find_launcher: MagicMock,
    mock_path_exists: MagicMock,
    mock_os_access: MagicMock,
    orchestrator: PackagingOrchestrator,
    setup_payload_dir: Path,
    tmp_path: Path,
) -> None:
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

    # Set up mock run to create the output file as a side effect
    def create_mock_file_external(*args: Any, **kwargs: Any) -> None:
        """Side effect to create mock output file for external builder."""
        output_path = Path(orchestrator.output_flavor_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(b"mock package content from external builder" * 1000)
        return None  # run returns None on success

    mock_run.side_effect = create_mock_file_external

    orchestrator.build_package()

    mock_python_packager.assert_called_once()
    mock_packager_instance.prepare_artifacts.assert_called_once()
    mock_run.assert_called_once()

    call_args = mock_run.call_args[0][0]
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
@patch("flavor.packaging.orchestrator.run", side_effect=BuildError("Build failed"))
@patch("flavor.packaging.orchestrator.PythonPackager")
def test_external_builder_error_handling(
    mock_python_packager: MagicMock,
    mock_run: MagicMock,
    mock_find_builder: MagicMock,
    mock_find_launcher: MagicMock,
    mock_path_exists: MagicMock,
    mock_os_access: MagicMock,
    orchestrator: PackagingOrchestrator,
    setup_payload_dir: Path,
    tmp_path: Path,
) -> None:
    """Verify that BuildError from run is propagated correctly."""
    mock_find_builder.return_value = Path("/fake/builder")
    mock_find_launcher.return_value = Path("/fake/launcher")

    mock_packager_instance = mock_python_packager.return_value
    mock_packager_instance.prepare_artifacts.return_value = {
        "payload_dir": setup_payload_dir,
        "python_tgz": tmp_path / "python.tgz",
    }
    (tmp_path / "python.tgz").touch()

    orchestrator.builder_bin = "/fake/builder"
    with pytest.raises(BuildError):
        orchestrator.build_package()


@patch("flavor.packaging.orchestrator.find_launcher_executable")
def test_launcher_not_found(mock_find_launcher: MagicMock, orchestrator: PackagingOrchestrator) -> None:
    """Test that a BuildError is raised if the launcher binary is not found."""
    mock_find_launcher.return_value.exists.return_value = False
    with pytest.raises(BuildError, match="Launcher binary not found"):
        orchestrator.build_package()


@patch("flavor.packaging.orchestrator.find_launcher_executable")
@patch("os.access", return_value=False)
def test_launcher_not_executable(
    mock_os_access: MagicMock,
    mock_find_launcher: MagicMock,
    orchestrator: PackagingOrchestrator,
    tmp_path: Path,
) -> None:
    """Test that a BuildError is raised if the launcher binary is not executable."""
    launcher_path = tmp_path / "launcher"
    launcher_path.touch()
    mock_find_launcher.return_value = launcher_path

    with pytest.raises(BuildError, match="Launcher binary not executable"):
        orchestrator.build_package()


@patch("flavor.packaging.orchestrator.run")
def test_launcher_type_detection(mock_run: MagicMock, orchestrator: PackagingOrchestrator) -> None:
    """Test the launcher type detection logic for Go and Rust."""
    mock_run.return_value.stdout = "flavor-go-launcher version 1.2.3"
    assert orchestrator._detect_launcher_type(Path("go-launcher")) == "go"

    mock_run.return_value.stdout = "flavor-rs-launcher 0.5.0"
    assert orchestrator._detect_launcher_type(Path("rs-launcher")) == "rust"

    mock_run.return_value.stdout = "some other launcher"
    assert orchestrator._detect_launcher_type(Path("unknown-launcher")) == "rust"


# ---------------------------------------------------------------------------
# Regression tests: Windows-aware UV slot target
# The internal Python builder must use "Scripts/uv.exe" on Windows and
# "bin/uv" on Unix.  The external builder manifest (create_builder_manifest)
# must produce a matching UV slot target on each platform.
# ---------------------------------------------------------------------------


@patch("os.access", return_value=True)
@patch("pathlib.Path.exists", return_value=True)
@patch("flavor.packaging.orchestrator.is_windows", return_value=False)
@patch("flavor.psp.format_2025.pspf_builder.PSPFBuilder")
@patch("flavor.packaging.orchestrator.PythonPackager")
@patch("flavor.packaging.orchestrator.find_launcher_executable")
@patch("flavor.packaging.orchestrator.PackagingOrchestrator._detect_launcher_type")
def test_python_builder_uv_slot_target_unix(
    mock_detect_launcher: MagicMock,
    mock_find_launcher: MagicMock,
    mock_python_packager: MagicMock,
    mock_pspf_builder: MagicMock,
    mock_is_windows: MagicMock,
    mock_path_exists: MagicMock,
    mock_os_access: MagicMock,
    orchestrator: PackagingOrchestrator,
    setup_payload_dir: Path,
    tmp_path: Path,
) -> None:
    """On Unix the internal builder UV slot target must be 'bin/uv'."""
    mock_find_launcher.return_value = Path("/path/to/launcher")
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

    def create_mock_file(output_path: Path) -> MagicMock:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(b"mock" * 1000)
        return mock_build_result

    mock_builder_instance.build.side_effect = create_mock_file

    orchestrator.build_package()

    # Find the add_slot call for the "uv" slot
    uv_calls = [c for c in mock_builder_instance.add_slot.call_args_list if c.kwargs.get("id") == "uv"]
    assert len(uv_calls) == 1, "Expected exactly one add_slot call for 'uv'"
    assert uv_calls[0].kwargs["target"] == "bin/uv"


@patch("os.access", return_value=True)
@patch("pathlib.Path.exists", return_value=True)
@patch("flavor.packaging.orchestrator.is_windows", return_value=True)
@patch("flavor.psp.format_2025.pspf_builder.PSPFBuilder")
@patch("flavor.packaging.orchestrator.PythonPackager")
@patch("flavor.packaging.orchestrator.find_launcher_executable")
@patch("flavor.packaging.orchestrator.PackagingOrchestrator._detect_launcher_type")
def test_python_builder_uv_slot_target_windows(
    mock_detect_launcher: MagicMock,
    mock_find_launcher: MagicMock,
    mock_python_packager: MagicMock,
    mock_pspf_builder: MagicMock,
    mock_is_windows: MagicMock,
    mock_path_exists: MagicMock,
    mock_os_access: MagicMock,
    orchestrator: PackagingOrchestrator,
    setup_payload_dir: Path,
    tmp_path: Path,
) -> None:
    """When is_windows() returns True the UV slot target must be 'Scripts/uv.exe'."""
    mock_find_launcher.return_value = Path("/path/to/launcher")
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

    def create_mock_file(output_path: Path) -> MagicMock:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(b"mock" * 1000)
        return mock_build_result

    mock_builder_instance.build.side_effect = create_mock_file

    orchestrator.build_package()

    uv_calls = [c for c in mock_builder_instance.add_slot.call_args_list if c.kwargs.get("id") == "uv"]
    assert len(uv_calls) == 1, "Expected exactly one add_slot call for 'uv'"
    assert uv_calls[0].kwargs["target"] == "Scripts/uv.exe"


@patch("flavor.packaging.orchestrator_helpers.is_windows", return_value=False)
def test_external_builder_uv_slot_target_unix(mock_is_windows: MagicMock, tmp_path: Path) -> None:
    """External builder manifest UV slot target must be 'bin/uv' on Unix."""
    from flavor.packaging.orchestrator_helpers import create_builder_manifest

    slots = {
        "uv": tmp_path / "uv",
        "python": tmp_path / "python.tgz",
        "wheels": tmp_path / "wheels.tar",
    }
    key_paths: dict[str, str | None] = {"private": None, "public": None}

    manifest = create_builder_manifest(
        package_name="testpkg",
        version="1.0.0",
        build_config={},
        slots=slots,
        key_paths=key_paths,
    )

    uv_slots = [s for s in manifest["slots"] if s["id"] == "uv"]
    assert len(uv_slots) == 1
    assert uv_slots[0]["target"] == "bin/uv"


@patch("flavor.packaging.orchestrator_helpers.is_windows", return_value=True)
def test_external_builder_uv_slot_target_windows(mock_is_windows: MagicMock, tmp_path: Path) -> None:
    """External builder manifest UV slot target must use Windows path when is_windows() is True."""
    from flavor.packaging.orchestrator_helpers import create_builder_manifest

    slots = {
        "uv": tmp_path / "uv.exe",
        "python": tmp_path / "python.tgz",
        "wheels": tmp_path / "wheels.tar",
    }
    key_paths: dict[str, str | None] = {"private": None, "public": None}

    manifest = create_builder_manifest(
        package_name="testpkg",
        version="1.0.0",
        build_config={},
        slots=slots,
        key_paths=key_paths,
    )

    uv_slots = [s for s in manifest["slots"] if s["id"] == "uv"]
    assert len(uv_slots) == 1
    assert uv_slots[0]["target"] == "Scripts/uv.exe"


@patch("flavor.packaging.orchestrator_helpers.is_windows")
def test_internal_and_external_uv_slot_target_consistent_unix(
    mock_helpers_is_windows: MagicMock,
    tmp_path: Path,
) -> None:
    """On Unix, internal and external builders must agree on the UV slot target."""
    from flavor.packaging.orchestrator_helpers import create_builder_manifest

    mock_helpers_is_windows.return_value = False

    slots = {
        "uv": tmp_path / "uv",
        "python": tmp_path / "python.tgz",
        "wheels": tmp_path / "wheels.tar",
    }
    key_paths: dict[str, str | None] = {"private": None, "public": None}

    manifest = create_builder_manifest(
        package_name="testpkg",
        version="1.0.0",
        build_config={},
        slots=slots,
        key_paths=key_paths,
    )

    external_uv_target = next(s["target"] for s in manifest["slots"] if s["id"] == "uv")

    # Internal builder logic (mirrors orchestrator.py line 190)
    internal_uv_target = "bin/uv"

    assert external_uv_target == internal_uv_target, (
        f"Unix UV slot target mismatch: internal={internal_uv_target!r}, external={external_uv_target!r}"
    )


# 🌶️📦🔚
