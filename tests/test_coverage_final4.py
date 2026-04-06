#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
"""Tests to close specific coverage gaps identified in coverage reports.

Covers:
- dependency_resolver.py: trace/debug branches and uncommon code paths
- helpers/manager.py: list_helpers() iteration branches and find_helper() no-match
- environment_builder.py: trace logging and loop exhaustion branches
- executor.py: is_debug_enabled branch in prepare_environment
- operations.py: single-op branch
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

from provide.foundation import logger as pf_logger
import pytest

# ===========================================================================
# 1. dependency_resolver.py
# ===========================================================================


class TestDependencyResolverTraceBranches:
    """Cover trace/debug/error branches in dependency_resolver.py."""

    @pytest.mark.unit
    def test_find_uv_via_pipx_exception_with_trace_enabled(self) -> None:
        """Line 108: trace log when is_trace_enabled() is True AND pipx raises exception."""
        from flavor.packaging.python.dependency_resolver import DependencyResolver

        resolver = DependencyResolver(is_windows=False)

        with (
            patch("flavor.packaging.python.dependency_resolver.shutil.which", return_value="/usr/bin/pipx"),
            patch(
                "flavor.packaging.python.dependency_resolver.run",
                side_effect=Exception("pipx connection refused"),
            ),
            patch.object(pf_logger, "is_trace_enabled", return_value=True),
        ):
            result = resolver._find_uv_via_pipx()

        assert result is None

    @pytest.mark.unit
    def test_download_uv_wheel_debug_disabled_pip_unavailable(self, tmp_path: Path) -> None:
        """Lines 137->141: is_debug_enabled() False, then _ensure_pip_available() returns False."""
        from flavor.packaging.python.dependency_resolver import DependencyResolver

        resolver = DependencyResolver(is_windows=False)

        with (
            patch.object(pf_logger, "is_debug_enabled", return_value=False),
            patch.object(resolver, "_ensure_pip_available", return_value=False),
        ):
            result = resolver.download_uv_wheel(tmp_path)

        assert result is None

    @pytest.mark.unit
    def test_download_uv_wheel_trace_enabled_temp_dir_log(self, tmp_path: Path) -> None:
        """Line 146: trace log for temp directory creation when is_trace_enabled() is True."""
        from flavor.packaging.python.dependency_resolver import DependencyResolver

        resolver = DependencyResolver(is_windows=False)

        with (
            patch.object(pf_logger, "is_debug_enabled", return_value=False),
            patch.object(pf_logger, "is_trace_enabled", return_value=True),
            patch.object(resolver, "_ensure_pip_available", return_value=True),
            patch.object(resolver, "_download_uv_with_pip", return_value=None),
            patch.object(resolver, "_fallback_download_uv", return_value=None),
        ):
            result = resolver.download_uv_wheel(tmp_path)

        assert result is None

    @pytest.mark.unit
    def test_install_pip_uv_pip_raises_exception(self) -> None:
        """Lines 204-205: run(uv_pip_cmd) raises exception — UV pip install fails."""
        from flavor.packaging.python.dependency_resolver import DependencyResolver

        resolver = DependencyResolver(is_windows=False)

        with (
            patch(
                "flavor.packaging.python.dependency_resolver.run",
                side_effect=[
                    Exception("ensurepip failed"),  # first call: ensurepip
                    Exception("uv pip failed"),  # second call: uv pip install
                ],
            ),
            patch.object(resolver, "find_uv_command", return_value="/usr/bin/uv"),
        ):
            result = resolver._install_pip(Path("/usr/bin/python3"))

        assert result is False

    @pytest.mark.unit
    def test_get_uv_platform_tag_linux_unknown_arch(self) -> None:
        """Line 249->251: Linux OS but arch is neither 'amd64' nor 'arm64' returns None."""
        from flavor.packaging.python.dependency_resolver import DependencyResolver

        resolver = DependencyResolver(is_windows=False)

        with (
            patch("flavor.packaging.python.dependency_resolver.get_os_name", return_value="linux"),
            patch("flavor.packaging.python.dependency_resolver.get_arch_name", return_value="x86"),
        ):
            result = resolver._get_uv_platform_tag()

        assert result is None

    @pytest.mark.unit
    def test_execute_download_command_trace_logging(self) -> None:
        """Lines 270, 274, 276: trace logging in _execute_download_command when trace enabled."""
        from flavor.packaging.python.dependency_resolver import DependencyResolver

        resolver = DependencyResolver(is_windows=False)

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "Download complete"
        mock_result.stderr = "some stderr output"

        with (
            patch.object(pf_logger, "is_trace_enabled", return_value=True),
            patch(
                "flavor.packaging.python.dependency_resolver.run",
                return_value=mock_result,
            ),
        ):
            result = resolver._execute_download_command(["pip", "download", "uv"])

        assert result is True

    @pytest.mark.unit
    def test_find_downloaded_uv_wheel_trace_logging(self, tmp_path: Path) -> None:
        """Lines 283, 286: trace logging in _find_downloaded_uv_wheel when trace enabled."""
        from flavor.packaging.python.dependency_resolver import DependencyResolver

        resolver = DependencyResolver(is_windows=False)
        # No .whl files — both trace log lines fire and we get None
        (tmp_path / "something.txt").write_text("not a wheel")

        with patch.object(pf_logger, "is_trace_enabled", return_value=True):
            result = resolver._find_downloaded_uv_wheel(str(tmp_path))

        assert result is None

    @pytest.mark.unit
    def test_validate_manylinux_wheel_no_manylinux_in_name(self, tmp_path: Path) -> None:
        """Line 298->exit: _validate_manylinux_wheel returns early when 'manylinux' not in name."""
        from flavor.packaging.python.dependency_resolver import DependencyResolver

        resolver = DependencyResolver(is_windows=False)
        # Wheel name does NOT contain "manylinux" — function should return without logging
        wheel_path = tmp_path / "uv-1.0.0-cp311-cp311-win_amd64.whl"
        wheel_path.write_bytes(b"fake wheel")

        # Should not raise and should return silently
        resolver._validate_manylinux_wheel(wheel_path)


# ===========================================================================
# 2. helpers/manager.py
# ===========================================================================


class TestHelperManagerListHelpersBranches:
    """Cover list_helpers() branch gaps in helpers/manager.py."""

    @pytest.mark.unit
    def test_list_helpers_bin_does_not_exist(self, tmp_path: Path) -> None:
        """Branch 77->91: helpers_bin.exists() is False — main loop is skipped entirely."""
        from flavor.helpers.manager import HelperManager

        with patch.object(HelperManager, "__init__", lambda s: None):
            mgr = HelperManager.__new__(HelperManager)
            # Point to a path that does not exist — exists() returns False
            mgr.helpers_bin = tmp_path / "nonexistent_bin"
            mgr.current_platform = "linux_amd64"
            mgr._binary_loader = MagicMock()

            fake_embedded = MagicMock()
            fake_embedded.exists.return_value = False

            with patch("flavor.helpers.manager.Path", return_value=fake_embedded):
                result = mgr.list_helpers()

        assert result == {"launchers": [], "builders": []}

    @pytest.mark.unit
    def test_list_helpers_skips_subdirectory_in_helpers_bin(self, tmp_path: Path) -> None:
        """Branch 79->78: iterdir() yields a directory (is_file() False) — skipped."""
        from flavor.helpers.manager import HelperManager

        with patch.object(HelperManager, "__init__", lambda s: None):
            mgr = HelperManager.__new__(HelperManager)
            mgr.helpers_bin = tmp_path / "bin"
            mgr.helpers_bin.mkdir()
            mgr.current_platform = "linux_amd64"
            mgr._binary_loader = MagicMock()

            # Create a subdirectory, not a file
            (mgr.helpers_bin / "subdir").mkdir()

            fake_embedded = MagicMock()
            fake_embedded.exists.return_value = False

            with patch("flavor.helpers.manager.Path") as MockPath:
                MockPath.return_value = fake_embedded

                result = mgr.list_helpers()

        assert result == {"launchers": [], "builders": []}

    @pytest.mark.unit
    def test_list_helpers_get_helper_info_returns_none(self, tmp_path: Path) -> None:
        """Branch 84->78: _get_helper_info() returns None — entry skipped."""
        from flavor.helpers.manager import HelperManager

        with patch.object(HelperManager, "__init__", lambda s: None):
            mgr = HelperManager.__new__(HelperManager)
            mgr.helpers_bin = tmp_path / "bin"
            mgr.helpers_bin.mkdir()
            mgr.current_platform = "linux_amd64"
            mgr._binary_loader = MagicMock()

            (mgr.helpers_bin / "flavor-go-launcher-linux_amd64").write_bytes(b"x")

            fake_embedded = MagicMock()
            fake_embedded.exists.return_value = False

            with (
                patch.object(mgr, "_get_helper_info", return_value=None),
                patch("flavor.helpers.manager.Path") as MockPath,
            ):
                MockPath.return_value = fake_embedded
                result = mgr.list_helpers()

        assert result == {"launchers": [], "builders": []}

    @pytest.mark.unit
    def test_list_helpers_unknown_type_skipped(self, tmp_path: Path) -> None:
        """Branch 87->78: _get_helper_info() returns info with unknown type — skipped."""
        from flavor.helpers.manager import HelperManager

        with patch.object(HelperManager, "__init__", lambda s: None):
            mgr = HelperManager.__new__(HelperManager)
            mgr.helpers_bin = tmp_path / "bin"
            mgr.helpers_bin.mkdir()
            mgr.current_platform = "linux_amd64"
            mgr._binary_loader = MagicMock()

            (mgr.helpers_bin / "flavor-go-launcher-linux_amd64").write_bytes(b"x")

            unknown_info = MagicMock()
            unknown_info.type = "unknown_type"
            unknown_info.name = "flavor-go-launcher-linux_amd64"

            fake_embedded = MagicMock()
            fake_embedded.exists.return_value = False

            with (
                patch.object(mgr, "_get_helper_info", return_value=unknown_info),
                patch("flavor.helpers.manager.Path") as MockPath,
            ):
                MockPath.return_value = fake_embedded
                result = mgr.list_helpers()

        # Unknown type is neither launcher nor builder — both lists remain empty
        assert result == {"launchers": [], "builders": []}

    @pytest.mark.unit
    def test_list_helpers_embedded_bin_subdirectory_skipped(self, tmp_path: Path) -> None:
        """Branch 94->93: embedded_bin has a subdirectory (is_file() False) — skipped."""
        from flavor.helpers.manager import HelperManager

        with patch.object(HelperManager, "__init__", lambda s: None):
            mgr = HelperManager.__new__(HelperManager)
            mgr.helpers_bin = tmp_path / "bin"
            mgr.helpers_bin.mkdir()
            mgr.current_platform = "linux_amd64"
            mgr._binary_loader = MagicMock()

            embedded_bin = tmp_path / "embedded"
            embedded_bin.mkdir()
            (embedded_bin / "subdir").mkdir()  # directory, not file

            with patch("flavor.helpers.manager.Path") as MockPath:
                mock_embedded = MagicMock()
                mock_embedded.exists.return_value = True
                subdir = MagicMock()
                subdir.is_file.return_value = False
                mock_embedded.iterdir.return_value = [subdir]
                # Path(__file__).parent / "bin" → Path(x) → mock_path_obj
                #   → .parent → mock_path_obj.parent
                #   → / "bin" → mock_embedded
                MockPath.return_value.parent.__truediv__.return_value = mock_embedded

                result = mgr.list_helpers()

        assert result == {"launchers": [], "builders": []}

    @pytest.mark.unit
    def test_list_helpers_embedded_bin_get_helper_info_none(self, tmp_path: Path) -> None:
        """Branch 99->93: embedded_bin has file but _get_helper_info() returns None."""
        from flavor.helpers.manager import HelperManager

        with patch.object(HelperManager, "__init__", lambda s: None):
            mgr = HelperManager.__new__(HelperManager)
            mgr.helpers_bin = tmp_path / "bin"
            mgr.helpers_bin.mkdir()
            mgr.current_platform = "linux_amd64"
            mgr._binary_loader = MagicMock()

            with patch("flavor.helpers.manager.Path") as MockPath:
                mock_embedded = MagicMock()
                mock_embedded.exists.return_value = True
                embedded_file = MagicMock()
                embedded_file.is_file.return_value = True
                mock_embedded.iterdir.return_value = [embedded_file]
                MockPath.return_value.parent.__truediv__.return_value = mock_embedded

                with patch.object(mgr, "_get_helper_info", return_value=None):
                    result = mgr.list_helpers()

        assert result == {"launchers": [], "builders": []}

    @pytest.mark.unit
    def test_list_helpers_embedded_bin_duplicate_skipped(self, tmp_path: Path) -> None:
        """Branch 102->93: embedded_bin file already in existing_names — not added again."""
        from flavor.helpers.manager import HelperManager

        with patch.object(HelperManager, "__init__", lambda s: None):
            mgr = HelperManager.__new__(HelperManager)
            mgr.helpers_bin = tmp_path / "bin"
            mgr.helpers_bin.mkdir()
            mgr.current_platform = "linux_amd64"
            mgr._binary_loader = MagicMock()

            helper_name = "flavor-go-launcher-linux_amd64"
            (mgr.helpers_bin / helper_name).write_bytes(b"x")

            launcher_info = MagicMock()
            launcher_info.type = "launcher"
            launcher_info.name = helper_name

            # Patch _get_helper_info to always return the same launcher name
            with (
                patch.object(mgr, "_get_helper_info", return_value=launcher_info),
                patch("flavor.helpers.manager.Path") as MockPath,
            ):
                mock_embedded = MagicMock()
                mock_embedded.exists.return_value = True
                embedded_file = MagicMock()
                embedded_file.is_file.return_value = True
                embedded_file.name = helper_name
                mock_embedded.iterdir.return_value = [embedded_file]
                MockPath.return_value.parent.__truediv__.return_value = mock_embedded

                result = mgr.list_helpers()

        # The helper should appear exactly once (not duplicated)
        assert len(result["launchers"]) == 1

    @pytest.mark.unit
    def test_list_helpers_embedded_bin_unknown_type_skipped(self, tmp_path: Path) -> None:
        """Branch 105->93: embedded file has info but unknown type — not appended."""
        from flavor.helpers.manager import HelperManager

        with patch.object(HelperManager, "__init__", lambda s: None):
            mgr = HelperManager.__new__(HelperManager)
            mgr.helpers_bin = tmp_path / "bin"
            mgr.helpers_bin.mkdir()
            mgr.current_platform = "linux_amd64"
            mgr._binary_loader = MagicMock()

            embedded_name = "flavor-go-extractor-linux_amd64"
            unknown_info = MagicMock()
            unknown_info.type = "extractor"
            unknown_info.name = embedded_name

            with (
                patch.object(mgr, "_get_helper_info", return_value=unknown_info),
                patch("flavor.helpers.manager.Path") as MockPath,
            ):
                mock_embedded = MagicMock()
                mock_embedded.exists.return_value = True
                embedded_file = MagicMock()
                embedded_file.is_file.return_value = True
                embedded_file.name = embedded_name
                mock_embedded.iterdir.return_value = [embedded_file]
                MockPath.return_value.parent.__truediv__.return_value = mock_embedded

                result = mgr.list_helpers()

        assert result == {"launchers": [], "builders": []}

    @pytest.mark.unit
    def test_get_helper_info_no_partial_match(self, tmp_path: Path) -> None:
        """Branch 243->242: find_helper() iterates helpers but name not in any helper.name."""
        from flavor.helpers.manager import HelperManager

        with patch.object(HelperManager, "__init__", lambda s: None):
            mgr = HelperManager.__new__(HelperManager)
            mgr.helpers_bin = tmp_path / "nonexistent_bin"
            mgr.current_platform = "linux_amd64"
            mgr._binary_loader = MagicMock()

            existing_helper = MagicMock()
            existing_helper.name = "flavor-go-launcher-linux_amd64"

            with patch.object(
                mgr,
                "list_helpers",
                return_value={"launchers": [existing_helper], "builders": []},
            ):
                result = mgr.get_helper_info("totally_unknown_name_xyz")

        assert result is None


# ===========================================================================
# 3. environment_builder.py — trace and loop branches
# ===========================================================================


class TestEnvironmentBuilderTraceBranches:
    """Cover trace logging and loop exhaustion branches in environment_builder.py."""

    @pytest.mark.unit
    def test_find_python_in_all_dirs_loop_exhausts(self, tmp_path: Path) -> None:
        """Branches 220->218 and 218->224: loop continues when _find_python_binary returns falsy
        for all candidates, then falls through to line 224 (fallback)."""
        from flavor.packaging.python.environment_builder import PythonEnvironmentBuilder

        with patch.object(PythonEnvironmentBuilder, "__init__", lambda s: None):
            builder = PythonEnvironmentBuilder.__new__(PythonEnvironmentBuilder)
            builder.is_windows = False

            # Create an install dir with non-cpython subdirs so all_dirs is non-empty
            install_path = tmp_path / "install"
            install_path.mkdir()
            (install_path / "pypy-3.10").mkdir()
            (install_path / "pypy-3.11").mkdir()

            # _find_python_binary returns None for every candidate (220->218 loops)
            # after loop exhausts, falls to line 224 (_fallback_find_python)
            with (
                patch.object(builder, "_find_python_binary", return_value=None),
                patch.object(builder, "_fallback_find_python", return_value=None),
            ):
                result = builder._find_python_installation(str(install_path), "/usr/bin/uv")

        assert result is None

    @pytest.mark.unit
    def test_validate_python_installation_not_system_symlink(self, tmp_path: Path) -> None:
        """Branch 360->367: is_system_path is False — no 'system symlink' error logged."""
        from flavor.packaging.python.environment_builder import PythonEnvironmentBuilder

        with patch.object(PythonEnvironmentBuilder, "__init__", lambda s: None):
            builder = PythonEnvironmentBuilder.__new__(PythonEnvironmentBuilder)
            builder.is_windows = False

            bin_dir = tmp_path / "cpython-3.11" / "bin"
            bin_dir.mkdir(parents=True)
            python_bin = bin_dir / "python3"
            python_bin.write_bytes(b"fake python")

            # Make it a symlink pointing to a non-system path
            symlink_path = tmp_path / "python3_link"
            symlink_path.symlink_to(python_bin)

            with patch.object(builder, "_log_installation_contents"):
                result = builder._validate_python_installation(symlink_path)

        # Should return the install dir (parent of bin/)
        assert result is not None

    @pytest.mark.unit
    def test_tarball_filter_externally_managed_with_trace(self, tmp_path: Path) -> None:
        """Line 559: trace log when EXTERNALLY-MANAGED file is skipped with trace enabled."""
        import tarfile

        from flavor.packaging.python.environment_builder import PythonEnvironmentBuilder

        with patch.object(PythonEnvironmentBuilder, "__init__", lambda s: None):
            builder = PythonEnvironmentBuilder.__new__(PythonEnvironmentBuilder)
            builder.is_windows = False

            stats: dict[str, int] = {"files_added": 0, "bytes_added": 0, "files_skipped": 0}
            filter_func = builder._create_tarball_filter(stats)

            tarinfo = tarfile.TarInfo(name="./lib/python3.11/EXTERNALLY-MANAGED")
            tarinfo.size = 0

            with patch.object(pf_logger, "is_trace_enabled", return_value=True):
                result = filter_func(tarinfo)

        assert result is None

    @pytest.mark.unit
    def test_tarball_filter_windows_bin_rename_with_trace(self, tmp_path: Path) -> None:
        """Lines 567, 571: trace logs when Windows bin/ renaming occurs with trace enabled."""
        import tarfile

        from flavor.packaging.python.environment_builder import PythonEnvironmentBuilder

        with patch.object(PythonEnvironmentBuilder, "__init__", lambda s: None):
            builder = PythonEnvironmentBuilder.__new__(PythonEnvironmentBuilder)
            builder.is_windows = True

            stats: dict[str, int] = {"files_added": 0, "bytes_added": 0, "files_skipped": 0}
            filter_func = builder._create_tarball_filter(stats)

            with patch.object(pf_logger, "is_trace_enabled", return_value=True):
                # Test line 567: ./bin/python -> ./Scripts/python
                tarinfo1 = tarfile.TarInfo(name="./bin/python")
                tarinfo1.size = 100
                tarinfo1.type = tarfile.REGTYPE
                with patch(
                    "flavor.packaging.python.environment_builder.deterministic_filter",
                    return_value=tarinfo1,
                ):
                    filter_func(tarinfo1)
                assert tarinfo1.name == "./Scripts/python"

                # Test line 571: ./bin -> ./Scripts
                tarinfo2 = tarfile.TarInfo(name="./bin")
                tarinfo2.size = 0
                tarinfo2.type = tarfile.DIRTYPE
                with patch(
                    "flavor.packaging.python.environment_builder.deterministic_filter",
                    return_value=tarinfo2,
                ):
                    filter_func(tarinfo2)
                assert tarinfo2.name == "./Scripts"


# ===========================================================================
# 4. executor.py — is_debug_enabled branch in prepare_environment
# ===========================================================================


class TestBundleExecutorDebugBranch:
    """Cover is_debug_enabled branch in executor.py prepare_environment."""

    @pytest.mark.unit
    def test_prepare_environment_debug_enabled_logs(self, tmp_path: Path) -> None:
        """Branch 215->217: is_debug_enabled() returns True — debug log is emitted."""
        from flavor.psp.format_2025.executor import BundleExecutor

        metadata: dict = {
            "package": {"name": "mypkg", "version": "1.0.0"},
            "execution": {},
        }
        executor = BundleExecutor(metadata=metadata, workenv_dir=tmp_path)

        with (
            patch.object(pf_logger, "is_debug_enabled", return_value=True),
            patch(
                "flavor.psp.format_2025.executor.apply_environment_layers",
                return_value={"KEY": "value"},
            ),
        ):
            env = executor.prepare_environment()

        assert "KEY" in env


# ===========================================================================
# 5. operations.py — single operation branch and raise path
# ===========================================================================


class TestOperationsSingleOpBranch:
    """Cover single-op and raise branches in format_2025/operations.py."""

    @pytest.mark.unit
    def test_string_to_operations_single_gzip(self) -> None:
        """Line 231->232: op_string is a single known op (e.g. 'gzip') — returns packed ops."""
        from flavor.psp.format_2025.operations import string_to_operations

        result = string_to_operations("gzip")
        assert result != 0

    @pytest.mark.unit
    def test_string_to_operations_single_tar(self) -> None:
        """Line 231->232: op_string is 'tar' — returns packed ops for tar only."""
        from flavor.psp.format_2025.operations import string_to_operations

        result = string_to_operations("tar")
        assert result != 0

    @pytest.mark.unit
    def test_string_to_operations_unknown_raises(self) -> None:
        """Line 234: unknown single op raises ValueError."""
        from flavor.psp.format_2025.operations import string_to_operations

        with pytest.raises(ValueError, match="Unknown v0 operation string"):
            string_to_operations("lzma")

    @pytest.mark.unit
    def test_string_to_operations_pipe_with_unknown_raises(self) -> None:
        """Line 218: pipe-separated op with unknown part raises ValueError."""
        from flavor.psp.format_2025.operations import string_to_operations

        with pytest.raises(ValueError, match="Unsupported v0 operation"):
            string_to_operations("tar|lzma")


# 🌶️📦🔚
