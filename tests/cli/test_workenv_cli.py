#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""Tests for workenv CLI subcommands via Click CliRunner."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from flavor.commands.workenv import workenv_group


def _make_pkg_entry(
    pkg_id: str = "abc123",
    name: str = "mypkg",
    version: str = "1.0",
    size: int = 1024 * 1024 * 5,  # 5 MB
    modified: float = 1_700_000_000.0,
) -> dict:
    return {
        "id": pkg_id,
        "path": f"/cache/{pkg_id}",
        "name": name,
        "version": version,
        "size": size,
        "modified": modified,
    }


@pytest.mark.unit
class TestWorkenvList:
    """Test `workenv list` command."""

    def test_list_empty_cache(self) -> None:
        runner = CliRunner()
        with patch("flavor.cache.CacheManager") as MockMgr:
            MockMgr.return_value.list_cached.return_value = []
            result = runner.invoke(workenv_group, ["list"])

        assert result.exit_code == 0
        assert "No cached packages" in result.output

    def test_list_with_packages(self) -> None:
        runner = CliRunner()
        pkg = _make_pkg_entry()
        with patch("flavor.cache.CacheManager") as MockMgr:
            MockMgr.return_value.list_cached.return_value = [pkg]
            result = runner.invoke(workenv_group, ["list"])

        assert result.exit_code == 0
        assert "mypkg" in result.output
        assert "v1.0" in result.output
        assert "abc123" in result.output

    def test_list_package_without_version(self) -> None:
        runner = CliRunner()
        pkg = _make_pkg_entry()
        del pkg["version"]
        with patch("flavor.cache.CacheManager") as MockMgr:
            MockMgr.return_value.list_cached.return_value = [pkg]
            result = runner.invoke(workenv_group, ["list"])

        assert result.exit_code == 0
        assert "mypkg" in result.output
        # When no version, should still show name
        assert "v" not in result.output or "v1" not in result.output

    def test_list_non_numeric_size_branch(self) -> None:
        runner = CliRunner()
        pkg = _make_pkg_entry()
        pkg["size"] = "not-a-number"  # triggers isinstance fallback
        with patch("flavor.cache.CacheManager") as MockMgr:
            MockMgr.return_value.list_cached.return_value = [pkg]
            result = runner.invoke(workenv_group, ["list"])

        assert result.exit_code == 0
        assert "0.0 MB" in result.output

    def test_list_non_numeric_modified_branch(self) -> None:
        runner = CliRunner()
        pkg = _make_pkg_entry()
        pkg["modified"] = "not-a-timestamp"  # triggers isinstance fallback
        with patch("flavor.cache.CacheManager") as MockMgr:
            MockMgr.return_value.list_cached.return_value = [pkg]
            result = runner.invoke(workenv_group, ["list"])

        assert result.exit_code == 0


@pytest.mark.unit
class TestWorkenvInfo:
    """Test `workenv info` command."""

    def test_info_shows_cache_stats(self) -> None:
        runner = CliRunner()
        with patch("flavor.cache.CacheManager") as MockMgr, \
             patch("flavor.cache.get_cache_dir") as mock_dir:
            mock_dir.return_value = Path("/fake/cache")
            MockMgr.return_value.list_cached.return_value = [_make_pkg_entry()]
            MockMgr.return_value.get_cache_size.return_value = 10 * 1024 * 1024
            result = runner.invoke(workenv_group, ["info"])

        assert result.exit_code == 0
        assert "Cache Information" in result.output
        assert "10.0 MB" in result.output
        assert "1" in result.output  # 1 package


@pytest.mark.unit
class TestWorkenvClean:
    """Test `workenv clean` command."""

    def test_clean_with_yes_flag_removes_all(self) -> None:
        runner = CliRunner()
        with patch("flavor.cache.CacheManager") as MockMgr:
            MockMgr.return_value.clean.return_value = ["pkg1", "pkg2"]
            result = runner.invoke(workenv_group, ["clean", "--yes"])

        assert result.exit_code == 0
        assert "2" in result.output

    def test_clean_no_packages_message(self) -> None:
        runner = CliRunner()
        with patch("flavor.cache.CacheManager") as MockMgr:
            MockMgr.return_value.clean.return_value = []
            result = runner.invoke(workenv_group, ["clean", "--yes"])

        assert result.exit_code == 0
        assert "No packages to clean" in result.output

    def test_clean_with_older_than(self) -> None:
        runner = CliRunner()
        with patch("flavor.cache.CacheManager") as MockMgr:
            MockMgr.return_value.clean.return_value = ["old_pkg"]
            result = runner.invoke(workenv_group, ["clean", "--yes", "--older-than", "7"])

        assert result.exit_code == 0
        MockMgr.return_value.clean.assert_called_once_with(max_age_days=7)

    def test_clean_aborts_without_yes(self) -> None:
        runner = CliRunner()
        with patch("flavor.cache.CacheManager"):
            result = runner.invoke(workenv_group, ["clean"], input="n\n")

        assert result.exit_code == 0
        assert "Aborted" in result.output

    def test_clean_with_older_than_prompt_includes_days(self) -> None:
        runner = CliRunner()
        with patch("flavor.cache.CacheManager") as MockMgr:
            MockMgr.return_value.clean.return_value = []
            result = runner.invoke(workenv_group, ["clean", "--older-than", "30"], input="n\n")

        assert result.exit_code == 0
        assert "30 days" in result.output


@pytest.mark.unit
class TestWorkenvRemove:
    """Test `workenv remove` command."""

    def test_remove_not_found_shows_error(self) -> None:
        runner = CliRunner()
        with patch("flavor.cache.CacheManager") as MockMgr:
            MockMgr.return_value.remove.return_value = False
            MockMgr.return_value.inspect_workenv.return_value = {"exists": False}
            result = runner.invoke(workenv_group, ["remove", "--yes", "ghost"])

        assert result.exit_code == 0
        assert "not found" in result.output

    def test_remove_success_with_yes(self) -> None:
        runner = CliRunner()
        with patch("flavor.cache.CacheManager") as MockMgr:
            MockMgr.return_value.remove.return_value = True
            result = runner.invoke(workenv_group, ["remove", "--yes", "mypkg"])

        assert result.exit_code == 0

    def test_remove_aborts_without_yes_when_found(self) -> None:
        runner = CliRunner()
        with patch("flavor.cache.CacheManager") as MockMgr:
            MockMgr.return_value.inspect_workenv.return_value = {
                "exists": True,
                "content_dir": "/cache/mypkg",
                "package_info": {"name": "mypkg"},
            }
            MockMgr.return_value._get_dir_size.return_value = 0
            result = runner.invoke(workenv_group, ["remove", "mypkg"], input="n\n")

        assert result.exit_code == 0
        assert "Aborted" in result.output


@pytest.mark.unit
class TestWorkenvInspect:
    """Test `workenv inspect` command."""

    def test_inspect_not_found_shows_error(self) -> None:
        runner = CliRunner()
        with patch("flavor.cache.CacheManager") as MockMgr:
            MockMgr.return_value.inspect_workenv.return_value = {"exists": False}
            result = runner.invoke(workenv_group, ["inspect", "ghost"])

        assert result.exit_code == 0
        assert "not found" in result.output

    def test_inspect_json_output(self) -> None:
        runner = CliRunner()
        info = {
            "name": "mypkg",
            "exists": True,
            "content_dir": "/cache/mypkg",
            "metadata_type": "instance",
            "metadata_dir": "/cache/.mypkg.pspf",
            "checksum": "abc123",
            "extraction_complete": True,
            "package_info": {"name": "mypkg", "version": "1.0", "builder": None},
        }
        with patch("flavor.cache.CacheManager") as MockMgr:
            MockMgr.return_value.inspect_workenv.return_value = info
            result = runner.invoke(workenv_group, ["inspect", "--json", "mypkg"])

        assert result.exit_code == 0
        assert "mypkg" in result.output

    def test_inspect_human_readable(self) -> None:
        runner = CliRunner()
        info = {
            "name": "mypkg",
            "exists": True,
            "content_dir": "/cache/mypkg",
            "metadata_type": "instance",
            "metadata_dir": None,
            "checksum": "abc123",
            "extraction_complete": True,
            "package_info": {"name": "mypkg", "version": "1.0", "builder": "uv"},
        }
        with patch("flavor.cache.CacheManager") as MockMgr:
            MockMgr.return_value.inspect_workenv.return_value = info
            result = runner.invoke(workenv_group, ["inspect", "mypkg"])

        assert result.exit_code == 0
        assert "mypkg" in result.output
        assert "abc123" in result.output

    def test_inspect_with_index_json(self, tmp_path: Path) -> None:
        runner = CliRunner()
        metadata_dir = tmp_path / ".mypkg.pspf"
        index_dir = metadata_dir / "instance"
        index_dir.mkdir(parents=True)
        index_file = index_dir / "index.json"
        index_file.write_text(json.dumps({
            "format_version": 0x20250100,
            "package_size": 1000,
            "launcher_size": 500,
            "slot_count": 3,
            "index_checksum": "cafebabe",
            "build_timestamp": 1700000000,
            "capabilities": 0,
            "requirements": 0,
        }))

        info = {
            "name": "mypkg",
            "exists": True,
            "content_dir": str(tmp_path / "mypkg"),
            "metadata_type": "instance",
            "metadata_dir": str(metadata_dir),
            "checksum": None,
            "extraction_complete": True,
            "package_info": {},
        }
        with patch("flavor.cache.CacheManager") as MockMgr:
            MockMgr.return_value.inspect_workenv.return_value = info
            result = runner.invoke(workenv_group, ["inspect", "mypkg"])

        assert result.exit_code == 0
        assert "Slot Count: 3" in result.output
