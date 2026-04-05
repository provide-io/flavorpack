#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""Tests for the flavor doctor diagnostic command."""

from __future__ import annotations

import os
from pathlib import Path
import sys
from unittest.mock import MagicMock, Mock, patch

from click.testing import CliRunner, Result

from flavor.cli import main as cli_main
from flavor.helpers.manager import HelperInfo


def _make_helper(name: str, tmp_path: Path) -> HelperInfo:
    """Create a HelperInfo with a real file on disk."""
    helper_path = tmp_path / name
    helper_path.write_bytes(b"\x7fELF")
    helper_path.chmod(0o755)
    return HelperInfo(
        name=name,
        path=helper_path,
        type="launcher" if "launcher" in name else "builder",
        language="go" if "-go-" in name else "rust",
        size=1_200_000,
        version="v0.3.21",
    )


class TestDoctorCommand:
    """Tests for flavor doctor."""

    def _run(self, *args: str) -> Result:
        runner = CliRunner()
        return runner.invoke(cli_main, ["doctor", *args])

    @patch("flavor.commands.doctor.get_trusted_keys_dir")
    @patch("flavor.commands.doctor.get_config_dir")
    @patch("flavor.commands.doctor.get_cache_dir")
    @patch("flavor.commands.doctor.HelperManager")
    def test_runs_without_crash(
        self,
        mock_mgr_cls: Mock,
        mock_cache_dir: Mock,
        mock_config_dir: Mock,
        mock_keys_dir: Mock,
        tmp_path: Path,
    ) -> None:
        """Doctor command runs without crashing."""
        helper = _make_helper("flavor-go-launcher-darwin_arm64", tmp_path)
        mock_mgr = MagicMock()
        mock_mgr.list_helpers.return_value = {"launchers": [helper], "builders": []}
        mock_mgr_cls.return_value = mock_mgr

        cache = tmp_path / "cache"
        cache.mkdir()
        mock_cache_dir.return_value = cache

        config = tmp_path / "config"
        config.mkdir()
        mock_config_dir.return_value = config

        keys = tmp_path / "keys"
        keys.mkdir()
        (keys / "mykey.pub").write_text("pubkey")
        mock_keys_dir.return_value = keys

        result = self._run()
        assert result.exit_code == 0

    @patch("flavor.commands.doctor.get_trusted_keys_dir")
    @patch("flavor.commands.doctor.get_config_dir")
    @patch("flavor.commands.doctor.get_cache_dir")
    @patch("flavor.commands.doctor.HelperManager")
    def test_output_contains_header(
        self,
        mock_mgr_cls: Mock,
        mock_cache_dir: Mock,
        mock_config_dir: Mock,
        mock_keys_dir: Mock,
        tmp_path: Path,
    ) -> None:
        """Output contains the FlavorPack Doctor header."""
        mock_mgr = MagicMock()
        mock_mgr.list_helpers.return_value = {"launchers": [], "builders": []}
        mock_mgr_cls.return_value = mock_mgr
        mock_cache_dir.return_value = tmp_path / "cache"
        mock_config_dir.return_value = tmp_path / "config"
        mock_keys_dir.return_value = tmp_path / "keys"

        result = self._run()
        assert "FlavorPack Doctor" in result.output

    @patch("flavor.commands.doctor.get_trusted_keys_dir")
    @patch("flavor.commands.doctor.get_config_dir")
    @patch("flavor.commands.doctor.get_cache_dir")
    @patch("flavor.commands.doctor.HelperManager")
    def test_exit_code_0_with_helpers(
        self,
        mock_mgr_cls: Mock,
        mock_cache_dir: Mock,
        mock_config_dir: Mock,
        mock_keys_dir: Mock,
        tmp_path: Path,
    ) -> None:
        """Exit code is 0 when helpers are present and cache is writable."""
        helper = _make_helper("flavor-go-launcher-darwin_arm64", tmp_path)
        mock_mgr = MagicMock()
        mock_mgr.list_helpers.return_value = {"launchers": [helper], "builders": []}
        mock_mgr_cls.return_value = mock_mgr

        cache = tmp_path / "cache"
        cache.mkdir()
        mock_cache_dir.return_value = cache

        config = tmp_path / "config"
        mock_config_dir.return_value = config

        keys = tmp_path / "keys"
        keys.mkdir()
        (keys / "k.pub").write_text("key")
        mock_keys_dir.return_value = keys

        result = self._run()
        assert result.exit_code == 0
        assert "[OK]" in result.output

    @patch("flavor.commands.doctor.get_trusted_keys_dir")
    @patch("flavor.commands.doctor.get_config_dir")
    @patch("flavor.commands.doctor.get_cache_dir")
    @patch("flavor.commands.doctor.HelperManager")
    def test_warns_when_no_helpers(
        self,
        mock_mgr_cls: Mock,
        mock_cache_dir: Mock,
        mock_config_dir: Mock,
        mock_keys_dir: Mock,
        tmp_path: Path,
    ) -> None:
        """Doctor warns when no helpers are found."""
        mock_mgr = MagicMock()
        mock_mgr.list_helpers.return_value = {"launchers": [], "builders": []}
        mock_mgr_cls.return_value = mock_mgr

        cache = tmp_path / "cache"
        cache.mkdir()
        mock_cache_dir.return_value = cache
        mock_config_dir.return_value = tmp_path / "config"

        keys = tmp_path / "keys"
        keys.mkdir()
        (keys / "k.pub").write_text("key")
        mock_keys_dir.return_value = keys

        result = self._run()
        # No hard error for missing helpers, but a warning is emitted
        assert "none found" in result.output or "[WARN]" in result.output

    @patch("flavor.commands.doctor.get_trusted_keys_dir")
    @patch("flavor.commands.doctor.get_config_dir")
    @patch("flavor.commands.doctor.get_cache_dir")
    @patch("flavor.commands.doctor.HelperManager")
    def test_warns_when_no_trusted_keys(
        self,
        mock_mgr_cls: Mock,
        mock_cache_dir: Mock,
        mock_config_dir: Mock,
        mock_keys_dir: Mock,
        tmp_path: Path,
    ) -> None:
        """Doctor warns when the trusted keys directory has no .pub files."""
        helper = _make_helper("flavor-go-launcher-darwin_arm64", tmp_path)
        mock_mgr = MagicMock()
        mock_mgr.list_helpers.return_value = {"launchers": [helper], "builders": []}
        mock_mgr_cls.return_value = mock_mgr

        cache = tmp_path / "cache"
        cache.mkdir()
        mock_cache_dir.return_value = cache
        mock_config_dir.return_value = tmp_path / "config"

        keys = tmp_path / "keys"
        keys.mkdir()  # exists but empty
        mock_keys_dir.return_value = keys

        result = self._run()
        assert "[WARN]" in result.output
        assert "key" in result.output.lower()


class TestDoctorCoverageGaps:
    """Cover remaining uncovered lines in doctor.py."""

    def _run(self, *args: str) -> Result:
        runner = CliRunner()
        return runner.invoke(cli_main, ["doctor", *args])

    @patch("flavor.commands.doctor.get_trusted_keys_dir")
    @patch("flavor.commands.doctor.get_config_dir")
    @patch("flavor.commands.doctor.get_cache_dir")
    @patch("flavor.commands.doctor.HelperManager")
    def test_python_below_311_warns(
        self,
        mock_mgr_cls: Mock,
        mock_cache: Mock,
        mock_config: Mock,
        mock_keys: Mock,
        tmp_path: Path,
    ) -> None:
        """Lines 40-42: Python < 3.11 triggers WARN."""
        mock_mgr_cls.return_value.list_helpers.return_value = {"launchers": [], "builders": []}
        cache = tmp_path / "cache"
        cache.mkdir()
        mock_cache.return_value = cache
        mock_config.return_value = tmp_path / "config"
        keys = tmp_path / "keys"
        keys.mkdir()
        (keys / "k.pub").write_text("key")
        mock_keys.return_value = keys

        fake_info = MagicMock(major=2, minor=7)
        with patch("flavor.commands.doctor.sys") as mock_sys:
            mock_sys.version = "2.7.18 (default)"
            mock_sys.version_info = fake_info
            mock_sys.platform = sys.platform
            result = self._run()
        assert "WARN" in result.output

    @patch("flavor.commands.doctor.get_trusted_keys_dir")
    @patch("flavor.commands.doctor.get_config_dir")
    @patch("flavor.commands.doctor.get_cache_dir")
    @patch("flavor.commands.doctor.HelperManager")
    def test_missing_helper_errors(
        self,
        mock_mgr_cls: Mock,
        mock_cache: Mock,
        mock_config: Mock,
        mock_keys: Mock,
        tmp_path: Path,
    ) -> None:
        """Lines 72-74, 124-129: MISSING helper adds error, exit code 1."""
        missing = HelperInfo(
            name="flavor-go-launcher-linux_amd64",
            path=tmp_path / "nonexistent" / "helper",
            type="launcher",
            language="go",
            size=0,
            version=None,
        )
        mock_mgr_cls.return_value.list_helpers.return_value = {"launchers": [missing], "builders": []}
        cache = tmp_path / "cache"
        cache.mkdir()
        mock_cache.return_value = cache
        mock_config.return_value = tmp_path / "config"
        keys = tmp_path / "keys"
        keys.mkdir()
        (keys / "k.pub").write_text("key")
        mock_keys.return_value = keys

        result = self._run()
        assert result.exit_code == 1
        assert "MISSING" in result.output

    @patch("flavor.commands.doctor.get_trusted_keys_dir")
    @patch("flavor.commands.doctor.get_config_dir")
    @patch("flavor.commands.doctor.get_cache_dir")
    @patch("flavor.commands.doctor.HelperManager")
    def test_not_executable_helper(
        self,
        mock_mgr_cls: Mock,
        mock_cache: Mock,
        mock_config: Mock,
        mock_keys: Mock,
        tmp_path: Path,
    ) -> None:
        """Lines 75-77: Helper exists but not executable."""
        helper_path = tmp_path / "helper"
        helper_path.write_bytes(b"\x7fELF")
        helper_path.chmod(0o644)
        helper = HelperInfo(
            name="flavor-go-launcher",
            path=helper_path,
            type="launcher",
            language="go",
            size=4,
            version="v1",
        )
        mock_mgr_cls.return_value.list_helpers.return_value = {"launchers": [helper], "builders": []}
        cache = tmp_path / "cache"
        cache.mkdir()
        mock_cache.return_value = cache
        mock_config.return_value = tmp_path / "config"
        keys = tmp_path / "keys"
        keys.mkdir()
        (keys / "k.pub").write_text("key")
        mock_keys.return_value = keys

        orig_access = os.access

        def fake_access(path: object, mode: int) -> bool:
            if mode == os.X_OK:
                return False
            return orig_access(path, mode)  # type: ignore[arg-type]

        with patch("flavor.commands.doctor.os.access", side_effect=fake_access):
            result = self._run()
        assert result.exit_code == 1
        assert "NOT-EXEC" in result.output

    @patch("flavor.commands.doctor.get_trusted_keys_dir")
    @patch("flavor.commands.doctor.get_config_dir")
    @patch("flavor.commands.doctor.get_cache_dir")
    @patch("flavor.commands.doctor.HelperManager")
    def test_cache_not_writable(
        self,
        mock_mgr_cls: Mock,
        mock_cache: Mock,
        mock_config: Mock,
        mock_keys: Mock,
        tmp_path: Path,
    ) -> None:
        """Lines 97-98: Cache not writable adds error."""
        mock_mgr_cls.return_value.list_helpers.return_value = {"launchers": [], "builders": []}
        cache = tmp_path / "cache"
        cache.mkdir()
        mock_cache.return_value = cache
        mock_config.return_value = tmp_path / "config"
        keys = tmp_path / "keys"
        keys.mkdir()
        (keys / "k.pub").write_text("key")
        mock_keys.return_value = keys

        orig_access = os.access

        def fake_access(path: object, mode: int) -> bool:
            if path == cache and mode == os.W_OK:
                return False
            return orig_access(path, mode)  # type: ignore[arg-type]

        with patch("flavor.commands.doctor.os.access", side_effect=fake_access):
            result = self._run()
        assert result.exit_code == 1
        assert "NOT WRITABLE" in result.output


# 🌶️📦🔚
