#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""Test launcher availability and resilience."""

from collections.abc import Callable
import io
import os
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from flavor.exceptions import BuildError
from flavor.packaging.orchestrator import PackagingOrchestrator


@pytest.fixture
def manifest_file(tmp_path: Path) -> Path:
    """Create a simple pyproject.toml manifest file."""
    manifest_path = tmp_path / "pyproject.toml"
    manifest_path.write_text("""    [project]
    name = "test-package"
    version = "1.0.0"

    [tool.flavor]
    entry_point = "test:main"
    """)
    # Also create the buildconfig.toml that the API function expects
    (tmp_path / "buildconfig.toml").touch()

    # Create a minimal Python project structure for pip wheel
    (tmp_path / "test_pkg").mkdir()
    (tmp_path / "test_pkg" / "__init__.py").touch()
    (tmp_path / "test_pkg" / "main.py").write_text("def cli(): pass")

    # Create a dummy setup.py for pip wheel to find
    (tmp_path / "setup.py").write_text("""
from setuptools import setup, find_packages

setup(
    name="test-package",
    version="1.0.0",
    packages=find_packages(),
)
""")
    return manifest_path


@pytest.fixture
def orchestrator_factory(tmp_path: Path) -> Callable[..., PackagingOrchestrator]:
    """Factory to create a PackagingOrchestrator instance for tests."""

    def _factory(**kwargs: Any) -> PackagingOrchestrator:
        defaults = {
            "package_integrity_key_path": None,
            "public_key_path": None,
            "output_flavor_path": str(tmp_path / "dist/test.psp"),
            "build_config": {},
            "manifest_dir": tmp_path,
            "package_name": "test-package",
            "version": "1.0.0",
            "entry_point": "test_pkg.main:cli",
            "show_progress": False,
        }
        defaults.update(kwargs)
        return PackagingOrchestrator(**defaults)

    return _factory


class TestLauncherAvailability:
    """Test launcher availability and error handling with focused unit tests."""

    @patch("flavor.packaging.orchestrator.find_launcher_executable")
    def test_missing_launcher_error(
        self,
        mock_find_launcher: MagicMock,
        orchestrator_factory: Callable[..., PackagingOrchestrator],
        manifest_file: Path,
    ) -> None:
        """Test BuildError is raised when launcher binary does not exist."""
        mock_find_launcher.return_value.exists.return_value = False
        orchestrator = orchestrator_factory(launcher_bin="/fake/launcher")
        with pytest.raises(BuildError, match="Launcher binary not found"):
            orchestrator.build_package()

    @patch("flavor.packaging.orchestrator.find_launcher_executable")
    @patch("os.access", return_value=False)
    def test_launcher_not_executable(
        self,
        mock_os_access: MagicMock,
        mock_find_launcher: MagicMock,
        orchestrator_factory: Callable[..., PackagingOrchestrator],
        tmp_path: Path,
        manifest_file: Path,
    ) -> None:
        """Test BuildError is raised when launcher binary is not executable."""
        launcher_path = tmp_path / "unexecutable-launcher"
        launcher_path.touch()
        mock_find_launcher.return_value = launcher_path
        orchestrator = orchestrator_factory(launcher_bin=launcher_path)
        with pytest.raises(BuildError, match="Launcher binary not executable"):
            orchestrator.build_package()
        mock_os_access.assert_called_with(launcher_path, os.X_OK)

    @patch("flavor.packaging.orchestrator.run")
    def test_corrupted_launcher_detection(
        self,
        mock_run: MagicMock,
        orchestrator_factory: Callable[..., PackagingOrchestrator],
        tmp_path: Path,
    ) -> None:
        """Test BuildError is raised if launcher is corrupted and cannot be executed."""
        # Create a fake launcher file
        launcher_path = tmp_path / "fake-launcher"
        launcher_path.touch()
        launcher_path.chmod(0o755)

        # Mock run to simulate corrupted launcher
        mock_run.side_effect = OSError("Corrupted binary")

        orchestrator = orchestrator_factory(launcher_bin=str(launcher_path))

        # Test that the launcher detection fails properly
        with pytest.raises(BuildError, match="Failed to execute command"):
            orchestrator._detect_launcher_type(launcher_path)

    @patch("flavor.packaging.orchestrator.find_launcher_executable")
    @patch("pathlib.Path.exists", return_value=True)
    @patch("os.access", return_value=True)
    @patch("flavor.packaging.orchestrator.logger.warning")
    @patch("flavor.packaging.orchestrator.PackagingOrchestrator._build_with_python_builder")
    def test_wrong_platform_launcher_warning(
        self,
        mock_build: MagicMock,
        mock_logger: MagicMock,
        mock_access: MagicMock,
        mock_exists: MagicMock,
        mock_find: MagicMock,
        orchestrator_factory: Callable[..., PackagingOrchestrator],
        manifest_file: Path,
    ) -> None:
        """Test that a warning is logged for a platform mismatch."""
        mock_find.return_value = Path("launcher-windows-amd64")
        orchestrator = orchestrator_factory()
        orchestrator.build_package()
        mock_logger.assert_called_once()
        assert "mismatch" in mock_logger.call_args[0][0].lower()


class TestLauncherReproducibility:
    """Test launcher build reproducibility."""

    @patch("os.stat")
    @patch("tarfile.open")
    @patch("gzip.open")
    @patch("shutil.copy2")
    @patch("tempfile.mkdtemp", return_value="/tmp/flavor_build_deterministic")
    @patch("flavor.packaging.orchestrator.find_launcher_executable")
    @patch("pathlib.Path.exists", return_value=True)
    @patch("os.access", return_value=True)
    @patch("flavor.packaging.orchestrator.run")
    @patch("flavor.psp.format_2025.builder.build_package")
    @patch("flavor.packaging.python.packager.PythonPackager.prepare_artifacts")
    @patch("flavor.packaging.orchestrator_helpers.create_python_slot_tarballs")
    @patch("builtins.open")
    @patch("flavor.packaging.orchestrator.HelperManager")
    def test_reproducible_builds_with_same_launcher(
        self,
        mock_helper_manager: MagicMock,
        mock_open: MagicMock,
        mock_create_slot_tarballs: MagicMock,
        mock_prepare_artifacts: MagicMock,
        mock_build: MagicMock,
        mock_run: MagicMock,
        mock_access: MagicMock,
        mock_exists: MagicMock,
        mock_find: MagicMock,
        mock_mkdtemp: MagicMock,
        mock_copy2: MagicMock,
        mock_gzip_open: MagicMock,
        mock_tarfile_open: MagicMock,
        mock_os_stat: MagicMock,
        orchestrator_factory: Callable[..., PackagingOrchestrator],
        tmp_path: Path,
        manifest_file: Path,
    ) -> None:
        """Test that builds with the same launcher are reproducible."""
        self._setup_mocks_for_reproducible_builds(
            mock_helper_manager,
            mock_open,
            mock_create_slot_tarballs,
            mock_prepare_artifacts,
            mock_build,
            mock_run,
            mock_access,
            mock_exists,
            mock_find,
            mock_mkdtemp,
            mock_copy2,
            mock_gzip_open,
            mock_tarfile_open,
            mock_os_stat,
            tmp_path,
        )

        orchestrator1 = orchestrator_factory(key_seed="test-seed", output_flavor_path=tmp_path / "test1.psp")
        orchestrator1.build_package()

        orchestrator2 = orchestrator_factory(key_seed="test-seed", output_flavor_path=tmp_path / "test2.psp")
        orchestrator2.build_package()

        assert mock_build.call_count == 2
        spec1 = mock_build.call_args_list[0][0][0]
        spec2 = mock_build.call_args_list[1][0][0]

        # The specs passed to the pure builder function should be identical
        assert spec1 == spec2

    def _setup_mocks_for_reproducible_builds(
        self,
        mock_helper_manager: MagicMock,
        mock_open: MagicMock,
        mock_create_slot_tarballs: MagicMock,
        mock_prepare_artifacts: MagicMock,
        mock_build: MagicMock,
        mock_run: MagicMock,
        mock_access: MagicMock,
        mock_exists: MagicMock,
        mock_find: MagicMock,
        mock_mkdtemp: MagicMock,
        mock_copy2: MagicMock,
        mock_gzip_open: MagicMock,
        mock_tarfile_open: MagicMock,
        mock_os_stat: MagicMock,
        tmp_path: Path,
    ) -> None:
        mock_os_stat.side_effect = self._get_stat_side_effect()

        mock_copy2.side_effect = self._get_copy2_side_effect()

        mock_gzip_file = MagicMock()
        mock_gzip_file.write.return_value = None
        mock_gzip_file.__enter__.return_value = mock_gzip_file
        mock_gzip_file.__exit__.return_value = None
        mock_gzip_open.return_value = mock_gzip_file

        mock_tar = MagicMock()
        mock_tar.add.return_value = None
        mock_tar.__enter__.return_value = mock_tar
        mock_tar.__exit__.return_value = None
        mock_tarfile_open.return_value = mock_tar

        original_path_open = Path.open

        mock_open.side_effect = self._get_mock_open_side_effect(mock_prepare_artifacts, original_path_open)

        mock_uv_path = MagicMock(spec=Path)
        mock_uv_path.open.return_value.__enter__.return_value = io.BytesIO(b"mock uv content")
        mock_uv_path.resolve.return_value = Path("/mock/payload_dir/bin/uv")
        mock_uv_path.stat.return_value.st_size = 15
        mock_uv_path.exists.return_value = True
        mock_python_tgz_path = MagicMock(spec=Path)
        mock_python_tgz_path.open.return_value.__enter__.return_value = io.BytesIO(b"mock python tgz content")
        mock_python_tgz_path.resolve.return_value = Path("/mock/python.tgz")
        mock_python_tgz_path.stat.return_value.st_size = 23
        mock_python_tgz_path.exists.return_value = True
        mock_wheels_tgz_path = MagicMock(spec=Path)
        mock_wheels_tgz_path.open.return_value.__enter__.return_value = io.BytesIO(b"mock wheels tgz content")
        mock_wheels_tgz_path.resolve.return_value = Path("/mock/wheels.tgz")
        mock_wheels_tgz_path.stat.return_value.st_size = 23
        mock_wheels_tgz_path.exists.return_value = True

        mock_prepare_artifacts.return_value = {
            "uv_binary": mock_uv_path,
            "python_tgz": mock_python_tgz_path,
            "wheels_tgz": mock_wheels_tgz_path,
            "payload_dir": Path("/mock/payload_dir"),
        }

        mock_uv_gz = MagicMock(spec=Path)
        mock_uv_gz.__str__.return_value = "/tmp/flavor_build_deterministic/uv.gz"
        mock_uv_gz.stat.return_value.st_size = 100
        mock_uv_gz.exists.return_value = True
        mock_uv_gz.open.return_value.__enter__.return_value = io.BytesIO(b"mock uv gz content")
        mock_uv_gz.open.return_value.__exit__.return_value = None

        mock_python_tar = MagicMock(spec=Path)
        mock_python_tar.__str__.return_value = "/tmp/flavor_build_deterministic/python.tar.gz"
        mock_python_tar.stat.return_value.st_size = 200
        mock_python_tar.exists.return_value = True
        mock_python_tar.open.return_value.__enter__.return_value = io.BytesIO(b"mock python tar content")
        mock_python_tar.open.return_value.__exit__.return_value = None

        mock_wheels_tar = MagicMock(spec=Path)
        mock_wheels_tar.__str__.return_value = "/tmp/flavor_build_deterministic/wheels.tar.gz"
        mock_wheels_tar.stat.return_value.st_size = 300
        mock_wheels_tar.exists.return_value = True
        mock_wheels_tar.open.return_value.__enter__.return_value = io.BytesIO(b"mock wheels tar content")
        mock_wheels_tar.open.return_value.__exit__.return_value = None

        mock_create_slot_tarballs.return_value = (
            mock_uv_gz,
            mock_python_tar,
            mock_wheels_tar,
        )

        launcher_path = tmp_path / "test-launcher"
        launcher_path.write_bytes(b"\x7fELF\x02\x01\x01\x00" + b"\x00" * 100)
        launcher_path.chmod(0o755)
        mock_find.return_value = launcher_path

    def _get_stat_side_effect(self) -> Callable[..., MagicMock]:
        import stat as stat_module

        def stat_side_effect(path: Path, *args: Any, **kwargs: Any) -> MagicMock:
            mock_stat = MagicMock()
            str_path = str(path)
            if "uv.gz" in str_path:
                mock_stat.st_size = 100
                mock_stat.st_mode = stat_module.S_IFREG | 0o644
            elif "python.tar.gz" in str_path:
                mock_stat.st_size = 200
                mock_stat.st_mode = stat_module.S_IFREG | 0o644
            elif "wheels.tar.gz" in str_path:
                mock_stat.st_size = 300
                mock_stat.st_mode = stat_module.S_IFREG | 0o644
            elif "test-launcher" in str_path:
                mock_stat.st_size = 108  # Size of our fake launcher
                mock_stat.st_mode = stat_module.S_IFREG | 0o755
            elif "helpers" in str_path or str_path.endswith("/"):
                mock_stat.st_size = 0
                mock_stat.st_mode = stat_module.S_IFDIR | 0o755
            else:
                mock_stat.st_size = 0
                mock_stat.st_mode = stat_module.S_IFREG | 0o644
            return mock_stat

        return stat_side_effect

    def _get_copy2_side_effect(self) -> Callable[[Path, Path], Path]:
        def copy2_side_effect(src: Path, dst: Path) -> Path:
            return dst

        return copy2_side_effect

    def _get_mock_open_side_effect(
        self, mock_prepare_artifacts: MagicMock, original_path_open: Callable[..., Any]
    ) -> Callable[..., Any]:
        import io
        from pathlib import Path

        def mock_open_side_effect(file: Path, mode: str = "r", *args: Any, **kwargs: Any) -> Any:
            if file.resolve() == mock_prepare_artifacts.return_value["uv_binary"].resolve():
                return io.BytesIO(b"mock uv content")
            elif file.resolve() == mock_prepare_artifacts.return_value["python_tgz"].resolve():
                return io.BytesIO(b"mock python tgz content")
            elif file.resolve() == mock_prepare_artifacts.return_value["wheels_tgz"].resolve():
                return io.BytesIO(b"mock wheels tgz content")
            else:
                # Call the original Path.open for other files (e.g., manifest_file)
                return original_path_open(file, mode, *args, **kwargs)

        return mock_open_side_effect


# 🌶️📦🔚
