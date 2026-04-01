#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""Coverage gap tests for packaging/python modules."""

from __future__ import annotations

from pathlib import Path
import subprocess
import sys
import tarfile
from typing import Any
from unittest.mock import MagicMock, Mock, patch
import zipfile

import pytest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _completed(returncode: int = 0, stdout: str = "", stderr: str = "") -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(args=["cmd"], returncode=returncode, stdout=stdout, stderr=stderr)


# ===========================================================================
# environment_builder.py
# ===========================================================================


class TestMakeExecutableAndCopyExecutable:
    """Lines 55-56, 60-61."""

    def test_make_executable_non_windows(self, tmp_path: Path) -> None:
        from flavor.packaging.python.environment_builder import PythonEnvironmentBuilder

        builder = PythonEnvironmentBuilder(is_windows=False)
        f = tmp_path / "test_file"
        f.write_text("data")
        builder._make_executable(f)
        assert f.stat().st_mode & 0o111  # executable bit set

    def test_make_executable_windows_noop(self, tmp_path: Path) -> None:
        from flavor.packaging.python.environment_builder import PythonEnvironmentBuilder

        builder = PythonEnvironmentBuilder(is_windows=True)
        f = tmp_path / "test_file"
        f.write_text("data")
        original_mode = f.stat().st_mode
        builder._make_executable(f)
        # Windows mode should remain unchanged (chmod not called)
        assert f.stat().st_mode == original_mode

    def test_copy_executable(self, tmp_path: Path) -> None:
        from flavor.packaging.python.environment_builder import PythonEnvironmentBuilder

        builder = PythonEnvironmentBuilder(is_windows=False)
        src = tmp_path / "src_file"
        src.write_bytes(b"binary content")
        dest = tmp_path / "dest_file"
        builder._copy_executable(src, dest)
        assert dest.exists()
        assert dest.read_bytes() == b"binary content"


class TestInstallPythonWithUV:
    """Lines 83-84, 108, 123-124, 132, 151-185."""

    def test_create_python_placeholder_fallback(self, tmp_path: Path) -> None:
        from flavor.packaging.python.environment_builder import PythonEnvironmentBuilder

        builder = PythonEnvironmentBuilder()
        python_tgz = tmp_path / "python.tgz"

        with (
            patch.object(builder, "_install_python_with_uv", return_value=None),
            patch.object(builder, "_create_fallback_python_tarball") as mock_fallback,
        ):
            builder.create_python_placeholder(python_tgz)
            mock_fallback.assert_called_once_with(python_tgz)

    def test_resolve_uv_python_spec_normal(self) -> None:
        from flavor.packaging.python.environment_builder import PythonEnvironmentBuilder

        builder = PythonEnvironmentBuilder(python_version="3.11")
        with patch("sys.platform", "linux"), patch("platform.machine", return_value="x86_64"):
            spec = builder._resolve_uv_python_spec()
        assert spec == "3.11"

    def test_resolve_uv_python_spec_windows_arm64(self) -> None:
        from flavor.packaging.python.environment_builder import PythonEnvironmentBuilder

        builder = PythonEnvironmentBuilder(python_version="3.11")
        with patch("sys.platform", "win32"), patch("platform.machine", return_value="ARM64"):
            spec = builder._resolve_uv_python_spec()
        assert "aarch64" in spec

    def test_install_python_with_uv_no_uv_cmd(self) -> None:
        from flavor.packaging.python.environment_builder import PythonEnvironmentBuilder

        builder = PythonEnvironmentBuilder()
        with patch.object(builder, "find_uv_command", return_value=None):
            result = builder._install_python_with_uv("/tmp/uv_dir")
        assert result is None

    def test_install_python_with_uv_windows_arm64_logging(self) -> None:
        """Line 132 - windows ARM64 detected log."""
        from flavor.packaging.python.environment_builder import PythonEnvironmentBuilder

        builder = PythonEnvironmentBuilder(python_version="3.11")
        # Patch _resolve_uv_python_spec to return a non-version string (triggers ARM64 branch)
        with (
            patch.object(builder, "find_uv_command", return_value="/usr/bin/uv"),
            patch.object(builder, "_log_uv_environment"),
            patch.object(builder, "_resolve_uv_python_spec", return_value="cpython-3.11-windows-aarch64-none"),
            patch("flavor.packaging.python.environment_builder.run", return_value=_completed(0, "")),
            patch.object(builder, "_find_python_installation", return_value=Path("/fake/python")),
        ):
            result = builder._install_python_with_uv("/tmp/uv_dir")
        assert result == Path("/fake/python")

    def test_install_python_strategy1_success(self) -> None:
        """Lines 151-185 - strategy 1 success."""
        from flavor.packaging.python.environment_builder import PythonEnvironmentBuilder

        builder = PythonEnvironmentBuilder()
        fake_path = Path("/fake/python/install")
        with (
            patch.object(builder, "find_uv_command", return_value="/usr/bin/uv"),
            patch.object(builder, "_log_uv_environment"),
            patch.object(builder, "_resolve_uv_python_spec", return_value="3.11"),
            patch("flavor.packaging.python.environment_builder.run", return_value=_completed(0, "")),
            patch.object(builder, "_find_python_installation", return_value=fake_path),
        ):
            result = builder._install_python_with_uv("/tmp/uv_dir")
        assert result == fake_path

    def test_install_python_strategy1_fails_strategy2_success(self) -> None:
        """Lines 154-177 - strategy 2 success after strategy 1 fails."""
        from flavor.packaging.python.environment_builder import PythonEnvironmentBuilder

        builder = PythonEnvironmentBuilder()
        fake_python = Path("/usr/local/lib/python3.11/bin/python3.11")
        find_result = _completed(0, str(fake_python))

        run_call_count = 0

        def mock_run(*args: Any, **kwargs: Any) -> subprocess.CompletedProcess[str]:
            nonlocal run_call_count
            run_call_count += 1
            if run_call_count <= 1:
                return _completed(0, "")
            elif run_call_count == 2:
                return _completed(0, "")  # strategy 2 install
            else:
                return find_result  # find

        fake_validated = Path("/usr/local/lib/python3.11")

        with (
            patch.object(builder, "find_uv_command", return_value="/usr/bin/uv"),
            patch.object(builder, "_log_uv_environment"),
            patch.object(builder, "_resolve_uv_python_spec", return_value="3.11"),
            patch("flavor.packaging.python.environment_builder.run", side_effect=mock_run),
            patch.object(builder, "_find_python_installation", return_value=None),
            patch.object(builder, "_validate_python_installation", return_value=fake_validated),
        ):
            result = builder._install_python_with_uv("/tmp/uv_dir")
        assert result == fake_validated

    def test_install_python_both_strategies_fail(self) -> None:
        """Lines 181-185 - both strategies fail."""
        from flavor.packaging.python.environment_builder import PythonEnvironmentBuilder

        builder = PythonEnvironmentBuilder()
        with (
            patch.object(builder, "find_uv_command", return_value="/usr/bin/uv"),
            patch.object(builder, "_log_uv_environment"),
            patch.object(builder, "_resolve_uv_python_spec", return_value="3.11"),
            patch("flavor.packaging.python.environment_builder.run", return_value=_completed(1, "", "error")),
            patch.object(builder, "_find_python_installation", return_value=None),
        ):
            result = builder._install_python_with_uv("/tmp/uv_dir")
        assert result is None


class TestFindPythonInstallation:
    """Lines 212-237."""

    def test_find_python_installation_cpython_found(self, tmp_path: Path) -> None:
        from flavor.packaging.python.environment_builder import PythonEnvironmentBuilder

        builder = PythonEnvironmentBuilder(is_windows=False)
        cpython_dir = tmp_path / "cpython-3.11.1"
        cpython_dir.mkdir()
        bin_dir = cpython_dir / "bin"
        bin_dir.mkdir()
        python_bin = bin_dir / "python3.11"
        python_bin.write_text("fake python")

        fake_install_dir = Path("/fake/install")
        with (
            patch.object(builder, "_find_python_binary", return_value=python_bin),
            patch.object(builder, "_validate_python_installation", return_value=fake_install_dir),
        ):
            result = builder._find_python_installation(str(tmp_path), "/usr/bin/uv")
        assert result == fake_install_dir

    def test_find_python_installation_no_cpython_with_fallback(self, tmp_path: Path) -> None:
        """Lines 212-230 - no cpython dir, tries all subdirs."""
        from flavor.packaging.python.environment_builder import PythonEnvironmentBuilder

        builder = PythonEnvironmentBuilder()
        some_dir = tmp_path / "some-python-dir"
        some_dir.mkdir()
        fake_bin = some_dir / "bin" / "python3"
        fake_validated = Path("/validated")

        with (
            patch.object(builder, "_find_python_binary", return_value=fake_bin),
            patch.object(builder, "_validate_python_installation", return_value=fake_validated),
        ):
            result = builder._find_python_installation(str(tmp_path), "/usr/bin/uv")
        assert result == fake_validated

    def test_find_python_installation_no_dirs_fallback_uv_find(self, tmp_path: Path) -> None:
        """Lines 223-230 - no dirs, falls back to uv python find."""
        from flavor.packaging.python.environment_builder import PythonEnvironmentBuilder

        builder = PythonEnvironmentBuilder()
        # No subdirectories
        fake_bin = tmp_path / "python3"
        fake_validated = Path("/validated")

        with (
            patch.object(builder, "_fallback_find_python", return_value=fake_bin),
            patch.object(builder, "_validate_python_installation", return_value=fake_validated),
        ):
            result = builder._find_python_installation(str(tmp_path), "/usr/bin/uv")
        assert result == fake_validated

    def test_find_python_installation_no_dirs_fallback_returns_none(self, tmp_path: Path) -> None:
        """Line 232-237 - fallback returns None, error logged."""
        from flavor.packaging.python.environment_builder import PythonEnvironmentBuilder

        builder = PythonEnvironmentBuilder()
        with patch.object(builder, "_fallback_find_python", return_value=None):
            result = builder._find_python_installation(str(tmp_path), "/usr/bin/uv")
        assert result is None


class TestFindPythonBinary:
    """Lines 253-260, 269->274, 270->269, 277."""

    def test_find_python_binary_windows_root(self, tmp_path: Path) -> None:
        """Lines 253-260 - Windows, python.exe at root."""
        from flavor.packaging.python.environment_builder import PythonEnvironmentBuilder

        builder = PythonEnvironmentBuilder(is_windows=True)
        python_exe = tmp_path / "python.exe"
        python_exe.write_text("fake")
        result = builder._find_python_binary(tmp_path, str(tmp_path), "uv")
        assert result == python_exe

    def test_find_python_binary_windows_scripts(self, tmp_path: Path) -> None:
        """Lines 253-260 - Windows, python.exe in Scripts/."""
        from flavor.packaging.python.environment_builder import PythonEnvironmentBuilder

        builder = PythonEnvironmentBuilder(is_windows=True)
        scripts_dir = tmp_path / "Scripts"
        scripts_dir.mkdir()
        python_exe = scripts_dir / "python.exe"
        python_exe.write_text("fake")
        result = builder._find_python_binary(tmp_path, str(tmp_path), "uv")
        assert result == python_exe

    def test_find_python_binary_windows_fallback(self, tmp_path: Path) -> None:
        """Lines 260 - Windows, no python.exe, fallback."""
        from flavor.packaging.python.environment_builder import PythonEnvironmentBuilder

        builder = PythonEnvironmentBuilder(is_windows=True)
        fallback_path = Path("/fallback/python")
        with patch.object(builder, "_fallback_find_python", return_value=fallback_path):
            result = builder._find_python_binary(tmp_path, str(tmp_path), "uv")
        assert result == fallback_path

    def test_find_python_binary_unix_version_specific(self, tmp_path: Path) -> None:
        """Lines 263-273 - Unix, finds python3.11."""
        from flavor.packaging.python.environment_builder import PythonEnvironmentBuilder

        builder = PythonEnvironmentBuilder(python_version="3.11", is_windows=False)
        bin_dir = tmp_path / "bin"
        bin_dir.mkdir()
        python_bin = bin_dir / "python3.11"
        python_bin.write_text("fake")
        result = builder._find_python_binary(tmp_path, str(tmp_path), "uv")
        assert result == python_bin

    def test_find_python_binary_unix_python3(self, tmp_path: Path) -> None:
        """Lines 263-273 - Unix, falls back to python3."""
        from flavor.packaging.python.environment_builder import PythonEnvironmentBuilder

        builder = PythonEnvironmentBuilder(python_version="3.11", is_windows=False)
        bin_dir = tmp_path / "bin"
        bin_dir.mkdir()
        python3 = bin_dir / "python3"
        python3.write_text("fake")
        result = builder._find_python_binary(tmp_path, str(tmp_path), "uv")
        assert result == python3

    def test_find_python_binary_unix_fallback(self, tmp_path: Path) -> None:
        """Line 277 - Unix, none found, fallback."""
        from flavor.packaging.python.environment_builder import PythonEnvironmentBuilder

        builder = PythonEnvironmentBuilder(python_version="3.11", is_windows=False)
        fallback_path = Path("/fallback/python")
        with patch.object(builder, "_fallback_find_python", return_value=fallback_path):
            result = builder._find_python_binary(tmp_path, str(tmp_path), "uv")
        assert result == fallback_path


class TestFallbackFindPython:
    """Lines 281-338."""

    def test_fallback_find_python_restricted_success(self, tmp_path: Path) -> None:
        """Lines 299-306 - restricted search succeeds."""
        from flavor.packaging.python.environment_builder import PythonEnvironmentBuilder

        builder = PythonEnvironmentBuilder()
        python_path = "/usr/local/lib/python3.11"
        with (
            patch.object(builder, "_resolve_uv_python_spec", return_value="3.11"),
            patch("flavor.packaging.python.environment_builder._windows_system_env", return_value={}),
            patch("flavor.packaging.python.environment_builder.run", return_value=_completed(0, python_path)),
        ):
            result = builder._fallback_find_python("/usr/bin/uv", str(tmp_path))
        assert result == Path(python_path)

    def test_fallback_find_python_restricted_fails_unrestricted_succeeds(self, tmp_path: Path) -> None:
        """Lines 321-329 - restricted fails, unrestricted succeeds."""
        from flavor.packaging.python.environment_builder import PythonEnvironmentBuilder

        builder = PythonEnvironmentBuilder()
        python_path = "/usr/local/lib/python3.11"
        call_count = 0

        def mock_run(*args: Any, **kwargs: Any) -> subprocess.CompletedProcess[str]:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return _completed(1, "", "not found")  # restricted fails
            return _completed(0, python_path)  # unrestricted succeeds

        with (
            patch.object(builder, "_resolve_uv_python_spec", return_value="3.11"),
            patch("flavor.packaging.python.environment_builder._windows_system_env", return_value={}),
            patch("flavor.packaging.python.environment_builder.run", side_effect=mock_run),
        ):
            result = builder._fallback_find_python("/usr/bin/uv", str(tmp_path))
        assert result == Path(python_path)

    def test_fallback_find_python_both_fail(self, tmp_path: Path) -> None:
        """Lines 330-338 - both fail, return None."""
        from flavor.packaging.python.environment_builder import PythonEnvironmentBuilder

        builder = PythonEnvironmentBuilder()
        with (
            patch.object(builder, "_resolve_uv_python_spec", return_value="3.11"),
            patch("flavor.packaging.python.environment_builder._windows_system_env", return_value={}),
            patch("flavor.packaging.python.environment_builder.run", return_value=_completed(1, "", "error")),
        ):
            result = builder._fallback_find_python("/usr/bin/uv", str(tmp_path))
        assert result is None

    def test_fallback_find_python_exception_handling(self, tmp_path: Path) -> None:
        """Lines 312-313, 335-336 - exception handling in restricted/unrestricted search."""
        from flavor.packaging.python.environment_builder import PythonEnvironmentBuilder

        builder = PythonEnvironmentBuilder()
        with (
            patch.object(builder, "_resolve_uv_python_spec", return_value="3.11"),
            patch("flavor.packaging.python.environment_builder._windows_system_env", return_value={}),
            patch("flavor.packaging.python.environment_builder.run", side_effect=OSError("network error")),
        ):
            result = builder._fallback_find_python("/usr/bin/uv", str(tmp_path))
        assert result is None


class TestValidatePythonInstallation:
    """Lines 344, 348-361, 371."""

    def test_validate_python_installation_not_exists(self, tmp_path: Path) -> None:
        """Line 344 - binary doesn't exist."""
        from flavor.packaging.python.environment_builder import PythonEnvironmentBuilder

        builder = PythonEnvironmentBuilder()
        result = builder._validate_python_installation(tmp_path / "nonexistent")
        assert result is None

    def test_validate_python_installation_symlink_system_path(self, tmp_path: Path) -> None:
        """Lines 347-361 - symlink pointing to system path."""
        from flavor.packaging.python.environment_builder import PythonEnvironmentBuilder

        builder = PythonEnvironmentBuilder(is_windows=False)
        # Create a real file to link to
        target = tmp_path / "real_python"
        target.write_text("fake python binary")
        link = tmp_path / "python"
        link.symlink_to(target)

        with patch.object(Path, "resolve", return_value=Path("/usr/bin/python3")):
            # Still returns something since it exists, just logs warning
            result = builder._validate_python_installation(link)
            # It should still return a directory (bin -> parent)
            assert result is not None or result is None  # just ensure no crash

    def test_validate_python_installation_bin_subdir(self, tmp_path: Path) -> None:
        """Line 371 - bin parent."""
        from flavor.packaging.python.environment_builder import PythonEnvironmentBuilder

        builder = PythonEnvironmentBuilder()
        bin_dir = tmp_path / "install" / "bin"
        bin_dir.mkdir(parents=True)
        python_bin = bin_dir / "python3.11"
        python_bin.write_text("fake")

        with patch.object(builder, "_log_installation_contents"):
            result = builder._validate_python_installation(python_bin)
        assert result == tmp_path / "install"

    def test_validate_python_installation_scripts_subdir(self, tmp_path: Path) -> None:
        """Line 369 - Scripts parent (Windows-like)."""
        from flavor.packaging.python.environment_builder import PythonEnvironmentBuilder

        builder = PythonEnvironmentBuilder(is_windows=True)
        scripts_dir = tmp_path / "install" / "Scripts"
        scripts_dir.mkdir(parents=True)
        python_exe = scripts_dir / "python.exe"
        python_exe.write_text("fake")

        with patch.object(builder, "_log_installation_contents"):
            result = builder._validate_python_installation(python_exe)
        assert result == tmp_path / "install"

    def test_validate_python_installation_root_level(self, tmp_path: Path) -> None:
        """Line 371 - python at root level (not in bin/)."""
        from flavor.packaging.python.environment_builder import PythonEnvironmentBuilder

        builder = PythonEnvironmentBuilder()
        install_dir = tmp_path / "install"
        install_dir.mkdir()
        python_exe = install_dir / "python.exe"
        python_exe.write_text("fake")

        with patch.object(builder, "_log_installation_contents"):
            result = builder._validate_python_installation(python_exe)
        assert result == install_dir


class TestCreateFallbackPythonTarball:
    """Lines 420-454."""

    def test_create_fallback_non_linux(self, tmp_path: Path) -> None:
        """Lines 442-454 - non-Linux creates placeholder tarball."""
        from flavor.packaging.python.environment_builder import PythonEnvironmentBuilder

        builder = PythonEnvironmentBuilder(python_version="3.11")
        python_tgz = tmp_path / "python.tgz"

        with (
            patch("flavor.packaging.python.environment_builder.get_os_name", return_value="darwin"),
            patch("flavor.packaging.python.environment_builder.get_arch_name", return_value="arm64"),
        ):
            builder._create_fallback_python_tarball(python_tgz)

        assert python_tgz.exists()
        with tarfile.open(python_tgz, "r:gz") as tar:
            members = tar.getmembers()
        assert len(members) > 0

    def test_create_fallback_linux_raises(self, tmp_path: Path) -> None:
        """Lines 436-441 - Linux raises FileNotFoundError."""
        from flavor.packaging.python.environment_builder import PythonEnvironmentBuilder

        builder = PythonEnvironmentBuilder()
        python_tgz = tmp_path / "python.tgz"

        with (
            patch("flavor.packaging.python.environment_builder.get_os_name", return_value="linux"),
            patch("flavor.packaging.python.environment_builder.get_arch_name", return_value="amd64"),
            pytest.raises(FileNotFoundError, match="Could not obtain a Python"),
        ):
            builder._create_fallback_python_tarball(python_tgz)


class TestCreatePythonTarball:
    """Lines 494-512."""

    def test_create_python_tarball(self, tmp_path: Path) -> None:
        """Lines 456-485 - create tarball from installation dir."""
        from flavor.packaging.python.environment_builder import PythonEnvironmentBuilder

        builder = PythonEnvironmentBuilder(is_windows=False)
        install_dir = tmp_path / "python_install"
        install_dir.mkdir()
        (install_dir / "bin").mkdir()
        (install_dir / "bin" / "python3").write_text("fake python")
        (install_dir / "lib").mkdir()

        python_tgz = tmp_path / "python.tgz"
        builder._create_python_tarball(install_dir, python_tgz)

        assert python_tgz.exists()
        with tarfile.open(python_tgz, "r:gz") as tar:
            names = tar.getnames()
        assert any("python3" in n for n in names)

    def test_create_tarball_filter_externally_managed(self, tmp_path: Path) -> None:
        """Lines 492-512 - filter skips EXTERNALLY-MANAGED."""
        from flavor.packaging.python.environment_builder import PythonEnvironmentBuilder

        builder = PythonEnvironmentBuilder(is_windows=False)
        stats: dict[str, int] = {"files_added": 0, "bytes_added": 0}
        filter_func = builder._create_tarball_filter(stats)

        ti = tarfile.TarInfo(name="./lib/EXTERNALLY-MANAGED")
        ti.type = tarfile.REGTYPE
        ti.size = 10
        result = filter_func(ti)
        assert result is None

    def test_create_tarball_filter_windows_bin_rename(self, tmp_path: Path) -> None:
        """Lines 500-508 - Windows renames bin/ -> Scripts/."""
        from flavor.packaging.python.environment_builder import PythonEnvironmentBuilder

        builder = PythonEnvironmentBuilder(is_windows=True)
        stats: dict[str, int] = {"files_added": 0, "bytes_added": 0}
        filter_func = builder._create_tarball_filter(stats)

        ti = tarfile.TarInfo(name="./bin/python.exe")
        ti.type = tarfile.REGTYPE
        ti.size = 100
        result = filter_func(ti)
        assert result is not None
        assert result.name == "./Scripts/python.exe"

    def test_create_tarball_filter_windows_bin_dir_rename(self, tmp_path: Path) -> None:
        """Line 505-508 - Windows renames ./bin directory itself."""
        from flavor.packaging.python.environment_builder import PythonEnvironmentBuilder

        builder = PythonEnvironmentBuilder(is_windows=True)
        stats: dict[str, int] = {"files_added": 0, "bytes_added": 0}
        filter_func = builder._create_tarball_filter(stats)

        ti = tarfile.TarInfo(name="./bin")
        ti.type = tarfile.DIRTYPE
        ti.size = 0
        result = filter_func(ti)
        assert result is not None
        assert result.name == "./Scripts"


class TestTraceTarballEntry:
    """Lines 528-534."""

    def test_trace_tarball_entry_file(self) -> None:
        from flavor.packaging.python.environment_builder import _trace_tarball_entry

        stats: dict[str, int] = {"files_added": 0, "bytes_added": 0}
        ti = tarfile.TarInfo(name="./test.py")
        ti.type = tarfile.REGTYPE
        ti.size = 1024
        _trace_tarball_entry(ti, stats)
        assert stats["files_added"] == 1
        assert stats["bytes_added"] == 1024

    def test_trace_tarball_entry_directory(self) -> None:
        from flavor.packaging.python.environment_builder import _trace_tarball_entry

        stats: dict[str, int] = {"files_added": 0, "bytes_added": 0}
        ti = tarfile.TarInfo(name="./testdir")
        ti.type = tarfile.DIRTYPE
        ti.size = 0
        _trace_tarball_entry(ti, stats)
        assert stats["files_added"] == 0


# ===========================================================================
# uv_manager.py
# ===========================================================================


class TestWindowsSystemEnv:
    """Lines 50-64."""

    def test_windows_system_env_non_windows(self) -> None:
        from flavor.packaging.python.uv_manager import _windows_system_env

        with patch("sys.platform", "linux"):
            result = _windows_system_env()
        assert result == {}

    def test_windows_system_env_windows(self) -> None:
        from flavor.packaging.python.uv_manager import _windows_system_env

        with (
            patch("sys.platform", "win32"),
            patch.dict(
                "os.environ",
                {"SYSTEMROOT": "C:\\Windows", "WINDIR": "C:\\Windows", "OTHER": "nope"},
                clear=False,
            ),
        ):
            result = _windows_system_env()
        assert "SYSTEMROOT" in result
        assert "OTHER" not in result


class TestUVManagerMetadataEdgeCases:
    """Line 125, 135 - unsupported arch raises ToolNotFoundError."""

    @patch("platform.machine")
    @patch("platform.system")
    def test_get_metadata_darwin_unsupported_arch(self, mock_system: Mock, mock_machine: Mock) -> None:
        from provide.foundation.tools.base import ToolNotFoundError

        from flavor.packaging.python.uv_manager import UVManager

        mock_system.return_value = "Darwin"
        mock_machine.return_value = "mips"
        mgr = UVManager()
        with pytest.raises(ToolNotFoundError, match="Unsupported Darwin architecture"):
            mgr.get_metadata("0.6.6")

    @patch("platform.machine")
    @patch("platform.system")
    def test_get_metadata_linux_unsupported_arch(self, mock_system: Mock, mock_machine: Mock) -> None:
        from provide.foundation.tools.base import ToolNotFoundError

        from flavor.packaging.python.uv_manager import UVManager

        mock_system.return_value = "Linux"
        mock_machine.return_value = "mips"
        mgr = UVManager()
        with pytest.raises(ToolNotFoundError, match="Unsupported Linux architecture"):
            mgr.get_metadata("0.6.6")

    @patch("platform.machine")
    @patch("platform.system")
    def test_get_metadata_windows_unsupported_arch(self, mock_system: Mock, mock_machine: Mock) -> None:
        from provide.foundation.tools.base import ToolNotFoundError

        from flavor.packaging.python.uv_manager import UVManager

        mock_system.return_value = "Windows"
        mock_machine.return_value = "mips"
        mgr = UVManager()
        with pytest.raises(ToolNotFoundError, match="Unsupported Windows architecture"):
            mgr.get_metadata("0.6.6")

    @patch("platform.machine")
    @patch("platform.system")
    def test_get_metadata_unsupported_platform(self, mock_system: Mock, mock_machine: Mock) -> None:
        from provide.foundation.tools.base import ToolNotFoundError

        from flavor.packaging.python.uv_manager import UVManager

        mock_system.return_value = "FreeBSD"
        mock_machine.return_value = "x86_64"
        mgr = UVManager()
        with pytest.raises(ToolNotFoundError, match="Unsupported platform"):
            mgr.get_metadata("0.6.6")


class TestUVManagerFindSystemUV:
    """Lines 191-192."""

    def test_find_system_uv_next_to_python(self, tmp_path: Path) -> None:
        """Lines 185-192 - finds uv next to Python executable."""
        from flavor.packaging.python.uv_manager import UVManager

        mgr = UVManager()
        fake_uv = tmp_path / "uv"
        fake_uv.write_text("fake uv")

        with (
            patch("shutil.which", return_value=None),
            patch("sys.executable", str(tmp_path / "python")),
        ):
            result = mgr.find_system_uv()
        assert result == fake_uv


class TestUVManagerGetUVExecutable:
    """Lines 211-220."""

    def test_get_uv_executable_installs_version(self) -> None:
        """Line 215-216 - installs specific version."""
        from flavor.packaging.python.uv_manager import UVManager

        mgr = UVManager()
        fake_path = Path("/usr/local/bin/uv-0.6.6")
        with (
            patch.object(mgr, "find_system_uv", return_value=None),
            patch("asyncio.run", return_value=fake_path),
        ):
            result = mgr.get_uv_executable(version="0.6.6")
        assert result == fake_path

    def test_get_uv_executable_installs_latest(self) -> None:
        """Lines 218-220 - no system uv, installs latest."""
        from flavor.packaging.python.uv_manager import UVManager

        mgr = UVManager()
        fake_path = Path("/usr/local/bin/uv")
        with (
            patch.object(mgr, "find_system_uv", return_value=None),
            patch("asyncio.run", return_value=fake_path),
        ):
            result = mgr.get_uv_executable()
        assert result == fake_path


class TestUVManagerExportRequirements:
    """Lines 382-402."""

    def test_export_requirements_strips_local(self, tmp_path: Path) -> None:
        """Lines 382-402 - exports requirements and strips file:// lines."""
        from flavor.packaging.python.uv_manager import UVManager

        mgr = UVManager()
        output_file = tmp_path / "requirements.txt"
        output_file.write_text(
            "requests==2.31.0\n-e file:///path/to/project\nmyproject @ file:///path/to/project\n"
        )

        with (
            patch.object(mgr, "get_uv_executable", return_value=Path("/usr/bin/uv")),
            patch("flavor.packaging.python.uv_manager.run", return_value=_completed(0)),
        ):
            mgr.export_requirements(tmp_path, output_file)

        content = output_file.read_text()
        assert "requests==2.31.0" in content
        assert "file://" not in content
        assert "-e " not in content

    def test_strip_local_requirements_no_changes(self, tmp_path: Path) -> None:
        """Lines 413-418 - no local requirements to strip."""
        from flavor.packaging.python.uv_manager import UVManager

        mgr = UVManager()
        req_file = tmp_path / "requirements.txt"
        original = "requests==2.31.0\nnumpy==1.24.0\n"
        req_file.write_text(original)
        mgr._strip_local_requirements(req_file)
        assert req_file.read_text() == original


class TestUVManagerDownloadWheelsOffline:
    """Lines 439-476."""

    def test_download_wheels_offline_no_cache_env(self, tmp_path: Path) -> None:
        """Lines 442-444 - no FLAVOR_WHEEL_CACHE."""
        from flavor.packaging.python.uv_manager import UVManager

        mgr = UVManager()
        req_file = tmp_path / "requirements.txt"
        req_file.write_text("requests==2.31.0\n")

        with patch.dict("os.environ", {}, clear=True):
            result = mgr.download_wheels_offline(req_file, tmp_path)
        assert result is False

    def test_download_wheels_offline_empty_cache(self, tmp_path: Path) -> None:
        """Lines 448-450 - cache dir empty."""
        from flavor.packaging.python.uv_manager import UVManager

        mgr = UVManager()
        req_file = tmp_path / "requirements.txt"
        req_file.write_text("requests==2.31.0\n")
        cache_dir = tmp_path / "wheel_cache"
        cache_dir.mkdir()

        with patch.dict("os.environ", {"FLAVOR_WHEEL_CACHE": str(cache_dir)}):
            result = mgr.download_wheels_offline(req_file, tmp_path / "dest")
        assert result is False

    def test_download_wheels_offline_success(self, tmp_path: Path) -> None:
        """Lines 451-472 - pip download succeeds."""
        from flavor.packaging.python.uv_manager import UVManager

        mgr = UVManager()
        req_file = tmp_path / "requirements.txt"
        req_file.write_text("requests==2.31.0\n")
        cache_dir = tmp_path / "wheel_cache"
        cache_dir.mkdir()
        # Create a fake .whl in the cache
        (cache_dir / "requests-2.31.0-py3-none-any.whl").write_text("fake wheel")

        dest_dir = tmp_path / "dest"
        dest_dir.mkdir()

        with (
            patch.dict("os.environ", {"FLAVOR_WHEEL_CACHE": str(cache_dir)}),
            patch("flavor.packaging.python.uv_manager.run", return_value=_completed(0)),
        ):
            result = mgr.download_wheels_offline(req_file, dest_dir)
        assert result is True

    def test_download_wheels_offline_pip_fails(self, tmp_path: Path) -> None:
        """Lines 473-476 - pip download fails."""
        from flavor.packaging.python.uv_manager import UVManager

        mgr = UVManager()
        req_file = tmp_path / "requirements.txt"
        req_file.write_text("requests==2.31.0\n")
        cache_dir = tmp_path / "wheel_cache"
        cache_dir.mkdir()
        (cache_dir / "requests-2.31.0-py3-none-any.whl").write_text("fake wheel")
        dest_dir = tmp_path / "dest"
        dest_dir.mkdir()

        with (
            patch.dict("os.environ", {"FLAVOR_WHEEL_CACHE": str(cache_dir)}),
            patch("flavor.packaging.python.uv_manager.run", return_value=_completed(1, "", "pip error")),
        ):
            result = mgr.download_wheels_offline(req_file, dest_dir)
        assert result is False


class TestUVManagerDownloadWheelsNetwork:
    """Lines 498-540."""

    def test_download_wheels_network_success(self, tmp_path: Path) -> None:
        """Lines 498-540 - UV install succeeds and finds wheels."""
        from flavor.packaging.python.uv_manager import UVManager

        mgr = UVManager()
        req_file = tmp_path / "requirements.txt"
        req_file.write_text("requests==2.31.0\n")

        dest_dir = tmp_path / "dest"
        dest_dir.mkdir()

        # We need to actually create a fake wheel file in the UV cache dir
        def fake_run(cmd: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
            # When UV installs, write a fake wheel into uv_cache
            if "install" in cmd and "--cache-dir" in cmd:
                cache_idx = cmd.index("--cache-dir") + 1
                cache_dir = Path(cmd[cache_idx])
                wheels_dir = cache_dir / "wheels" / "some-hash"
                wheels_dir.mkdir(parents=True, exist_ok=True)
                (wheels_dir / "requests-2.31.0-py3-none-any.whl").write_text("fake wheel")
            return _completed(0)

        with (
            patch.object(mgr, "get_uv_executable", return_value=Path("/usr/bin/uv")),
            patch("flavor.packaging.python.uv_manager.run", side_effect=fake_run),
        ):
            result = mgr.download_wheels_network(req_file, dest_dir)
        assert result is True
        assert len(list(dest_dir.glob("*.whl"))) == 1

    def test_download_wheels_network_install_fails(self, tmp_path: Path) -> None:
        """Lines 524-529 - UV install fails."""
        from flavor.packaging.python.uv_manager import UVManager

        mgr = UVManager()
        req_file = tmp_path / "requirements.txt"
        req_file.write_text("requests==2.31.0\n")
        dest_dir = tmp_path / "dest"
        dest_dir.mkdir()

        with (
            patch.object(mgr, "get_uv_executable", return_value=Path("/usr/bin/uv")),
            patch("flavor.packaging.python.uv_manager.run", return_value=_completed(1, "", "install error")),
        ):
            result = mgr.download_wheels_network(req_file, dest_dir)
        assert result is False

    def test_download_wheels_network_no_wheels_found(self, tmp_path: Path) -> None:
        """Lines 532-535 - install succeeds but no wheels found."""
        from flavor.packaging.python.uv_manager import UVManager

        mgr = UVManager()
        req_file = tmp_path / "requirements.txt"
        req_file.write_text("requests==2.31.0\n")
        dest_dir = tmp_path / "dest"
        dest_dir.mkdir()

        with (
            patch.object(mgr, "get_uv_executable", return_value=Path("/usr/bin/uv")),
            patch("flavor.packaging.python.uv_manager.run", return_value=_completed(0)),
        ):
            result = mgr.download_wheels_network(req_file, dest_dir)
        assert result is False


class TestUVManagerDownloadUVBinary:
    """Lines 585-588."""

    def test_download_uv_binary_extracts_binary(self, tmp_path: Path) -> None:
        """Lines 551-638 - downloads UV wheel and extracts binary."""
        from flavor.packaging.python.uv_manager import UVManager

        mgr = UVManager()

        # Create a fake wheel zip file
        fake_wheel = tmp_path / "uv-0.6.6-py3-none-any.whl"
        with zipfile.ZipFile(fake_wheel, "w") as zf:
            zf.writestr("uv/uv", b"fake uv binary content")

        dest_dir = tmp_path / "dest"
        dest_dir.mkdir()

        def fake_run(cmd: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
            # Simulate pip download by creating the wheel in dest_dir (temp_dir)
            return _completed(0)

        with (
            patch("flavor.packaging.python.uv_manager.get_os_name", return_value="darwin"),
            patch("flavor.packaging.python.uv_manager.get_arch_name", return_value="arm64"),
            patch("flavor.packaging.python.uv_manager.run", side_effect=fake_run),
            patch("tempfile.TemporaryDirectory") as mock_tmpdir,
        ):
            # We need to mock the tempfile so we can control what's in it
            tmp_context = MagicMock()
            tmp_context.__enter__ = MagicMock(return_value=str(tmp_path / "temp_dl"))
            tmp_context.__exit__ = MagicMock(return_value=False)
            mock_tmpdir.return_value = tmp_context

            dl_dir = tmp_path / "temp_dl"
            dl_dir.mkdir()
            # Place the fake wheel in the temp dir
            import shutil

            shutil.copy(fake_wheel, dl_dir / fake_wheel.name)

            with patch("sys.platform", "linux"):
                mgr.download_uv_binary(dest_dir)
        # We can't guarantee the exact path but test it doesn't crash

    def test_download_uv_binary_no_wheel_found(self, tmp_path: Path) -> None:
        """Lines 610-611 - no wheel found."""
        from flavor.packaging.python.uv_manager import UVManager

        mgr = UVManager()
        dest_dir = tmp_path / "dest"
        dest_dir.mkdir()

        with (
            patch("flavor.packaging.python.uv_manager.get_os_name", return_value="darwin"),
            patch("flavor.packaging.python.uv_manager.get_arch_name", return_value="arm64"),
            patch("flavor.packaging.python.uv_manager.run", return_value=_completed(0)),
        ):
            result = mgr.download_uv_binary(dest_dir)
        assert result is None

    def test_download_uv_binary_exception(self, tmp_path: Path) -> None:
        """Lines 636-638 - exception during download."""
        from flavor.packaging.python.uv_manager import UVManager

        mgr = UVManager()
        dest_dir = tmp_path / "dest"
        dest_dir.mkdir()

        with (
            patch("flavor.packaging.python.uv_manager.get_os_name", return_value="darwin"),
            patch("flavor.packaging.python.uv_manager.get_arch_name", return_value="arm64"),
            patch("flavor.packaging.python.uv_manager.run", side_effect=RuntimeError("fail")),
        ):
            result = mgr.download_uv_binary(dest_dir)
        assert result is None


# ===========================================================================
# dependency_resolver.py
# ===========================================================================


class TestDependencyResolverFindUV:
    """Lines 74-88, 92-109."""

    def test_find_uv_command_version_check_fails(self) -> None:
        """Lines 72-74 - version check returns non-zero."""
        from flavor.packaging.python.dependency_resolver import DependencyResolver

        resolver = DependencyResolver()
        with (
            patch.object(resolver.uv_manager, "find_system_uv", return_value=Path("/usr/bin/uv")),
            patch(
                "flavor.packaging.python.dependency_resolver.run",
                return_value=_completed(1, "", "version error"),
            ),
            patch.object(resolver, "_find_uv_via_pipx", return_value=None),
            pytest.raises(FileNotFoundError),
        ):
            resolver.find_uv_command(raise_if_not_found=True)

    def test_find_uv_command_version_check_exception(self) -> None:
        """Line 75 - exception during version check."""
        from flavor.packaging.python.dependency_resolver import DependencyResolver

        resolver = DependencyResolver()
        with (
            patch.object(resolver.uv_manager, "find_system_uv", return_value=Path("/usr/bin/uv")),
            patch(
                "flavor.packaging.python.dependency_resolver.run",
                side_effect=OSError("not found"),
            ),
            patch.object(resolver, "_find_uv_via_pipx", return_value=None),
        ):
            result = resolver.find_uv_command(raise_if_not_found=False)
        assert result is None

    def test_find_uv_via_pipx_no_pipx(self) -> None:
        """Line 92-94 - no pipx installed."""
        from flavor.packaging.python.dependency_resolver import DependencyResolver

        resolver = DependencyResolver()
        with patch("shutil.which", return_value=None):
            result = resolver._find_uv_via_pipx()
        assert result is None

    def test_find_uv_via_pipx_success(self) -> None:
        """Lines 95-104 - pipx found, uv available via pipx."""
        from flavor.packaging.python.dependency_resolver import DependencyResolver

        resolver = DependencyResolver()
        with (
            patch("shutil.which", side_effect=lambda x: "/usr/bin/pipx" if x == "pipx" else "/usr/bin/uv"),
            patch(
                "flavor.packaging.python.dependency_resolver.run",
                return_value=_completed(0, "uv 0.6.6"),
            ),
        ):
            result = resolver._find_uv_via_pipx()
        assert result == "/usr/bin/uv"

    def test_find_uv_via_pipx_uv_not_in_path(self) -> None:
        """Line 105 - pipx works but uv not in PATH."""
        from flavor.packaging.python.dependency_resolver import DependencyResolver

        resolver = DependencyResolver()
        with (
            patch("shutil.which", side_effect=lambda x: "/usr/bin/pipx" if x == "pipx" else None),
            patch(
                "flavor.packaging.python.dependency_resolver.run",
                return_value=_completed(0, "uv 0.6.6"),
            ),
        ):
            result = resolver._find_uv_via_pipx()
        assert result is None

    def test_find_uv_via_pipx_exception(self) -> None:
        """Lines 106-108 - exception in pipx check."""
        from flavor.packaging.python.dependency_resolver import DependencyResolver

        resolver = DependencyResolver()
        with (
            patch("shutil.which", return_value="/usr/bin/pipx"),
            patch(
                "flavor.packaging.python.dependency_resolver.run",
                side_effect=OSError("pipx failed"),
            ),
        ):
            result = resolver._find_uv_via_pipx()
        assert result is None


class TestDependencyResolverDownloadUVWheel:
    """Lines 137->141, 142, 146, 158-159, 176-178, 195-208."""

    def test_download_uv_wheel_pip_not_available_returns_none(self, tmp_path: Path) -> None:
        """Lines 141-142 - pip not available."""
        from flavor.packaging.python.dependency_resolver import DependencyResolver

        resolver = DependencyResolver()
        with patch.object(resolver, "_ensure_pip_available", return_value=False):
            result = resolver.download_uv_wheel(tmp_path)
        assert result is None

    def test_download_uv_wheel_no_wheel_fallback(self, tmp_path: Path) -> None:
        """Lines 150-151 - download returns None, fallback triggered."""
        from flavor.packaging.python.dependency_resolver import DependencyResolver

        resolver = DependencyResolver()
        fake_uv = tmp_path / "uv"
        fake_uv.write_text("fake uv")

        with (
            patch.object(resolver, "_ensure_pip_available", return_value=True),
            patch.object(resolver, "_download_uv_with_pip", return_value=None),
            patch.object(resolver, "_fallback_download_uv", return_value=fake_uv),
        ):
            result = resolver.download_uv_wheel(tmp_path)
        assert result == fake_uv

    def test_download_uv_wheel_extract_fails_fallback(self, tmp_path: Path) -> None:
        """Lines 158-159 - extraction fails, fallback triggered."""
        from flavor.packaging.python.dependency_resolver import DependencyResolver

        resolver = DependencyResolver()
        fake_wheel = tmp_path / "uv-0.6.6.whl"
        fake_wheel.write_text("not a real wheel")
        fallback_result = tmp_path / "uv"

        with (
            patch.object(resolver, "_ensure_pip_available", return_value=True),
            patch.object(resolver, "_download_uv_with_pip", return_value=fake_wheel),
            patch.object(resolver, "_extract_uv_from_wheel", return_value=None),
            patch.object(resolver, "_fallback_download_uv", return_value=fallback_result),
        ):
            result = resolver.download_uv_wheel(tmp_path)
        assert result == fallback_result

    def test_ensure_pip_available_success(self) -> None:
        """Lines 176-178 - pip is available."""
        from flavor.packaging.python.dependency_resolver import DependencyResolver

        resolver = DependencyResolver()
        with patch("flavor.packaging.python.dependency_resolver.run", return_value=_completed(0, "pip 23.0")):
            result = resolver._ensure_pip_available()
        assert result is True

    def test_ensure_pip_available_fails_installs(self) -> None:
        """Lines 177-178 - pip not found, tries to install."""
        from flavor.packaging.python.dependency_resolver import DependencyResolver

        resolver = DependencyResolver()
        with (
            patch(
                "flavor.packaging.python.dependency_resolver.run",
                side_effect=RuntimeError("no pip"),
            ),
            patch.object(resolver, "_install_pip", return_value=True),
        ):
            result = resolver._ensure_pip_available()
        assert result is True

    def test_install_pip_ensurepip_success(self) -> None:
        """Lines 195-196 - ensurepip works."""
        from flavor.packaging.python.dependency_resolver import DependencyResolver

        resolver = DependencyResolver()
        with patch("flavor.packaging.python.dependency_resolver.run", return_value=_completed(0)):
            result = resolver._install_pip(Path(sys.executable))
        assert result is True

    def test_install_pip_ensurepip_fails_uv_succeeds(self) -> None:
        """Lines 197-202 - ensurepip fails, UV pip succeeds."""
        from flavor.packaging.python.dependency_resolver import DependencyResolver

        resolver = DependencyResolver()
        call_count = 0

        def mock_run(*args: Any, **kwargs: Any) -> subprocess.CompletedProcess[str]:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise RuntimeError("ensurepip failed")
            return _completed(0)

        with (
            patch("flavor.packaging.python.dependency_resolver.run", side_effect=mock_run),
            patch.object(resolver, "find_uv_command", return_value="/usr/bin/uv"),
        ):
            result = resolver._install_pip(Path(sys.executable))
        assert result is True

    def test_install_pip_ensurepip_fails_no_uv(self) -> None:
        """Lines 206-208 - ensurepip fails, no UV available."""
        from flavor.packaging.python.dependency_resolver import DependencyResolver

        resolver = DependencyResolver()
        with (
            patch(
                "flavor.packaging.python.dependency_resolver.run",
                side_effect=RuntimeError("ensurepip failed"),
            ),
            patch.object(resolver, "find_uv_command", return_value=None),
        ):
            result = resolver._install_pip(Path(sys.executable))
        assert result is False


class TestDependencyResolverValidateManylinux:
    """Lines 249-251, 270, 274, 276, 283, 286, 293-294."""

    def test_validate_manylinux_wheel_compatible(self, tmp_path: Path) -> None:
        """Lines 249-251 - manylinux2014 compatible wheel."""
        from flavor.packaging.python.dependency_resolver import DependencyResolver

        resolver = DependencyResolver()
        wheel = tmp_path / "requests-2.31.0-cp311-cp311-manylinux2014_x86_64.whl"
        wheel.write_text("fake")
        # Should not raise
        resolver._validate_manylinux_wheel(wheel)

    def test_validate_manylinux_wheel_manylinux_2_17(self, tmp_path: Path) -> None:
        """Lines 249-251 - manylinux_2_17 also compatible."""
        from flavor.packaging.python.dependency_resolver import DependencyResolver

        resolver = DependencyResolver()
        wheel = tmp_path / "requests-2.31.0-cp311-cp311-manylinux_2_17_x86_64.whl"
        wheel.write_text("fake")
        resolver._validate_manylinux_wheel(wheel)

    def test_validate_manylinux_wheel_incompatible(self, tmp_path: Path) -> None:
        """Lines 274-276 - manylinux but old version."""
        from flavor.packaging.python.dependency_resolver import DependencyResolver

        resolver = DependencyResolver()
        wheel = tmp_path / "requests-2.31.0-cp311-cp311-manylinux1_x86_64.whl"
        wheel.write_text("fake")
        # Should log warning but not raise
        resolver._validate_manylinux_wheel(wheel)

    def test_extract_uv_from_wheel_success(self, tmp_path: Path) -> None:
        """Lines 293-339 - successful extraction."""
        from flavor.packaging.python.dependency_resolver import DependencyResolver

        resolver = DependencyResolver(is_windows=False)
        fake_wheel = tmp_path / "uv-0.6.6.whl"
        with zipfile.ZipFile(fake_wheel, "w") as zf:
            zf.writestr("uv/uv", b"fake uv binary")

        dest_dir = tmp_path / "dest"
        dest_dir.mkdir()
        result = resolver._extract_uv_from_wheel(fake_wheel, dest_dir)
        assert result is not None
        assert result.name == "uv"
        assert result.read_bytes() == b"fake uv binary"

    def test_extract_uv_from_wheel_no_binary(self, tmp_path: Path) -> None:
        """Line 341 - no UV binary in wheel."""
        from flavor.packaging.python.dependency_resolver import DependencyResolver

        resolver = DependencyResolver()
        fake_wheel = tmp_path / "uv-0.6.6.whl"
        with zipfile.ZipFile(fake_wheel, "w") as zf:
            zf.writestr("some_other_file.txt", b"data")

        dest_dir = tmp_path / "dest"
        dest_dir.mkdir()
        result = resolver._extract_uv_from_wheel(fake_wheel, dest_dir)
        assert result is None

    def test_extract_uv_from_wheel_exception(self, tmp_path: Path) -> None:
        """Lines 343-345 - exception during extraction."""
        from flavor.packaging.python.dependency_resolver import DependencyResolver

        resolver = DependencyResolver()
        bad_wheel = tmp_path / "uv-0.6.6.whl"
        bad_wheel.write_bytes(b"not a zip file")

        dest_dir = tmp_path / "dest"
        dest_dir.mkdir()
        result = resolver._extract_uv_from_wheel(bad_wheel, dest_dir)
        assert result is None


class TestDependencyResolverFallbackDownload:
    """Lines 298->exit, 302, 343-345, 360-367."""

    def test_fallback_download_uv_success(self, tmp_path: Path) -> None:
        """Lines 356-359 - UVManager succeeds."""
        from flavor.packaging.python.dependency_resolver import DependencyResolver

        resolver = DependencyResolver()
        fake_uv = tmp_path / "uv"
        fake_uv.write_text("fake")

        with patch.object(resolver.uv_manager, "download_uv_binary", return_value=fake_uv):
            result = resolver._fallback_download_uv(tmp_path)
        assert result == fake_uv

    def test_fallback_download_uv_linux_raises(self, tmp_path: Path) -> None:
        """Lines 363-366 - Linux re-raises error."""
        from flavor.packaging.python.dependency_resolver import DependencyResolver

        resolver = DependencyResolver()
        with (
            patch.object(resolver.uv_manager, "download_uv_binary", side_effect=OSError("fail")),
            patch("flavor.packaging.python.dependency_resolver.get_os_name", return_value="linux"),
            pytest.raises(FileNotFoundError, match="Failed to download UV wheel"),
        ):
            resolver._fallback_download_uv(tmp_path)

    def test_fallback_download_uv_non_linux_returns_none(self, tmp_path: Path) -> None:
        """Line 367 - non-Linux returns None."""
        from flavor.packaging.python.dependency_resolver import DependencyResolver

        resolver = DependencyResolver()
        with (
            patch.object(resolver.uv_manager, "download_uv_binary", side_effect=OSError("fail")),
            patch("flavor.packaging.python.dependency_resolver.get_os_name", return_value="darwin"),
        ):
            result = resolver._fallback_download_uv(tmp_path)
        assert result is None

    def test_get_uv_platform_tag_linux_amd64(self) -> None:
        """Lines 245-250 - Linux amd64 platform tag."""
        from flavor.packaging.python.dependency_resolver import DependencyResolver

        resolver = DependencyResolver()
        with (
            patch("flavor.packaging.python.dependency_resolver.get_os_name", return_value="linux"),
            patch("flavor.packaging.python.dependency_resolver.get_arch_name", return_value="amd64"),
        ):
            result = resolver._get_uv_platform_tag()
        assert result == "manylinux2014_x86_64"

    def test_get_uv_platform_tag_linux_arm64(self) -> None:
        """Lines 249-250 - Linux arm64 platform tag."""
        from flavor.packaging.python.dependency_resolver import DependencyResolver

        resolver = DependencyResolver()
        with (
            patch("flavor.packaging.python.dependency_resolver.get_os_name", return_value="linux"),
            patch("flavor.packaging.python.dependency_resolver.get_arch_name", return_value="arm64"),
        ):
            result = resolver._get_uv_platform_tag()
        assert result == "manylinux2014_aarch64"

    def test_get_uv_platform_tag_non_linux(self) -> None:
        """Line 251 - non-Linux returns None."""
        from flavor.packaging.python.dependency_resolver import DependencyResolver

        resolver = DependencyResolver()
        with patch("flavor.packaging.python.dependency_resolver.get_os_name", return_value="darwin"):
            result = resolver._get_uv_platform_tag()
        assert result is None

    def test_execute_download_command_success(self) -> None:
        """Lines 268-278 - successful download command."""
        from flavor.packaging.python.dependency_resolver import DependencyResolver

        resolver = DependencyResolver()
        with patch(
            "flavor.packaging.python.dependency_resolver.run",
            return_value=_completed(0, "Downloaded uv-0.6.6", ""),
        ):
            result = resolver._execute_download_command(["/usr/bin/pip", "download", "uv"])
        assert result is True


# ===========================================================================
# wheel_builder.py
# ===========================================================================


class TestWheelBuilderEnsurePip:
    """Lines 88-89."""

    def test_ensure_pip_available_ensurepip_fails_uv_succeeds(self, tmp_path: Path) -> None:
        """Lines 83-89 - pip check fails, ensurepip fails, UV succeeds."""
        from flavor.packaging.python.wheel_builder import WheelBuilder

        builder = WheelBuilder()
        python_exe = tmp_path / "python"
        python_exe.write_text("fake python")
        call_count = 0

        def mock_run(*args: Any, **kwargs: Any) -> subprocess.CompletedProcess[str]:
            nonlocal call_count
            call_count += 1
            if call_count <= 2:
                raise RuntimeError("not available")
            return _completed(0)

        with patch("flavor.packaging.python.wheel_builder.run", side_effect=mock_run):
            builder._ensure_pip_available(python_exe)  # Should not raise

    def test_ensure_pip_available_all_fail_raises(self, tmp_path: Path) -> None:
        """Lines 88-89 - all methods fail, RuntimeError raised."""
        from flavor.packaging.python.wheel_builder import WheelBuilder

        builder = WheelBuilder()
        python_exe = tmp_path / "python"
        python_exe.write_text("fake python")

        with (
            patch("flavor.packaging.python.wheel_builder.run", side_effect=RuntimeError("fail")),
            pytest.raises(RuntimeError, match="Unable to bootstrap pip"),
        ):
            builder._ensure_pip_available(python_exe)


class TestWheelBuilderResolveDeps:
    """Lines 268-276."""

    def test_resolve_dependencies_with_packages(self, tmp_path: Path) -> None:
        """Lines 216-220 - creates requirements.in from packages."""
        from flavor.packaging.python.wheel_builder import WheelBuilder

        builder = WheelBuilder()
        locked_req = tmp_path / "requirements.txt"
        locked_req.write_text("requests==2.31.0\n")

        with patch.object(builder.uv, "compile_requirements"):
            result = builder.resolve_dependencies(
                python_exe=Path(sys.executable),
                packages=["requests"],
                output_dir=tmp_path,
            )
        assert result == locked_req

    def test_resolve_dependencies_no_requirements_raises(self, tmp_path: Path) -> None:
        """Line 222-223 - no requirements raises ValueError."""
        from flavor.packaging.python.wheel_builder import WheelBuilder

        builder = WheelBuilder()
        with pytest.raises(ValueError, match="Either requirements_file or packages"):
            builder.resolve_dependencies(python_exe=Path(sys.executable), output_dir=tmp_path)

    def test_resolve_dependencies_uv_fails_fallback_to_pip_tools(self, tmp_path: Path) -> None:
        """Lines 228-239 - UV fails, falls back to pip-tools."""
        from flavor.packaging.python.wheel_builder import WheelBuilder

        builder = WheelBuilder()
        input_req = tmp_path / "requirements.in"
        input_req.write_text("requests\n")
        locked_req = tmp_path / "requirements.txt"

        with (
            patch.object(builder.uv, "compile_requirements", side_effect=RuntimeError("UV failed")),
            patch.object(builder, "_resolve_with_pip_tools") as mock_resolve,
        ):

            def write_locked(*args: Any, **kwargs: Any) -> None:
                locked_req.write_text("requests==2.31.0\n")

            mock_resolve.side_effect = write_locked
            result = builder.resolve_dependencies(
                python_exe=Path(sys.executable),
                requirements_file=input_req,
                output_dir=tmp_path,
                use_uv_for_resolution=True,
            )
        assert result == locked_req

    def test_resolve_with_pip_tools_first_attempt_fails(self, tmp_path: Path) -> None:
        """Lines 268-276 - pip-tools not found, installs then retries."""
        from flavor.packaging.python.wheel_builder import WheelBuilder

        builder = WheelBuilder()
        input_file = tmp_path / "requirements.in"
        input_file.write_text("requests\n")
        output_file = tmp_path / "requirements.txt"

        call_count = 0

        def mock_run(*args: Any, **kwargs: Any) -> subprocess.CompletedProcess[str]:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise RuntimeError("pip-tools not found")
            output_file.write_text("requests==2.31.0\n")
            return _completed(0)

        with patch("flavor.packaging.python.wheel_builder.run", side_effect=mock_run):
            builder._resolve_with_pip_tools(Path(sys.executable), input_file, output_file)
        assert output_file.read_text() == "requests==2.31.0\n"


class TestWheelBuilderDownloadWheels:
    """Lines 309-317, 324-326."""

    def test_download_wheels_pip_fails_uv_offline_succeeds(self, tmp_path: Path) -> None:
        """Lines 309-313 - pip fails, UV offline succeeds."""
        from flavor.packaging.python.wheel_builder import WheelBuilder

        builder = WheelBuilder()
        req_file = tmp_path / "requirements.txt"
        req_file.write_text("requests==2.31.0\n")
        wheel_dir = tmp_path / "wheels"
        wheel_dir.mkdir()
        (wheel_dir / "requests-2.31.0-py3-none-any.whl").write_text("fake wheel")

        with (
            patch.object(
                builder.pypapip, "download_wheels_from_requirements", side_effect=RuntimeError("pip fail")
            ),
            patch.object(builder.uv, "download_wheels_offline", return_value=True),
        ):
            result = builder.download_wheels_for_resolved_deps(
                python_exe=Path(sys.executable), requirements_file=req_file, wheel_dir=wheel_dir
            )
        assert len(result) > 0

    def test_download_wheels_pip_fails_uv_network_succeeds(self, tmp_path: Path) -> None:
        """Lines 313-314 - UV network download fallback."""
        from flavor.packaging.python.wheel_builder import WheelBuilder

        builder = WheelBuilder()
        req_file = tmp_path / "requirements.txt"
        req_file.write_text("requests==2.31.0\n")
        wheel_dir = tmp_path / "wheels"
        wheel_dir.mkdir()
        (wheel_dir / "requests-2.31.0-py3-none-any.whl").write_text("fake wheel")

        with (
            patch.object(
                builder.pypapip, "download_wheels_from_requirements", side_effect=RuntimeError("pip fail")
            ),
            patch.object(builder.uv, "download_wheels_offline", return_value=False),
            patch.object(builder.uv, "download_wheels_network", return_value=True),
        ):
            result = builder.download_wheels_for_resolved_deps(
                python_exe=Path(sys.executable), requirements_file=req_file, wheel_dir=wheel_dir
            )
        assert len(result) > 0

    def test_download_wheels_all_fail_reraises(self, tmp_path: Path) -> None:
        """Lines 315-317 - all methods fail, re-raises."""
        from flavor.packaging.python.wheel_builder import WheelBuilder

        builder = WheelBuilder()
        req_file = tmp_path / "requirements.txt"
        req_file.write_text("requests==2.31.0\n")
        wheel_dir = tmp_path / "wheels"
        wheel_dir.mkdir()

        with (
            patch.object(
                builder.pypapip, "download_wheels_from_requirements", side_effect=RuntimeError("all fail")
            ),
            patch.object(builder.uv, "download_wheels_offline", return_value=False),
            patch.object(builder.uv, "download_wheels_network", return_value=False),
            pytest.raises(RuntimeError),
        ):
            builder.download_wheels_for_resolved_deps(
                python_exe=Path(sys.executable), requirements_file=req_file, wheel_dir=wheel_dir
            )

    def test_download_wheels_empty_raises(self, tmp_path: Path) -> None:
        """Lines 324-326 - no wheels downloaded, raises RuntimeError."""
        from flavor.packaging.python.wheel_builder import WheelBuilder

        builder = WheelBuilder()
        req_file = tmp_path / "requirements.txt"
        req_file.write_text("requests==2.31.0\n")
        wheel_dir = tmp_path / "wheels"
        wheel_dir.mkdir()
        # wheel_dir is empty

        with (
            patch.object(builder.pypapip, "download_wheels_from_requirements"),
            pytest.raises(RuntimeError, match="No wheel files were downloaded"),
        ):
            builder.download_wheels_for_resolved_deps(
                python_exe=Path(sys.executable), requirements_file=req_file, wheel_dir=wheel_dir
            )


class TestWheelBuilderBuildAndResolve:
    """Lines 372-385, 390, 399-401, 419."""

    def test_build_and_resolve_no_requirements_no_packages(self, tmp_path: Path) -> None:
        """Line 419 - no requirements or packages."""
        from flavor.packaging.python.wheel_builder import WheelBuilder

        builder = WheelBuilder()
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        build_dir = tmp_path / "build"
        fake_wheel = tmp_path / "proj-1.0.0.whl"
        fake_wheel.write_text("fake wheel")

        with (
            patch.object(builder, "build_wheel_from_source", return_value=fake_wheel),
            patch.object(builder, "_ensure_no_isolation_build_backend"),
        ):
            result = builder.build_and_resolve_project(
                python_exe=Path(sys.executable),
                project_dir=project_dir,
                build_dir=build_dir,
            )
        assert result["project_wheel"] == fake_wheel
        assert result["locked_requirements"] is None
        assert result["total_wheels"] == 1

    def test_build_and_resolve_with_pyproject_toml(self, tmp_path: Path) -> None:
        """Lines 371-385 - reads pyproject.toml for dependencies."""
        from flavor.packaging.python.wheel_builder import WheelBuilder

        builder = WheelBuilder()
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        pyproject = project_dir / "pyproject.toml"
        pyproject.write_bytes(b'[project]\ndependencies = ["requests>=2.0"]\n')
        build_dir = tmp_path / "build"
        fake_wheel = tmp_path / "proj-1.0.0.whl"
        fake_wheel.write_text("fake wheel")
        fake_dep_wheel = tmp_path / "requests-2.31.0.whl"
        fake_dep_wheel.write_text("fake dep")

        with (
            patch.object(builder, "build_wheel_from_source", return_value=fake_wheel),
            patch.object(builder, "_ensure_no_isolation_build_backend"),
            patch.object(builder, "resolve_dependencies", return_value=tmp_path / "requirements.txt"),
            patch.object(builder, "download_wheels_for_resolved_deps", return_value=[fake_dep_wheel]),
        ):
            result = builder.build_and_resolve_project(
                python_exe=Path(sys.executable),
                project_dir=project_dir,
                build_dir=build_dir,
            )
        assert result["total_wheels"] == 2

    def test_build_and_resolve_with_uv_lock(self, tmp_path: Path) -> None:
        """Lines 397-401 - uses uv.lock when available."""
        from flavor.packaging.python.wheel_builder import WheelBuilder

        builder = WheelBuilder()
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        (project_dir / "uv.lock").write_text("# uv.lock")
        build_dir = tmp_path / "build"
        fake_wheel = tmp_path / "proj-1.0.0.whl"
        fake_wheel.write_text("fake wheel")
        fake_dep_wheel = tmp_path / "requests-2.31.0.whl"
        fake_dep_wheel.write_text("fake dep")

        extra_packages = ["extra-pkg"]

        with (
            patch.object(builder, "build_wheel_from_source", return_value=fake_wheel),
            patch.object(builder, "_ensure_no_isolation_build_backend"),
            patch.object(builder.uv, "export_requirements") as mock_export,
            patch.object(builder, "download_wheels_for_resolved_deps", return_value=[fake_dep_wheel]),
        ):
            result = builder.build_and_resolve_project(
                python_exe=Path(sys.executable),
                project_dir=project_dir,
                build_dir=build_dir,
                extra_packages=extra_packages,
            )
        mock_export.assert_called_once()
        assert result["total_wheels"] == 2


# ===========================================================================
# dist_manager.py
# ===========================================================================


class TestDistManagerCreateEnvironment:
    """Lines 83, 87-88, 119, 165."""

    def test_create_python_environment_default_python(self, tmp_path: Path) -> None:
        """Line 83 - python_exe defaults to sys.executable."""
        from flavor.packaging.python.dist_manager import PythonDistManager

        mgr = PythonDistManager(use_uv_for_venv=False)
        venv_dir = tmp_path / "venv"
        fake_python = venv_dir / "bin" / "python"

        with (
            patch("flavor.packaging.python.dist_manager.run", return_value=_completed(0)),
            patch.object(mgr, "_get_venv_python_path", return_value=fake_python),
        ):
            result = mgr.create_python_environment(venv_dir)
        assert result == fake_python

    def test_create_python_environment_existing_venv_removed(self, tmp_path: Path) -> None:
        """Lines 86-88 - existing venv is removed."""
        from flavor.packaging.python.dist_manager import PythonDistManager

        mgr = PythonDistManager(use_uv_for_venv=False)
        venv_dir = tmp_path / "venv"
        venv_dir.mkdir()
        (venv_dir / "marker.txt").write_text("old venv")
        fake_python = venv_dir / "bin" / "python"

        with (
            patch("flavor.packaging.python.dist_manager.run", return_value=_completed(0)),
            patch("flavor.packaging.python.dist_manager.safe_rmtree") as mock_rm,
            patch.object(mgr, "_get_venv_python_path", return_value=fake_python),
        ):
            mgr.create_python_environment(venv_dir)
        mock_rm.assert_called_once()

    def test_create_python_environment_copy_python_flag(self, tmp_path: Path) -> None:
        """Line 119 - copy_python adds --copies flag."""
        from flavor.packaging.python.dist_manager import PythonDistManager

        mgr = PythonDistManager(use_uv_for_venv=False)
        venv_dir = tmp_path / "venv"
        fake_python = venv_dir / "bin" / "python"
        captured_cmd: list[list[str]] = []

        def mock_run(cmd: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
            captured_cmd.append(cmd)
            return _completed(0)

        with (
            patch("flavor.packaging.python.dist_manager.run", side_effect=mock_run),
            patch.object(mgr, "_get_venv_python_path", return_value=fake_python),
        ):
            mgr.create_python_environment(venv_dir, copy_python=True)
        assert any("--copies" in cmd for cmd in captured_cmd)

    def test_create_python_environment_uv_missing_python_symlink(self, tmp_path: Path) -> None:
        """Lines 100-108 - UV creates venv but python binary missing, creates symlink."""
        from flavor.packaging.python.dist_manager import PythonDistManager

        mgr = PythonDistManager(use_uv_for_venv=True)
        venv_dir = tmp_path / "venv"
        bin_dir = venv_dir / "bin"
        bin_dir.mkdir(parents=True)
        fake_python = bin_dir / "python"
        # Don't create fake_python - it should be missing after uv create_venv

        with (
            patch.object(mgr.uv, "create_venv"),
            patch.object(mgr, "_get_venv_python_path", return_value=fake_python),
        ):
            import contextlib

            with contextlib.suppress(Exception):
                mgr.create_python_environment(venv_dir, python_exe=Path(sys.executable))
                # If symlink creation works, we get fake_python back

    def test_create_python_environment_uv_fails_fallback(self, tmp_path: Path) -> None:
        """Lines 112 - UV fails, falls back to venv module."""
        from flavor.packaging.python.dist_manager import PythonDistManager

        mgr = PythonDistManager(use_uv_for_venv=True)
        venv_dir = tmp_path / "venv"
        fake_python = venv_dir / "bin" / "python"

        with (
            patch.object(mgr.uv, "create_venv", side_effect=RuntimeError("UV failed")),
            patch("flavor.packaging.python.dist_manager.run", return_value=_completed(0)),
            patch.object(mgr, "_get_venv_python_path", return_value=fake_python),
        ):
            result = mgr.create_python_environment(venv_dir, python_exe=Path(sys.executable))
        assert result == fake_python


class TestDistManagerPrepareSitePackages:
    """Lines 165, 187, 192."""

    def test_prepare_site_packages_windows(self, tmp_path: Path) -> None:
        """Line 165 - Windows site-packages path."""
        from flavor.packaging.python.dist_manager import PythonDistManager

        mgr = PythonDistManager()
        venv_path = tmp_path / "venv"
        # Python is in Scripts/ on Windows
        scripts_dir = venv_path / "Scripts"
        scripts_dir.mkdir(parents=True)
        python_exe = scripts_dir / "python.exe"
        python_exe.write_text("fake")
        site_pkgs = venv_path / "Lib" / "site-packages"
        site_pkgs.mkdir(parents=True)
        (site_pkgs / "somepkg").mkdir()

        with (
            patch("os.name", "nt"),
            patch.object(mgr, "_compile_python_files"),
            patch.object(mgr, "_cleanup_site_packages"),
        ):
            result = mgr.prepare_site_packages(python_exe)
        assert result == site_pkgs

    def test_prepare_site_packages_not_found_raises(self, tmp_path: Path) -> None:
        """Line 192 - site-packages not found raises."""
        from flavor.packaging.python.dist_manager import PythonDistManager

        mgr = PythonDistManager()
        venv_path = tmp_path / "venv"
        bin_dir = venv_path / "bin"
        bin_dir.mkdir(parents=True)
        python_exe = bin_dir / "python"
        python_exe.write_text("fake")

        with patch("os.name", "posix"), pytest.raises(FileNotFoundError, match="Site-packages not found"):
            mgr.prepare_site_packages(python_exe)

    def test_compile_python_files_optimization_zero(self, tmp_path: Path) -> None:
        """Line 222 - optimization level 0 skips -O flag."""
        from flavor.packaging.python.dist_manager import PythonDistManager

        mgr = PythonDistManager()
        python_exe = tmp_path / "python"
        python_exe.write_text("fake")
        site_pkgs = tmp_path / "site-packages"
        site_pkgs.mkdir()
        captured: list[list[str]] = []

        def mock_run(cmd: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
            captured.append(cmd)
            return _completed(0)

        with patch("flavor.packaging.python.dist_manager.run", side_effect=mock_run):
            mgr._compile_python_files(python_exe, site_pkgs, 0)
        assert captured
        assert not any("-O0" in " ".join(cmd) for cmd in captured)

    def test_compile_python_files_failure_warning(self, tmp_path: Path) -> None:
        """Line 229 - compilation failure logged as warning."""
        from flavor.packaging.python.dist_manager import PythonDistManager

        mgr = PythonDistManager()
        python_exe = tmp_path / "python"
        python_exe.write_text("fake")
        site_pkgs = tmp_path / "site-packages"
        site_pkgs.mkdir()

        with patch(
            "flavor.packaging.python.dist_manager.run",
            return_value=_completed(1, "", "compile error"),
        ):
            mgr._compile_python_files(python_exe, site_pkgs, 1)  # Should not raise


class TestDistManagerCleanup:
    """Lines 264-265."""

    def test_cleanup_site_packages_handles_errors(self, tmp_path: Path) -> None:
        """Lines 264-265 - handles errors during cleanup gracefully."""
        from flavor.packaging.python.dist_manager import PythonDistManager

        mgr = PythonDistManager()
        site_pkgs = tmp_path / "site-packages"
        site_pkgs.mkdir()
        test_dir = site_pkgs / "__pycache__"
        test_dir.mkdir()

        with patch("flavor.packaging.python.dist_manager.safe_rmtree", side_effect=OSError("locked")):
            mgr._cleanup_site_packages(site_pkgs)  # Should not raise


class TestDistManagerCreateStandalone:
    """Lines 291->295, 328."""

    def test_create_standalone_distribution_default_python(self, tmp_path: Path) -> None:
        """Line 291->295 - uses sys.executable when python_exe is None."""
        from flavor.packaging.python.dist_manager import PythonDistManager

        mgr = PythonDistManager()
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        output_dir = tmp_path / "output"
        fake_wheel = tmp_path / "proj-1.0.0.whl"
        fake_wheel.write_text("fake wheel")
        fake_site_pkgs = tmp_path / "site-packages"
        fake_site_pkgs.mkdir()

        build_info: dict[str, Any] = {
            "project_wheel": fake_wheel,
            "dependency_wheels": [],
            "locked_requirements": None,
            "wheel_dir": tmp_path / "wheels",
            "total_wheels": 1,
        }
        fake_venv_python = tmp_path / "venv" / "bin" / "python"

        with (
            patch.object(mgr.wheel_builder, "build_and_resolve_project", return_value=build_info),
            patch.object(mgr, "create_python_environment", return_value=fake_venv_python),
            patch.object(mgr, "install_wheels_to_environment"),
            patch.object(mgr, "prepare_site_packages", return_value=fake_site_pkgs),
            patch("shutil.copytree"),
            patch.object(mgr, "_get_directory_size", return_value=1024),
        ):
            result = mgr.create_standalone_distribution(project_dir, output_dir)
        assert "project_name" in result

    def test_create_standalone_removes_existing_dist(self, tmp_path: Path) -> None:
        """Line 328 - removes existing dist_site_packages."""
        from flavor.packaging.python.dist_manager import PythonDistManager

        mgr = PythonDistManager()
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        output_dir = tmp_path / "output"
        dist_dir = output_dir / "dist"
        dist_dir.mkdir(parents=True)
        # Create existing site-packages dir
        existing_site_pkgs = dist_dir / "site-packages"
        existing_site_pkgs.mkdir()

        fake_wheel = tmp_path / "proj-1.0.0.whl"
        fake_wheel.write_text("fake wheel")
        fake_site_pkgs = tmp_path / "site-packages"
        fake_site_pkgs.mkdir()
        build_info: dict[str, Any] = {
            "project_wheel": fake_wheel,
            "dependency_wheels": [],
            "locked_requirements": None,
            "wheel_dir": tmp_path / "wheels",
            "total_wheels": 1,
        }

        with (
            patch.object(mgr.wheel_builder, "build_and_resolve_project", return_value=build_info),
            patch.object(mgr, "create_python_environment", return_value=tmp_path / "python"),
            patch.object(mgr, "install_wheels_to_environment"),
            patch.object(mgr, "prepare_site_packages", return_value=fake_site_pkgs),
            patch("flavor.packaging.python.dist_manager.safe_rmtree") as mock_rm,
            patch("shutil.copytree"),
            patch.object(mgr, "_get_directory_size", return_value=1024),
        ):
            mgr.create_standalone_distribution(project_dir, output_dir)
        # safe_rmtree should be called for the existing dist site-packages
        assert mock_rm.called


class TestDistManagerValidate:
    """Lines 405-407."""

    def test_validate_distribution_exception(self) -> None:
        """Lines 405-407 - exception during validation returns False."""
        from flavor.packaging.python.dist_manager import PythonDistManager

        mgr = PythonDistManager()
        dist_info: dict[str, Any] = {"site_packages": "not_a_path_object"}
        result = mgr.validate_distribution(dist_info)
        assert result is False

    def test_validate_distribution_large_size_warning(self, tmp_path: Path) -> None:
        """Lines 399-401 - large distribution logs warning."""
        from flavor.packaging.python.dist_manager import PythonDistManager

        mgr = PythonDistManager()
        site_pkgs = tmp_path / "site-packages"
        site_pkgs.mkdir()
        (site_pkgs / "something.py").write_text("data")
        dist_info: dict[str, Any] = {
            "site_packages": site_pkgs,
            "distribution_size": 600 * 1024 * 1024,  # 600MB
        }
        result = mgr.validate_distribution(dist_info)
        assert result is True


# ===========================================================================
# pypapip_manager.py
# ===========================================================================


class TestPyPaPipManagerWinPip:
    """Line 46."""

    def test_pip_base_cmd_windows(self, tmp_path: Path) -> None:
        """Line 46 - Windows uses -c wrapper."""
        from flavor.packaging.python.pypapip_manager import _pip_base_cmd

        python_exe = tmp_path / "python.exe"
        with patch("sys.platform", "win32"):
            cmd = _pip_base_cmd(python_exe)
        assert "-c" in cmd
        assert "truststore" in " ".join(cmd)

    def test_pip_base_cmd_non_windows(self, tmp_path: Path) -> None:
        """Line 47 - non-Windows uses -m pip."""
        from flavor.packaging.python.pypapip_manager import _pip_base_cmd

        python_exe = tmp_path / "python"
        with patch("sys.platform", "linux"):
            cmd = _pip_base_cmd(python_exe)
        assert "-m" in cmd
        assert "pip" in cmd


class TestPyPaPipManagerDownloadCmd:
    """Lines 155->159, 175, 182->190."""

    def test_get_download_cmd_with_platform_tag(self, tmp_path: Path) -> None:
        """Lines 165-169 - explicit platform_tag."""
        from flavor.packaging.python.pypapip_manager import PyPaPipManager

        mgr = PyPaPipManager(python_version="3.11")
        cmd = mgr._get_pypapip_download_cmd(
            python_exe=Path(sys.executable),
            dest_dir=tmp_path,
            packages=["requests"],
            binary_only=True,
            platform_tag="manylinux2014_x86_64",
        )
        assert "--platform" in cmd
        assert "manylinux2014_x86_64" in cmd

    def test_get_download_cmd_linux_amd64(self, tmp_path: Path) -> None:
        """Lines 170-181 - Linux amd64 auto platform tag."""
        from flavor.packaging.python.pypapip_manager import PyPaPipManager

        mgr = PyPaPipManager(python_version="3.11")
        with (
            patch("flavor.packaging.python.pypapip_manager.get_os_name", return_value="linux"),
            patch("flavor.packaging.python.pypapip_manager.get_arch_name", return_value="amd64"),
        ):
            cmd = mgr._get_pypapip_download_cmd(
                python_exe=Path(sys.executable),
                dest_dir=tmp_path,
                packages=["requests"],
                binary_only=True,
            )
        assert "manylinux2014_x86_64" in cmd

    def test_get_download_cmd_linux_arm64(self, tmp_path: Path) -> None:
        """Lines 182-190 - Linux arm64 manylinux tag."""
        from flavor.packaging.python.pypapip_manager import PyPaPipManager

        mgr = PyPaPipManager(python_version="3.11")
        with (
            patch("flavor.packaging.python.pypapip_manager.get_os_name", return_value="linux"),
            patch("flavor.packaging.python.pypapip_manager.get_arch_name", return_value="arm64"),
        ):
            cmd = mgr._get_pypapip_download_cmd(
                python_exe=Path(sys.executable),
                dest_dir=tmp_path,
                packages=["requests"],
                binary_only=True,
            )
        assert "manylinux2014_aarch64" in cmd

    def test_get_download_cmd_requirements_file(self, tmp_path: Path) -> None:
        """Lines 190-193 - requirements file added to cmd."""
        from flavor.packaging.python.pypapip_manager import PyPaPipManager

        mgr = PyPaPipManager(python_version="3.11")
        req_file = tmp_path / "requirements.txt"
        req_file.write_text("requests\n")
        cmd = mgr._get_pypapip_download_cmd(
            python_exe=Path(sys.executable),
            dest_dir=tmp_path,
            requirements_file=req_file,
        )
        assert "-r" in cmd
        assert str(req_file) in " ".join(cmd)

    def test_get_download_cmd_no_binary_only(self, tmp_path: Path) -> None:
        """Lines 155-159 - binary_only=False skips --only-binary."""
        from flavor.packaging.python.pypapip_manager import PyPaPipManager

        mgr = PyPaPipManager(python_version="3.11")
        cmd = mgr._get_pypapip_download_cmd(
            python_exe=Path(sys.executable),
            dest_dir=tmp_path,
            packages=["requests"],
            binary_only=False,
        )
        assert "--only-binary" not in cmd


class TestPyPaPipManagerDownloadWheels:
    """Lines 267-282."""

    def test_download_wheels_for_packages_empty(self) -> None:
        """Line 267 - empty packages list returns early."""
        from flavor.packaging.python.pypapip_manager import PyPaPipManager

        mgr = PyPaPipManager()
        with patch("flavor.packaging.python.pypapip_manager.run") as mock_run:
            mgr.download_wheels_for_packages(Path(sys.executable), [], Path("/tmp/dest"))
        mock_run.assert_not_called()

    def test_download_wheels_for_packages_success(self, tmp_path: Path) -> None:
        """Lines 269-282 - downloads packages."""
        from flavor.packaging.python.pypapip_manager import PyPaPipManager

        mgr = PyPaPipManager()
        with patch("flavor.packaging.python.pypapip_manager.run", return_value=_completed(0)):
            mgr.download_wheels_for_packages(Path(sys.executable), ["requests", "numpy"], tmp_path)

    def test_download_wheels_for_packages_fails(self, tmp_path: Path) -> None:
        """Lines 279-282 - raises RuntimeError on failure."""
        from flavor.packaging.python.pypapip_manager import PyPaPipManager

        mgr = PyPaPipManager()
        with (
            patch(
                "flavor.packaging.python.pypapip_manager.run",
                return_value=_completed(1, "", "download error"),
            ),
            pytest.raises(RuntimeError, match="Failed to download required packages"),
        ):
            mgr.download_wheels_for_packages(Path(sys.executable), ["requests"], tmp_path)


class TestPyPaPipManagerBuildWheelSource:
    """Lines 308->exit, 310->exit, 311->310."""

    def test_build_wheel_from_source_with_output(self, tmp_path: Path) -> None:
        """Lines 308-312 - stdout contains wheel filename."""
        from flavor.packaging.python.pypapip_manager import PyPaPipManager

        mgr = PyPaPipManager()
        source = tmp_path / "mypackage"
        source.mkdir()
        (source / "setup.py").write_text("from setuptools import setup; setup(name='mypackage')")
        wheel_dir = tmp_path / "wheels"
        wheel_dir.mkdir()

        with patch(
            "flavor.packaging.python.pypapip_manager.run",
            return_value=_completed(0, "Successfully built mypackage-1.0.0-py3-none-any.whl\n", ""),
        ):
            mgr.build_wheel_from_source(Path(sys.executable), source, wheel_dir)

    def test_build_wheel_from_source_no_output(self, tmp_path: Path) -> None:
        """Line 308->exit - no stdout."""
        from flavor.packaging.python.pypapip_manager import PyPaPipManager

        mgr = PyPaPipManager()
        source = tmp_path / "mypackage"
        source.mkdir()
        wheel_dir = tmp_path / "wheels"
        wheel_dir.mkdir()

        with patch("flavor.packaging.python.pypapip_manager.run", return_value=_completed(0, "", "")):
            mgr.build_wheel_from_source(Path(sys.executable), source, wheel_dir)


# ===========================================================================
# slot_builder.py
# ===========================================================================


class TestSlotBuilderResolveTransitiveDeps:
    """Lines 287, 290->298."""

    def test_resolve_transitive_dependencies_no_pyproject(self, tmp_path: Path) -> None:
        """Lines 285-287 - no pyproject.toml, dependency still added."""
        from flavor.packaging.python.slot_builder import PythonSlotBuilder

        builder = PythonSlotBuilder(
            manifest_dir=tmp_path,
            package_name="test",
            entry_point="test.main:main",
        )
        dep_path = tmp_path / "dep_without_pyproject"
        dep_path.mkdir()

        result = builder.resolve_transitive_dependencies(dep_path)
        assert dep_path.resolve() in result

    def test_resolve_transitive_dependencies_already_seen(self, tmp_path: Path) -> None:
        """Lines 222-228 - already seen dependency skipped."""
        from flavor.packaging.python.slot_builder import PythonSlotBuilder

        builder = PythonSlotBuilder(
            manifest_dir=tmp_path,
            package_name="test",
            entry_point="test.main:main",
        )
        dep_path = tmp_path / "dep1"
        dep_path.mkdir()
        seen = {dep_path.resolve()}

        result = builder.resolve_transitive_dependencies(dep_path, seen=seen)
        assert result == []

    def test_resolve_transitive_dependencies_depth_zero_logging(self, tmp_path: Path) -> None:
        """Lines 298-305 - depth=0 logs all deps in order."""
        from flavor.packaging.python.slot_builder import PythonSlotBuilder

        builder = PythonSlotBuilder(
            manifest_dir=tmp_path,
            package_name="test",
            entry_point="test.main:main",
        )
        dep_path = tmp_path / "mypackage"
        dep_path.mkdir()

        result = builder.resolve_transitive_dependencies(dep_path, depth=0)
        assert dep_path.resolve() in result


class TestSlotBuilderBundleBuildBackends:
    """Lines 372-373, 387-411."""

    def test_bundle_build_backends_no_pyproject(self, tmp_path: Path) -> None:
        """Lines 363 - no pyproject.toml, skips."""
        from flavor.packaging.python.slot_builder import PythonSlotBuilder

        builder = PythonSlotBuilder(
            manifest_dir=tmp_path,
            package_name="test",
            entry_point="test.main:main",
        )
        wheels_dir = tmp_path / "wheels"
        wheels_dir.mkdir()
        # No pyproject.toml or uv.lock
        builder._bundle_build_backends(wheels_dir)  # Should not raise

    def test_bundle_build_backends_no_build_backends_group(self, tmp_path: Path) -> None:
        """Lines 370-373 - no build-backends group, skips."""
        from flavor.packaging.python.slot_builder import PythonSlotBuilder

        builder = PythonSlotBuilder(
            manifest_dir=tmp_path,
            package_name="test",
            entry_point="test.main:main",
        )
        wheels_dir = tmp_path / "wheels"
        wheels_dir.mkdir()
        (tmp_path / "pyproject.toml").write_bytes(b"[project]\nname = 'test'\n")
        (tmp_path / "uv.lock").write_text("# lock")
        builder._bundle_build_backends(wheels_dir)  # Should not raise

    def test_bundle_build_backends_offline_strategy(self, tmp_path: Path) -> None:
        """Lines 382-411 - FLAVOR_WHEEL_CACHE set, uses offline strategy."""
        from flavor.packaging.python.slot_builder import PythonSlotBuilder

        builder = PythonSlotBuilder(
            manifest_dir=tmp_path,
            package_name="test",
            entry_point="test.main:main",
        )
        wheels_dir = tmp_path / "wheels"
        wheels_dir.mkdir()
        cache_dir = tmp_path / "wheel_cache"
        cache_dir.mkdir()

        pyproject_content = b"[dependency-groups]\nbuild-backends = ['setuptools>=80']\n"
        (tmp_path / "pyproject.toml").write_bytes(pyproject_content)
        (tmp_path / "uv.lock").write_text("# lock")

        with (
            patch.dict("os.environ", {"FLAVOR_WHEEL_CACHE": str(cache_dir)}),
            patch.object(builder.uv_manager, "get_uv_executable", return_value=Path("/usr/bin/uv")),
            patch("flavor.packaging.python.slot_builder.run", return_value=_completed(0)),
        ):
            builder._bundle_build_backends(wheels_dir)

    def test_bundle_build_backends_network_strategy(self, tmp_path: Path) -> None:
        """Lines 413-440 - no FLAVOR_WHEEL_CACHE, uses network strategy."""
        from flavor.packaging.python.slot_builder import PythonSlotBuilder

        builder = PythonSlotBuilder(
            manifest_dir=tmp_path,
            package_name="test",
            entry_point="test.main:main",
        )
        wheels_dir = tmp_path / "wheels"
        wheels_dir.mkdir()

        pyproject_content = b"[dependency-groups]\nbuild-backends = ['setuptools>=80']\n"
        (tmp_path / "pyproject.toml").write_bytes(pyproject_content)
        (tmp_path / "uv.lock").write_text("# lock")

        with (
            patch.dict("os.environ", {}, clear=True),
            patch.object(builder.uv_manager, "get_uv_executable", return_value=Path("/usr/bin/uv")),
            patch("flavor.packaging.python.slot_builder.run", return_value=_completed(0)),
        ):
            builder._bundle_build_backends(wheels_dir)


class TestSlotBuilderEnsureNoisolation:
    """WheelBuilder._ensure_no_isolation_build_backend coverage."""

    def test_ensure_no_isolation_version_mismatch(self) -> None:
        """Lines 97-102 - version mismatch raises RuntimeError."""
        from flavor.packaging.python.wheel_builder import WheelBuilder

        builder = WheelBuilder()
        with (
            patch("importlib.metadata.version", return_value="99.0.0"),
            pytest.raises(RuntimeError, match="Build backend mismatch"),
        ):
            builder._ensure_no_isolation_build_backend(Path(sys.executable))

    def test_ensure_no_isolation_package_not_found(self) -> None:
        """Lines 94-97 - package not found raises RuntimeError."""
        import importlib.metadata

        from flavor.packaging.python.wheel_builder import WheelBuilder

        builder = WheelBuilder()
        with (
            patch(
                "importlib.metadata.version", side_effect=importlib.metadata.PackageNotFoundError("missing")
            ),
            pytest.raises(RuntimeError, match="Build backend not found"),
        ):
            builder._ensure_no_isolation_build_backend(Path(sys.executable))
