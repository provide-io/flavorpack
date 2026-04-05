#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""Targeted coverage gap tests — final3 batch."""

from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest


class TestBinaryLoaderBranches:
    def _make_loader(self, tmp_path: Path) -> Any:
        """Create a BinaryLoader with a mock manager."""
        from flavor.helpers.binary_loader import BinaryLoader

        mgr = MagicMock()
        mgr.helpers_bin = tmp_path / "bin"
        mgr.helpers_bin.mkdir(parents=True, exist_ok=True)
        mgr.go_src_dir = tmp_path / "go-src"
        mgr.rust_src_dir = tmp_path / "rust-src"
        loader = BinaryLoader(mgr)
        return loader

    @pytest.mark.unit
    def test_go_build_failure_with_stderr(self, tmp_path: Path) -> None:
        """Branch 132->102: Go build fails and stderr is printed."""
        loader = self._make_loader(tmp_path)
        loader.manager.go_src_dir.mkdir(parents=True)

        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stderr = "compilation error"

        with patch("flavor.helpers.binary_loader.run", return_value=mock_result):
            result = loader._build_go_helpers(force=True)
        assert result == []

    @pytest.mark.unit
    def test_rust_build_failure_with_stderr(self, tmp_path: Path) -> None:
        """Branch 185->149: Rust build fails and stderr is printed."""
        loader = self._make_loader(tmp_path)
        loader.manager.rust_src_dir.mkdir(parents=True)

        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stderr = "linking failed"

        with patch("flavor.helpers.binary_loader.run", return_value=mock_result):
            result = loader._build_rust_helpers(force=True)
        assert result == []

    @pytest.mark.unit
    def test_clean_helpers_rust_language(self, tmp_path: Path) -> None:
        """Branch 209->212: clean_helpers with language='rust'."""
        loader = self._make_loader(tmp_path)
        # Create a fake rust binary
        fake_bin = loader.manager.helpers_bin / "flavor-rs-launcher-darwin_arm64"
        fake_bin.write_text("fake")
        removed = loader.clean_helpers(language="rust")
        assert len(removed) == 1
        assert "flavor-rs" in removed[0].name

    @pytest.mark.unit
    def test_clean_helpers_skips_directories(self, tmp_path: Path) -> None:
        """Branch 214->213: glob match is a directory, not a file."""
        loader = self._make_loader(tmp_path)
        # Create a directory that matches the glob pattern
        subdir = loader.manager.helpers_bin / "flavor-something"
        subdir.mkdir()
        removed = loader.clean_helpers(language=None)
        assert removed == []

    @pytest.mark.unit
    def test_find_versioned_helpers_no_matches(self, tmp_path: Path) -> None:
        """Branch 298->297: _find_versioned_helpers returns empty when no files match."""
        loader = self._make_loader(tmp_path)
        bin_dir = tmp_path / "bin"
        bin_dir.mkdir(exist_ok=True)
        result = loader._find_versioned_helpers(bin_dir, "flavor-rs-launcher")
        assert result == []


class TestAssemblyFindLauncherInDir:
    @pytest.mark.unit
    def test_find_launcher_no_exact_no_glob(self, tmp_path: Path) -> None:
        """Branch 69->73: is_dir but glob returns no matches => None."""
        from flavor.psp.format_2025.metadata.assembly import _find_launcher_in_dir

        result = _find_launcher_in_dir(
            base_path=tmp_path,
            launcher_base="flavor-rs-launcher",
            platform_str="linux_amd64",
            names=["nonexistent"],
            is_windows=False,
        )
        assert result is None

    @pytest.mark.unit
    def test_find_launcher_windows_exe_pattern(self, tmp_path: Path) -> None:
        """Branch 71->69: is_windows inserts .exe glob pattern."""
        from flavor.psp.format_2025.metadata.assembly import _find_launcher_in_dir

        # Create a .exe file matching the pattern
        exe_file = tmp_path / "flavor-rs-launcher-1.0.0-windows_amd64.exe"
        exe_file.write_text("fake")

        result = _find_launcher_in_dir(
            base_path=tmp_path,
            launcher_base="flavor-rs-launcher",
            platform_str="windows_amd64",
            names=["nonexistent"],
            is_windows=True,
        )
        assert result is not None
        assert result.name.endswith(".exe")


class TestPackageJsonManifest:
    @pytest.mark.unit
    def test_build_package_from_json_manifest(self, tmp_path: Path) -> None:
        """Line 79: manifest_type=='json' triggers _parse_json_manifest."""
        import json

        from flavor.package import build_package_from_manifest

        manifest = tmp_path / "manifest.json"
        manifest.write_text(
            json.dumps(
                {
                    "package": {"name": "testpkg", "version": "1.0.0"},
                    "execution": {"command": "python -m testpkg"},
                    "slots": [],
                }
            )
        )

        with patch("flavor.package._create_orchestrator") as mock_orch:
            mock_orch.return_value.build_package.return_value = None
            result = build_package_from_manifest(manifest_path=manifest)
        assert result is not None


class TestEnvironmentTraceBranches:
    @pytest.mark.unit
    def test_unset_all_except_preserved_trace(self) -> None:
        """Line 130: trace enabled logs unset variables."""
        from flavor.psp.format_2025.environment import _unset_all_except_preserved

        env = {"PATH": "/bin", "SECRET": "val", "HOME": "/home"}
        with (
            patch("flavor.psp.format_2025.environment.is_trace_enabled", return_value=True),
            patch("flavor.psp.format_2025.environment.plog") as mock_plog,
        ):
            _unset_all_except_preserved(env, lambda k: k == "PATH")
        assert "SECRET" not in env
        assert "HOME" not in env
        assert "PATH" in env
        assert mock_plog.trace.called

    @pytest.mark.unit
    def test_unset_glob_pattern_trace(self) -> None:
        """Line 139: trace enabled logs unset glob matches."""
        from flavor.psp.format_2025.environment import _unset_glob_pattern

        env = {"MY_VAR": "1", "MY_OTHER": "2", "KEEP": "3"}
        with (
            patch("flavor.psp.format_2025.environment.is_trace_enabled", return_value=True),
            patch("flavor.psp.format_2025.environment.plog") as mock_plog,
        ):
            _unset_glob_pattern(env, "MY_*", lambda k: False)
        assert "MY_VAR" not in env
        assert "MY_OTHER" not in env
        assert "KEEP" in env
        assert mock_plog.trace.called


# ===========================================================================
# 15. psp/format_2025/executor.py line 127, branch 215->217
#     Line 127: trace enabled logs primary substitution
#     Branch 215->217: debug enabled logs env var count
# ===========================================================================


class TestExecutorBranches:
    @pytest.mark.unit
    def test_substitute_primary_with_trace(self) -> None:
        """Line 127: trace enabled => log substitution."""
        from flavor.psp.format_2025.executor import BundleExecutor

        executor = BundleExecutor.__new__(BundleExecutor)
        executor.metadata = {
            "slots": [{"target": "app.py"}],
        }
        executor.execution_config = {"primary_slot": 0}

        with patch("flavor.psp.format_2025.executor.logger") as mock_logger:
            mock_logger.is_trace_enabled.return_value = True
            result = executor._substitute_primary("{primary}")
        assert result == "app.py"


# ===========================================================================
# 16. psp/format_2025/index.py line 254
#     Index.unpack with wrong-sized data => ValueError
# ===========================================================================


class TestIndexUnpackError:
    @pytest.mark.unit
    def test_unpack_wrong_size_raises(self) -> None:
        """Line 254: data length != DEFAULT_HEADER_SIZE."""
        from flavor.psp.format_2025.index import PSPFIndex

        with pytest.raises(ValueError, match="Index must be"):
            PSPFIndex.unpack(b"\x00" * 100)


class TestExecutorPrimarySlotOutOfRange:
    @pytest.mark.unit
    def test_substitute_primary_slot_out_of_range(self) -> None:
        """Line 129: primary_slot >= len(slots) => warning."""
        from flavor.psp.format_2025.executor import BundleExecutor

        executor = BundleExecutor.__new__(BundleExecutor)
        executor.metadata = {"slots": []}
        executor.execution_config = {"primary_slot": 5}

        result = executor._substitute_primary("{primary}")
        # The {primary} is NOT substituted
        assert "{primary}" in result


# 🌶️📦🔚
