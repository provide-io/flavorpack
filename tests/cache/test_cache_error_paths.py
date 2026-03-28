#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""Tests for CacheManager error paths and edge cases."""

from __future__ import annotations

import json
from pathlib import Path
import time
from unittest.mock import patch

import pytest


def _make_modern_pkg(
    cache_dir: Path, pkg_name: str, name: str = "pkg", version: str = "1.0"
) -> tuple[Path, Path]:
    """Create a well-formed cached package entry."""
    content_dir = cache_dir / pkg_name
    content_dir.mkdir(parents=True)

    metadata_dir = cache_dir / f".{pkg_name}.pspf"
    instance_dir = metadata_dir / "instance"
    (instance_dir / "extract").mkdir(parents=True)
    (instance_dir / "extract" / "complete").touch()

    package_dir = metadata_dir / "package"
    package_dir.mkdir(parents=True)
    (package_dir / "psp.json").write_text(json.dumps({"package": {"name": name, "version": version}}))
    return content_dir, metadata_dir


@pytest.mark.unit
class TestListCachedErrorPaths:
    """Test list_cached() handling of corrupted metadata."""

    def test_os_error_on_read_falls_back_to_unknown(self, tmp_path: Path) -> None:
        from flavor.cache import CacheManager

        cache_dir = tmp_path / "cache"
        cache_dir.mkdir()
        manager = CacheManager(cache_dir)

        _make_modern_pkg(cache_dir, "mypkg")

        with patch("flavor.cache.read_json", side_effect=OSError("read error")):
            cached = manager.list_cached()

        assert len(cached) == 1
        assert cached[0]["name"] == "unknown"
        assert cached[0]["version"] == "unknown"

    def test_no_metadata_dir_skipped(self, tmp_path: Path) -> None:
        from flavor.cache import CacheManager

        cache_dir = tmp_path / "cache"
        cache_dir.mkdir()
        manager = CacheManager(cache_dir)

        # Create content dir with no metadata dir
        content_dir = cache_dir / "orphan"
        content_dir.mkdir()

        cached = manager.list_cached()
        assert len(cached) == 0

    def test_no_completion_marker_skipped(self, tmp_path: Path) -> None:
        from flavor.cache import CacheManager

        cache_dir = tmp_path / "cache"
        cache_dir.mkdir()
        manager = CacheManager(cache_dir)

        # Create structure without completion marker
        content_dir = cache_dir / "incomplete"
        content_dir.mkdir()
        metadata_dir = cache_dir / ".incomplete.pspf"
        (metadata_dir / "instance" / "extract").mkdir(parents=True)
        # Note: no "complete" file

        cached = manager.list_cached()
        assert len(cached) == 0

    def test_hidden_dir_skipped(self, tmp_path: Path) -> None:
        from flavor.cache import CacheManager

        cache_dir = tmp_path / "cache"
        cache_dir.mkdir()
        manager = CacheManager(cache_dir)

        # Dot-prefixed dirs should be skipped
        hidden = cache_dir / ".hidden"
        hidden.mkdir()

        cached = manager.list_cached()
        assert len(cached) == 0

    def test_missing_psp_json_still_returns_entry(self, tmp_path: Path) -> None:
        from flavor.cache import CacheManager

        cache_dir = tmp_path / "cache"
        cache_dir.mkdir()
        manager = CacheManager(cache_dir)

        content_dir = cache_dir / "nojson"
        content_dir.mkdir()
        metadata_dir = cache_dir / ".nojson.pspf"
        (metadata_dir / "instance" / "extract").mkdir(parents=True)
        (metadata_dir / "instance" / "extract" / "complete").touch()
        # No psp.json file

        cached = manager.list_cached()
        assert len(cached) == 1
        assert cached[0]["name"] == "unknown"


@pytest.mark.unit
class TestCleanMaxAgeDays:
    """Test clean() with max_age_days filtering."""

    def test_clean_all_when_no_age_specified(self, tmp_path: Path) -> None:
        from flavor.cache import CacheManager

        cache_dir = tmp_path / "cache"
        cache_dir.mkdir()
        manager = CacheManager(cache_dir)

        d1 = cache_dir / "pkg1"
        d1.mkdir()
        d2 = cache_dir / "pkg2"
        d2.mkdir()

        removed = manager.clean(max_age_days=None)
        assert set(removed) == {"pkg1", "pkg2"}

    def test_clean_old_only_when_age_specified(self, tmp_path: Path) -> None:
        import os

        from flavor.cache import CacheManager

        cache_dir = tmp_path / "cache"
        cache_dir.mkdir()
        manager = CacheManager(cache_dir)

        old_dir = cache_dir / "old_pkg"
        old_dir.mkdir()
        new_dir = cache_dir / "new_pkg"
        new_dir.mkdir()

        # Make old_dir look 30 days old
        old_mtime = time.time() - (30 * 86400)
        os.utime(old_dir, (old_mtime, old_mtime))

        removed = manager.clean(max_age_days=10)

        assert "old_pkg" in removed
        assert "new_pkg" not in removed

    def test_clean_suppresses_os_error(self, tmp_path: Path) -> None:
        from flavor.cache import CacheManager

        cache_dir = tmp_path / "cache"
        cache_dir.mkdir()
        manager = CacheManager(cache_dir)

        d = cache_dir / "pkg"
        d.mkdir()

        with patch("flavor.cache.safe_rmtree", side_effect=OSError("locked")):
            removed = manager.clean(max_age_days=None)

        assert removed == []

    def test_clean_skips_files(self, tmp_path: Path) -> None:
        from flavor.cache import CacheManager

        cache_dir = tmp_path / "cache"
        cache_dir.mkdir()
        manager = CacheManager(cache_dir)

        (cache_dir / "somefile.txt").write_text("data")

        removed = manager.clean(max_age_days=None)
        assert removed == []


@pytest.mark.unit
class TestInspectWorkenv:
    """Test inspect_workenv() details."""

    def test_nonexistent_returns_exists_false(self, tmp_path: Path) -> None:
        from flavor.cache import CacheManager

        cache_dir = tmp_path / "cache"
        cache_dir.mkdir()
        manager = CacheManager(cache_dir)

        info = manager.inspect_workenv("ghost")
        assert info["exists"] is False
        assert info["metadata_type"] is None

    def test_reads_checksum_file(self, tmp_path: Path) -> None:
        from flavor.cache import CacheManager

        cache_dir = tmp_path / "cache"
        cache_dir.mkdir()
        manager = CacheManager(cache_dir)

        _content_dir, metadata_dir = _make_modern_pkg(cache_dir, "mypkg")
        checksum_file = metadata_dir / "instance" / "package.checksum"
        checksum_file.write_text("abc123\n")
        (metadata_dir / "instance" / "extract" / "complete").touch()

        info = manager.inspect_workenv("mypkg")
        assert info["checksum"] == "abc123"

    def test_extraction_complete_flag(self, tmp_path: Path) -> None:
        from flavor.cache import CacheManager

        cache_dir = tmp_path / "cache"
        cache_dir.mkdir()
        manager = CacheManager(cache_dir)

        _content_dir, _metadata_dir = _make_modern_pkg(cache_dir, "mypkg")
        info = manager.inspect_workenv("mypkg")
        assert info["extraction_complete"] is True

    def test_os_error_on_metadata_read_is_suppressed(self, tmp_path: Path) -> None:
        from flavor.cache import CacheManager

        cache_dir = tmp_path / "cache"
        cache_dir.mkdir()
        manager = CacheManager(cache_dir)

        _content_dir, _metadata_dir = _make_modern_pkg(cache_dir, "mypkg")

        with patch("flavor.cache.read_json", side_effect=OSError("can't read")):
            info = manager.inspect_workenv("mypkg")

        # Should still return basic info without raising
        assert info["exists"] is True
        assert info["package_info"] == {}


@pytest.mark.unit
class TestRemove:
    """Test remove() return values."""

    def test_remove_returns_true_when_found(self, tmp_path: Path) -> None:
        from flavor.cache import CacheManager

        cache_dir = tmp_path / "cache"
        cache_dir.mkdir()
        manager = CacheManager(cache_dir)

        pkg_dir = cache_dir / "mypkg"
        pkg_dir.mkdir()

        assert manager.remove("mypkg") is True
        assert not pkg_dir.exists()

    def test_remove_returns_false_when_not_found(self, tmp_path: Path) -> None:
        from flavor.cache import CacheManager

        cache_dir = tmp_path / "cache"
        cache_dir.mkdir()
        manager = CacheManager(cache_dir)

        assert manager.remove("ghost") is False

    def test_remove_returns_false_on_os_error(self, tmp_path: Path) -> None:
        from flavor.cache import CacheManager

        cache_dir = tmp_path / "cache"
        cache_dir.mkdir()
        manager = CacheManager(cache_dir)

        pkg_dir = cache_dir / "mypkg"
        pkg_dir.mkdir()

        with patch("flavor.cache.safe_rmtree", side_effect=OSError("locked")):
            assert manager.remove("mypkg") is False
