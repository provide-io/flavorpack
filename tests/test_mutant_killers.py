#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""Targeted tests to kill surviving mutants across the top 5 mutation-heavy files.

Files targeted:
  1. src/flavor/psp/format_2025/builder.py
  2. src/flavor/psp/format_2025/handlers.py
  3. src/flavor/package.py
  4. src/flavor/cache.py
  5. src/flavor/config/policy.py
"""

from __future__ import annotations

from datetime import UTC, datetime
import hashlib
import json
import os
from pathlib import Path
import time
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from flavor.config.defaults import (
    ACCESS_AUTO,
    CACHE_NORMAL,
    CAPABILITY_MMAP,
    CAPABILITY_PAGE_ALIGNED,
    CAPABILITY_SIGNED,
)
from flavor.config.policy import (
    EffectivePolicy,
    EnforcementMode,
    EnforcementPolicy,
    OperatorPolicy,
    PackagePolicy,
    _apply_enforcement,
    _parse_enforcement_section,
    _validate_operator_policy_value,
    enforce_policy,
    get_current_platform,
    merge_policy,
    parse_package_policy,
)
from flavor.psp.format_2025.constants import (
    DEFAULT_MAX_MEMORY,
    DEFAULT_MIN_MEMORY,
    OP_BZIP2,
    OP_GZIP,
    OP_NONE,
    OP_TAR,
    OP_XZ,
    OP_ZSTD,
)
from flavor.psp.format_2025.handlers import (
    apply_operations,
    map_operations,
    reverse_operations,
)
from flavor.psp.format_2025.operations import (
    pack_operations,
)
from flavor.psp.format_2025.spec import (
    BuildOptions,
    BuildResult,
    BuildSpec,
    KeyConfig,
    PreparedSlot,
)

# ---------------------------------------------------------------------------
# 1. builder.py — create_index, _apply_operations, _load_slot_data, prepare_slots
# ---------------------------------------------------------------------------


class TestBuilderCreateIndex:
    """Kill mutants in builder.create_index: capability flags, default values, policy hash."""

    def _make_spec(
        self,
        enable_mmap: bool = True,
        page_aligned: bool = True,
        metadata: dict[str, Any] | None = None,
    ) -> BuildSpec:
        opts = BuildOptions(enable_mmap=enable_mmap, page_aligned=page_aligned)
        return BuildSpec(metadata=metadata or {}, options=opts)

    def test_capabilities_mmap_and_page_aligned(self) -> None:
        from flavor.psp.format_2025.builder import create_index

        spec = self._make_spec(enable_mmap=True, page_aligned=True)
        index = create_index(spec, [], b"\x00" * 32, "")
        assert index.capabilities & CAPABILITY_MMAP != 0
        assert index.capabilities & CAPABILITY_PAGE_ALIGNED != 0
        assert index.capabilities & CAPABILITY_SIGNED != 0

    def test_capabilities_no_mmap_no_page(self) -> None:
        from flavor.psp.format_2025.builder import create_index

        spec = self._make_spec(enable_mmap=False, page_aligned=False)
        index = create_index(spec, [], b"\x00" * 32, "")
        # MMAP and PAGE_ALIGNED must NOT be set
        assert index.capabilities & CAPABILITY_MMAP == 0
        assert index.capabilities & CAPABILITY_PAGE_ALIGNED == 0
        # SIGNED must always be set
        assert index.capabilities & CAPABILITY_SIGNED != 0

    def test_default_access_and_memory(self) -> None:
        from flavor.psp.format_2025.builder import create_index

        spec = self._make_spec()
        index = create_index(spec, [], b"\x00" * 32, "")
        assert index.access_mode == ACCESS_AUTO
        assert index.cache_strategy == CACHE_NORMAL
        assert index.max_memory == DEFAULT_MAX_MEMORY
        assert index.min_memory == DEFAULT_MIN_MEMORY

    def test_slot_count_matches_input(self) -> None:
        from flavor.psp.format_2025.builder import create_index
        from flavor.psp.format_2025.slots import SlotMetadata

        slot_meta = SlotMetadata(
            index=0, id="test", source="", target="test", size=0, checksum="00", operations="RAW"
        )
        prepared = PreparedSlot(metadata=slot_meta, data=b"hello")
        spec = self._make_spec()
        index = create_index(spec, [prepared, prepared], b"\x00" * 32, "")
        assert index.slot_count == 2

    def test_attestation_key_fp_with_real_key(self) -> None:
        from flavor.psp.format_2025.builder import create_index

        pub = b"\x01" * 32
        spec = self._make_spec()
        index = create_index(spec, [], pub, "")
        expected_fp = hashlib.sha256(pub).hexdigest().encode("ascii")
        assert index.attestation_key_fp == expected_fp

    def test_attestation_key_fp_with_zero_key(self) -> None:
        from flavor.psp.format_2025.builder import create_index

        spec = self._make_spec()
        index = create_index(spec, [], b"\x00" * 32, "")
        # Should remain the default (zeros)
        assert index.attestation_key_fp == b"\x00" * 64

    def test_attestation_sbom_digest_bound(self) -> None:
        from flavor.psp.format_2025.builder import create_index

        digest = "ab" * 32  # 64 hex chars
        spec = self._make_spec()
        index = create_index(spec, [], b"\x00" * 32, digest)
        assert index.attestation_sbom_digest == digest.encode("ascii")

    def test_policy_hash_in_index(self) -> None:
        from flavor.psp.format_2025.builder import create_index

        policy = {"max_age_days": 30, "platforms": ["linux_amd64"]}
        spec = self._make_spec(metadata={"policy": policy})
        index = create_index(spec, [], b"\x00" * 32, "")
        canonical = json.dumps(policy, sort_keys=True, separators=(",", ":"))
        expected_hash = hashlib.sha256(canonical.encode()).hexdigest()
        assert index.attestation_policy_hash == expected_hash.encode("ascii").ljust(64, b"\x00")[:64]


class TestBuilderApplyOperations:
    """Kill mutants in builder._apply_operations: gzip detection, delegation."""

    def test_already_gzipped_returns_as_is(self) -> None:
        from flavor.psp.format_2025.builder import _apply_operations

        gzip_data = b"\x1f\x8b\x08" + b"\x00" * 100
        opts = BuildOptions()
        result = _apply_operations(gzip_data, 0x10, opts)
        # Must return the original data unchanged
        assert result == gzip_data

    def test_not_gzipped_delegates(self) -> None:
        from flavor.psp.format_2025.builder import _apply_operations

        data = b"hello world"
        opts = BuildOptions(compression_level=6)
        with patch("flavor.psp.format_2025.builder.handlers") as mock_handlers:
            mock_handlers.apply_operations.return_value = b"compressed"
            result = _apply_operations(data, 0x10, opts)
            mock_handlers.apply_operations.assert_called_once_with(
                data=data, packed_ops=0x10, compression_level=6, deterministic=False
            )
            assert result == b"compressed"

    def test_short_data_not_detected_as_gzip(self) -> None:
        """Data shorter than 3 bytes should not trigger gzip detection."""
        from flavor.psp.format_2025.builder import _apply_operations

        data = b"\x1f\x8b"  # Only 2 bytes
        opts = BuildOptions()
        with patch("flavor.psp.format_2025.builder.handlers") as mock_handlers:
            mock_handlers.apply_operations.return_value = data
            _apply_operations(data, 0x10, opts)
            mock_handlers.apply_operations.assert_called_once()


class TestBuilderLoadSlotData:
    """Kill mutants in builder._load_slot_data: empty source, workenv, dir vs file."""

    def test_empty_source_returns_empty_bytes(self) -> None:
        from flavor.psp.format_2025.builder import _load_slot_data
        from flavor.psp.format_2025.slots import SlotMetadata

        slot = SlotMetadata(index=0, id="empty", source="", target="t", size=0, checksum="00")
        assert _load_slot_data(slot) == b""

    def test_file_source_reads_bytes(self, tmp_path: Path) -> None:
        from flavor.psp.format_2025.builder import _load_slot_data
        from flavor.psp.format_2025.slots import SlotMetadata

        f = tmp_path / "data.bin"
        f.write_bytes(b"binary content")
        slot = SlotMetadata(index=0, id="f", source=str(f), target="t", size=14, checksum="00")
        assert _load_slot_data(slot) == b"binary content"

    def test_missing_source_raises_build_error(self) -> None:
        from flavor.exceptions import BuildError
        from flavor.psp.format_2025.builder import _load_slot_data
        from flavor.psp.format_2025.slots import SlotMetadata

        slot = SlotMetadata(index=0, id="missing", source="/does/not/exist", target="t", size=0, checksum="00")
        with pytest.raises(BuildError, match="does not exist"):
            _load_slot_data(slot)

    def test_directory_source_creates_tar(self, tmp_path: Path) -> None:
        from flavor.psp.format_2025.builder import _load_slot_data
        from flavor.psp.format_2025.slots import SlotMetadata

        d = tmp_path / "mydir"
        d.mkdir()
        (d / "hello.txt").write_text("hi")
        slot = SlotMetadata(index=0, id="dir", source=str(d), target="t", size=0, checksum="00")
        with patch("flavor.psp.format_2025.builder.handlers") as mock_h:
            mock_h.create_tar_archive.return_value = b"tarball"
            result = _load_slot_data(slot)
            mock_h.create_tar_archive.assert_called_once_with(Path(str(d)), deterministic=True)
            assert result == b"tarball"

    def test_workenv_substitution(self, tmp_path: Path) -> None:
        from flavor.psp.format_2025.builder import _load_slot_data
        from flavor.psp.format_2025.slots import SlotMetadata

        f = tmp_path / "data.bin"
        f.write_bytes(b"wenv")
        slot = SlotMetadata(
            index=0,
            id="w",
            source="{workenv}/data.bin",
            target="t",
            size=4,
            checksum="00",
        )
        with patch.dict(os.environ, {"FLAVOR_WORKENV_BASE": str(tmp_path)}):
            assert _load_slot_data(slot) == b"wenv"


# ---------------------------------------------------------------------------
# 2. handlers.py — map_operations, apply_operations, reverse_operations, etc.
# ---------------------------------------------------------------------------


class TestHandlersMapOperations:
    """Kill mutants in handlers.map_operations: OP_NONE skip, unsupported raises."""

    def test_op_none_skipped(self) -> None:
        result = map_operations([OP_NONE, OP_GZIP])
        # OP_NONE should be filtered out
        assert len(result) == 1

    def test_unsupported_op_raises_value_error(self) -> None:
        with pytest.raises(ValueError, match="Unsupported PSPF operation"):
            map_operations([0xFF])

    def test_known_ops_map_correctly(self) -> None:
        from provide.foundation.archive import ArchiveOperation as FoundationOp

        result = map_operations([OP_GZIP])
        assert result == [FoundationOp.GZIP]

        result = map_operations([OP_TAR, OP_GZIP])
        assert result == [FoundationOp.TAR, FoundationOp.GZIP]

    def test_all_compression_ops(self) -> None:
        from provide.foundation.archive import ArchiveOperation as FoundationOp

        result = map_operations([OP_BZIP2])
        assert result == [FoundationOp.BZIP2]
        result = map_operations([OP_XZ])
        assert result == [FoundationOp.XZ]
        result = map_operations([OP_ZSTD])
        assert result == [FoundationOp.ZSTD]


class TestHandlersApplyOperations:
    """Kill mutants in handlers.apply_operations: zero passthrough, compression_level bounds."""

    def test_packed_ops_zero_returns_data(self) -> None:
        data = b"untouched"
        assert apply_operations(data, 0) is data

    def test_compression_level_below_1_raises(self) -> None:
        with pytest.raises(ValueError, match="Compression level must be 1-9"):
            apply_operations(b"x", pack_operations([OP_GZIP]), compression_level=0)

    def test_compression_level_above_9_raises(self) -> None:
        with pytest.raises(ValueError, match="Compression level must be 1-9"):
            apply_operations(b"x", pack_operations([OP_GZIP]), compression_level=10)

    def test_compression_level_boundary_1(self) -> None:
        """Level 1 should be valid (boundary)."""
        packed = pack_operations([OP_GZIP])
        result = apply_operations(b"test data", packed, compression_level=1)
        assert isinstance(result, bytes)
        assert len(result) > 0

    def test_compression_level_boundary_9(self) -> None:
        """Level 9 should be valid (boundary)."""
        packed = pack_operations([OP_GZIP])
        result = apply_operations(b"test data", packed, compression_level=9)
        assert isinstance(result, bytes)

    def test_tar_only_returns_original_data(self) -> None:
        """TAR ops are skipped; if only TAR remains, return data unchanged."""
        packed = pack_operations([OP_TAR])
        data = b"just tarred"
        result = apply_operations(data, packed)
        assert result == data

    def test_gzip_roundtrip(self) -> None:
        packed = pack_operations([OP_GZIP])
        data = b"roundtrip test data for compression"
        compressed = apply_operations(data, packed, compression_level=6)
        assert compressed != data
        decompressed = reverse_operations(compressed, packed)
        assert decompressed == data


class TestHandlersReverseOperations:
    """Kill mutants in handlers.reverse_operations: zero passthrough, operation reversal order."""

    def test_packed_ops_zero_returns_data(self) -> None:
        data = b"untouched"
        assert reverse_operations(data, 0) is data

    def test_bzip2_roundtrip(self) -> None:
        packed = pack_operations([OP_BZIP2])
        data = b"bzip2 roundtrip test data"
        compressed = apply_operations(data, packed, compression_level=6)
        decompressed = reverse_operations(compressed, packed)
        assert decompressed == data

    def test_xz_roundtrip(self) -> None:
        packed = pack_operations([OP_XZ])
        data = b"xz roundtrip test"
        compressed = apply_operations(data, packed, compression_level=6)
        decompressed = reverse_operations(compressed, packed)
        assert decompressed == data


# ---------------------------------------------------------------------------
# 3. package.py — parsing, output path, key setup
# ---------------------------------------------------------------------------


class TestPackageDetermineOutputPath:
    """Kill mutants in package._determine_output_path: default extension, custom path."""

    def test_custom_output_path_returned(self, tmp_path: Path) -> None:
        from flavor.package import _determine_output_path

        custom = tmp_path / "out.psp"
        assert _determine_output_path(custom, tmp_path, "pkg") == custom

    def test_default_psp_extension(self, tmp_path: Path) -> None:
        from flavor.package import _determine_output_path

        with patch("flavor.package.sys") as mock_sys:
            mock_sys.platform = "linux"
            result = _determine_output_path(None, tmp_path, "myapp")
            assert result == tmp_path / "dist" / "myapp.psp"

    def test_windows_exe_extension(self, tmp_path: Path) -> None:
        from flavor.package import _determine_output_path

        with patch("flavor.package.sys") as mock_sys:
            mock_sys.platform = "win32"
            result = _determine_output_path(None, tmp_path, "myapp")
            assert result == tmp_path / "dist" / "myapp.exe"


class TestPackageSetupKeyPaths:
    """Kill mutants in package._setup_key_paths."""

    def test_key_seed_passes_through(self) -> None:
        from flavor.package import _setup_key_paths

        priv, pub = _setup_key_paths(Path("/k"), Path("/p"), Path("/m"), "seed123")
        assert priv == Path("/k")
        assert pub == Path("/p")

    def test_public_without_private_raises(self) -> None:
        from flavor.package import _setup_key_paths

        with pytest.raises(ValueError, match="Public key path requires a private key"):
            _setup_key_paths(None, Path("/pub"), Path("/m"), None)

    def test_both_none_ok(self) -> None:
        from flavor.package import _setup_key_paths

        priv, pub = _setup_key_paths(None, None, Path("/m"), None)
        assert priv is None
        assert pub is None


class TestPackageParseJsonManifest:
    """Kill mutants in package._parse_json_manifest: missing fields raise ValueError."""

    def test_missing_package_name_raises(self, tmp_path: Path) -> None:
        from flavor.package import _parse_json_manifest

        manifest = tmp_path / "manifest.json"
        manifest.write_text(json.dumps({"package": {"version": "1.0"}, "execution": {"command": "run"}}))
        with pytest.raises(ValueError, match="Package name"):
            _parse_json_manifest(manifest)

    def test_missing_version_raises(self, tmp_path: Path) -> None:
        from flavor.package import _parse_json_manifest

        manifest = tmp_path / "manifest.json"
        manifest.write_text(json.dumps({"package": {"name": "app"}, "execution": {"command": "run"}}))
        with pytest.raises(ValueError, match="Package version"):
            _parse_json_manifest(manifest)

    def test_missing_execution_command_raises(self, tmp_path: Path) -> None:
        from flavor.package import _parse_json_manifest

        manifest = tmp_path / "manifest.json"
        manifest.write_text(json.dumps({"package": {"name": "app", "version": "1.0"}, "execution": {}}))
        with pytest.raises(ValueError, match="Execution command"):
            _parse_json_manifest(manifest)

    def test_valid_json_manifest(self, tmp_path: Path) -> None:
        from flavor.package import _parse_json_manifest

        manifest = tmp_path / "manifest.json"
        manifest.write_text(
            json.dumps({"package": {"name": "app", "version": "2.0"}, "execution": {"command": "main"}})
        )
        result = _parse_json_manifest(manifest)
        assert result["project_name"] == "app"
        assert result["version"] == "2.0"
        assert result["entry_point"] == "main"
        assert result["package_name"] == "app"
        assert result["cli_scripts"] == {}


class TestPackageGetVersionFromToml:
    """Kill mutants in package._get_version_from_toml: static, dynamic, fallback."""

    def test_static_version(self) -> None:
        from flavor.package import _get_version_from_toml

        assert _get_version_from_toml({"version": "3.2.1"}, Path("/fake"), "pkg") == "3.2.1"

    def test_dynamic_not_in_dynamic_raises(self) -> None:
        from flavor.package import _get_version_from_toml

        with pytest.raises(ValueError, match="dynamic"):
            _get_version_from_toml({"dynamic": []}, Path("/fake"), "pkg")

    def test_dynamic_with_version_file(self, tmp_path: Path) -> None:
        from flavor.package import _get_version_from_toml

        manifest = tmp_path / "pyproject.toml"
        manifest.touch()
        (tmp_path / "VERSION").write_text("4.5.6\n")
        result = _get_version_from_toml({"dynamic": ["version"]}, manifest, "pkg")
        assert result == "4.5.6"


class TestPackageGetEntryPointFromToml:
    """Kill mutants in package._get_entry_point_from_toml."""

    def test_explicit_entry_point(self) -> None:
        from flavor.package import _get_entry_point_from_toml

        assert _get_entry_point_from_toml({"entry_point": "main:run"}, "pkg", {}) == "main:run"

    def test_cli_scripts_fallback(self) -> None:
        from flavor.package import _get_entry_point_from_toml

        result = _get_entry_point_from_toml({}, "myapp", {"myapp": "myapp.cli:main"})
        assert result == "myapp.cli:main"

    def test_no_entry_point_raises(self) -> None:
        from flavor.package import _get_entry_point_from_toml

        with pytest.raises(ValueError, match="entry_point"):
            _get_entry_point_from_toml({}, "pkg", {})


class TestPackageGetPackageName:
    """Kill mutants in package._get_package_name_from_toml."""

    def test_direct_package_name(self) -> None:
        from flavor.package import _get_package_name_from_toml

        assert _get_package_name_from_toml({"package_name": "custom"}, "default") == "custom"

    def test_metadata_package_name(self) -> None:
        from flavor.package import _get_package_name_from_toml

        assert _get_package_name_from_toml({"metadata": {"package_name": "meta"}}, "default") == "meta"

    def test_fallback_to_project_name(self) -> None:
        from flavor.package import _get_package_name_from_toml

        assert _get_package_name_from_toml({}, "fallback") == "fallback"


# ---------------------------------------------------------------------------
# 4. cache.py — get_cache_dir, CacheManager
# ---------------------------------------------------------------------------


class TestCacheGetCacheDir:
    """Kill mutants in cache.get_cache_dir: env var priority, XDG, default."""

    def test_flavor_cache_dir_env(self) -> None:
        from flavor.cache import get_cache_dir

        with patch.dict(os.environ, {"FLAVOR_CACHE_DIR": "/custom/cache"}, clear=False):
            assert get_cache_dir() == Path("/custom/cache")

    def test_flavor_cache_compat_env(self) -> None:
        from flavor.cache import get_cache_dir

        env = {"FLAVOR_CACHE": "/compat/cache"}
        with patch.dict(os.environ, env, clear=False):
            # Must remove FLAVOR_CACHE_DIR to test the fallback
            os.environ.pop("FLAVOR_CACHE_DIR", None)
            assert get_cache_dir() == Path("/compat/cache")

    def test_xdg_cache_home(self) -> None:
        from flavor.cache import get_cache_dir

        env = {"XDG_CACHE_HOME": "/xdg/cache"}
        with patch.dict(os.environ, env, clear=False):
            os.environ.pop("FLAVOR_CACHE_DIR", None)
            os.environ.pop("FLAVOR_CACHE", None)
            result = get_cache_dir()
            assert result == Path("/xdg/cache/flavor/workenv")

    def test_default_cache_dir(self) -> None:
        from flavor.cache import get_cache_dir

        with patch.dict(os.environ, {}, clear=True):
            result = get_cache_dir()
            assert result == Path.home() / ".cache" / "flavor" / "workenv"


class TestCacheManagerClean:
    """Kill mutants in CacheManager.clean: age comparison, removal logic."""

    def test_clean_all_removes_directories(self, tmp_path: Path) -> None:
        from flavor.cache import CacheManager

        (tmp_path / "pkg1").mkdir()
        (tmp_path / "pkg2").mkdir()
        mgr = CacheManager(cache_dir=tmp_path)
        removed = mgr.clean(max_age_days=None)
        assert len(removed) == 2

    def test_clean_by_age_boundary(self, tmp_path: Path) -> None:
        from flavor.cache import CacheManager

        old_dir = tmp_path / "old_pkg"
        old_dir.mkdir()
        # Make it 10 days old
        old_time = time.time() - (10 * 86400 + 1)
        os.utime(old_dir, (old_time, old_time))

        new_dir = tmp_path / "new_pkg"
        new_dir.mkdir()

        mgr = CacheManager(cache_dir=tmp_path)
        removed = mgr.clean(max_age_days=10)
        assert "old_pkg" in removed
        assert "new_pkg" not in removed

    def test_clean_recent_not_removed(self, tmp_path: Path) -> None:
        """Package younger than max_age_days should NOT be removed."""
        from flavor.cache import CacheManager

        d = tmp_path / "recent"
        d.mkdir()
        # Set modification to 1 day ago (well within 10-day limit)
        recent_time = time.time() - (1 * 86400)
        os.utime(d, (recent_time, recent_time))

        mgr = CacheManager(cache_dir=tmp_path)
        removed = mgr.clean(max_age_days=10)
        assert "recent" not in removed


class TestCacheManagerRemove:
    """Kill mutants in CacheManager.remove: returns True/False correctly."""

    def test_remove_existing(self, tmp_path: Path) -> None:
        from flavor.cache import CacheManager

        (tmp_path / "mypkg").mkdir()
        mgr = CacheManager(cache_dir=tmp_path)
        assert mgr.remove("mypkg") is True
        assert not (tmp_path / "mypkg").exists()

    def test_remove_nonexistent(self, tmp_path: Path) -> None:
        from flavor.cache import CacheManager

        mgr = CacheManager(cache_dir=tmp_path)
        assert mgr.remove("ghost") is False


class TestCacheManagerGetSize:
    """Kill mutants in CacheManager.get_cache_size and _get_dir_size."""

    def test_size_sums_files(self, tmp_path: Path) -> None:
        from flavor.cache import CacheManager

        d = tmp_path / "pkg"
        d.mkdir()
        (d / "a.bin").write_bytes(b"x" * 100)
        (d / "b.bin").write_bytes(b"y" * 50)
        mgr = CacheManager(cache_dir=tmp_path)
        assert mgr.get_cache_size() == 150

    def test_empty_cache_size_zero(self, tmp_path: Path) -> None:
        from flavor.cache import CacheManager

        mgr = CacheManager(cache_dir=tmp_path)
        assert mgr.get_cache_size() == 0


# ---------------------------------------------------------------------------
# 5. policy.py — merge_policy, enforce_policy, parsing, validation
# ---------------------------------------------------------------------------


class TestPolicyMerge:
    """Kill mutants in merge_policy: platform intersection, stricter-wins logic."""

    def test_platform_intersection(self) -> None:
        pkg = PackagePolicy(platforms=["linux_amd64", "darwin_arm64"])
        op = OperatorPolicy(allow_platforms=["linux_amd64", "windows_amd64"])
        eff = merge_policy(pkg, op)
        assert eff.platforms == ["linux_amd64"]

    def test_only_operator_platforms(self) -> None:
        pkg = PackagePolicy(platforms=[])
        op = OperatorPolicy(allow_platforms=["linux_amd64"])
        eff = merge_policy(pkg, op)
        assert eff.platforms == ["linux_amd64"]

    def test_only_package_platforms(self) -> None:
        pkg = PackagePolicy(platforms=["darwin_arm64"])
        op = OperatorPolicy(allow_platforms=[])
        eff = merge_policy(pkg, op)
        assert eff.platforms == ["darwin_arm64"]

    def test_refuse_root_or(self) -> None:
        # True if either is true
        pkg = PackagePolicy(refuse_root=True)
        op = OperatorPolicy(refuse_root=False)
        assert merge_policy(pkg, op).refuse_root is True

        pkg2 = PackagePolicy(refuse_root=False)
        op2 = OperatorPolicy(refuse_root=True)
        assert merge_policy(pkg2, op2).refuse_root is True

        pkg3 = PackagePolicy(refuse_root=False)
        op3 = OperatorPolicy(refuse_root=False)
        assert merge_policy(pkg3, op3).refuse_root is False

    def test_max_age_days_min_wins(self) -> None:
        pkg = PackagePolicy(max_age_days=30)
        op = OperatorPolicy(max_age_days=10)
        assert merge_policy(pkg, op).max_age_days == 10

    def test_max_age_days_one_none(self) -> None:
        pkg = PackagePolicy(max_age_days=30)
        op = OperatorPolicy(max_age_days=None)
        assert merge_policy(pkg, op).max_age_days == 30

        pkg2 = PackagePolicy(max_age_days=None)
        op2 = OperatorPolicy(max_age_days=20)
        assert merge_policy(pkg2, op2).max_age_days == 20

    def test_operator_fields_propagated(self) -> None:
        pkg = PackagePolicy()
        op = OperatorPolicy(require_trusted_key=True, use_os_keychain=True, require_sbom=True)
        eff = merge_policy(pkg, op)
        assert eff.require_trusted_key is True
        assert eff.use_os_keychain is True
        assert eff.require_sbom is True


class TestEnforcePolicy:
    """Kill mutants in enforce_policy: each check branch."""

    def _make_policy(self, **kwargs: Any) -> EffectivePolicy:
        return EffectivePolicy(**kwargs)

    def test_platform_deny(self) -> None:
        policy = self._make_policy(platforms=["imaginary_platform"])
        with pytest.raises(ValueError, match="platform not permitted"):
            enforce_policy(policy, build_timestamp=0, has_sbom=True, key_trusted=True)

    def test_platform_warn(self) -> None:
        enf = EnforcementPolicy(default=EnforcementMode.WARN)
        policy = self._make_policy(platforms=["imaginary_platform"], enforcement=enf)
        warnings = enforce_policy(policy, build_timestamp=0, has_sbom=True, key_trusted=True)
        assert any("platform" in w for w in warnings)

    def test_expired_package_deny(self) -> None:
        enf = EnforcementPolicy(default=EnforcementMode.DENY)
        old_ts = int(datetime.now(UTC).timestamp()) - (100 * 86400)
        policy = self._make_policy(max_age_days=30, enforcement=enf)
        with pytest.raises(ValueError, match="days old"):
            enforce_policy(policy, build_timestamp=old_ts, has_sbom=True, key_trusted=True)

    def test_missing_sbom_deny(self) -> None:
        policy = self._make_policy(require_sbom=True)
        with pytest.raises(ValueError, match="attestation slot"):
            enforce_policy(policy, build_timestamp=0, has_sbom=False, key_trusted=True)

    def test_untrusted_key_deny(self) -> None:
        policy = self._make_policy(require_trusted_key=True)
        with pytest.raises(ValueError, match="trusted signing key"):
            enforce_policy(policy, build_timestamp=0, has_sbom=True, key_trusted=False)

    def test_missing_env_deny(self) -> None:
        policy = self._make_policy(require_env=["SOME_REQUIRED_VAR_12345"])
        with pytest.raises(ValueError, match="SOME_REQUIRED_VAR_12345"):
            enforce_policy(policy, build_timestamp=0, has_sbom=True, key_trusted=True)

    def test_all_checks_pass(self) -> None:
        enf = EnforcementPolicy(default=EnforcementMode.ALLOW)
        policy = self._make_policy(enforcement=enf)
        warnings = enforce_policy(policy, build_timestamp=0, has_sbom=True, key_trusted=True)
        assert warnings == []


class TestApplyEnforcement:
    """Kill mutants in _apply_enforcement: exact branching."""

    def test_deny_raises(self) -> None:
        with pytest.raises(ValueError, match="boom"):
            _apply_enforcement(EnforcementMode.DENY, "boom", [])

    def test_warn_appends(self) -> None:
        warnings: list[str] = []
        _apply_enforcement(EnforcementMode.WARN, "heads up", warnings)
        assert "heads up" in warnings

    def test_allow_is_silent(self) -> None:
        warnings: list[str] = []
        _apply_enforcement(EnforcementMode.ALLOW, "ignored", warnings)
        assert warnings == []


class TestParseEnforcementSection:
    """Kill mutants in _parse_enforcement_section: unknown key, invalid mode."""

    def test_unknown_key_raises(self) -> None:
        with pytest.raises(ValueError, match="unknown enforcement key"):
            _parse_enforcement_section({"bogus_key": "deny"})

    def test_invalid_mode_raises(self) -> None:
        with pytest.raises(ValueError, match="must be one of"):
            _parse_enforcement_section({"default": "crash"})

    def test_valid_section(self) -> None:
        result = _parse_enforcement_section({"default": "warn", "root_execution": "deny"})
        assert result.default == EnforcementMode.WARN
        assert result.root_execution == EnforcementMode.DENY


class TestPolicyValidation:
    """Kill mutants in _validate_operator_policy_value: type checks for bool, int, str, list."""

    def test_bool_validation(self) -> None:
        # Valid
        _validate_operator_policy_value(Path("/f"), "trust", "require_trusted_key", True)
        # Invalid: int is not bool
        with pytest.raises(ValueError, match="must be a boolean"):
            _validate_operator_policy_value(Path("/f"), "trust", "require_trusted_key", 1)

    def test_int_validation(self) -> None:
        _validate_operator_policy_value(Path("/f"), "execution", "max_age_days", 30)
        with pytest.raises(ValueError, match="must be an integer"):
            _validate_operator_policy_value(Path("/f"), "execution", "max_age_days", 30.5)

    def test_str_validation(self) -> None:
        _validate_operator_policy_value(Path("/f"), "enforcement", "default", "deny")
        with pytest.raises(ValueError, match="must be a string"):
            _validate_operator_policy_value(Path("/f"), "enforcement", "default", 42)

    def test_list_validation(self) -> None:
        _validate_operator_policy_value(Path("/f"), "execution", "allow_platforms", ["linux_amd64"])
        with pytest.raises(ValueError, match="must be a list of strings"):
            _validate_operator_policy_value(Path("/f"), "execution", "allow_platforms", "not_a_list")
        with pytest.raises(ValueError, match="must be a list of strings"):
            _validate_operator_policy_value(Path("/f"), "execution", "allow_platforms", [123])


class TestGetCurrentPlatform:
    """Kill mutants in get_current_platform: platform string assembly."""

    def test_returns_string_format(self) -> None:
        result = get_current_platform()
        parts = result.split("_")
        assert len(parts) == 2
        assert parts[1] in ("amd64", "arm64")

    @patch("flavor.config.policy.platform")
    def test_aarch64_maps_to_arm64(self, mock_platform: MagicMock) -> None:
        mock_platform.machine.return_value = "aarch64"
        result = get_current_platform()
        assert result.endswith("_arm64")

    @patch("flavor.config.policy.platform")
    def test_x86_64_maps_to_amd64(self, mock_platform: MagicMock) -> None:
        mock_platform.machine.return_value = "x86_64"
        result = get_current_platform()
        assert result.endswith("_amd64")


class TestParsePackagePolicy:
    """Kill mutants in parse_package_policy."""

    def test_defaults(self) -> None:
        result = parse_package_policy({})
        assert result.platforms == []
        assert result.refuse_root is False
        assert result.max_age_days is None
        assert result.require_env == []

    def test_all_fields(self) -> None:
        raw = {
            "platforms": ["linux_amd64"],
            "refuse_root": True,
            "max_age_days": 90,
            "require_env": ["TOKEN"],
        }
        result = parse_package_policy(raw)
        assert result.platforms == ["linux_amd64"]
        assert result.refuse_root is True
        assert result.max_age_days == 90
        assert result.require_env == ["TOKEN"]


class TestEnforcementPolicyModeFor:
    """Kill mutants in EnforcementPolicy.mode_for: fallback to default."""

    def test_specific_override(self) -> None:
        enf = EnforcementPolicy(default=EnforcementMode.DENY, root_execution=EnforcementMode.WARN)
        assert enf.mode_for("root_execution") == EnforcementMode.WARN

    def test_fallback_to_default(self) -> None:
        enf = EnforcementPolicy(default=EnforcementMode.ALLOW)
        assert enf.mode_for("root_execution") == EnforcementMode.ALLOW

    def test_unknown_check_uses_default(self) -> None:
        enf = EnforcementPolicy(default=EnforcementMode.WARN)
        assert enf.mode_for("nonexistent_check") == EnforcementMode.WARN


# ---------------------------------------------------------------------------
# Spec objects — BuildResult, BuildSpec, PreparedSlot, KeyConfig, BuildOptions
# ---------------------------------------------------------------------------


class TestBuildResultMutants:
    """Kill mutants in BuildResult: has_errors, has_warnings, add_error."""

    def test_has_errors_true(self) -> None:
        r = BuildResult(success=False, errors=["e1"])
        assert r.has_errors() is True

    def test_has_errors_false(self) -> None:
        r = BuildResult(success=True)
        assert r.has_errors() is False

    def test_has_warnings_true(self) -> None:
        r = BuildResult(success=True, warnings=["w1"])
        assert r.has_warnings() is True

    def test_has_warnings_false(self) -> None:
        r = BuildResult(success=True)
        assert r.has_warnings() is False

    def test_add_error_sets_success_false(self) -> None:
        r = BuildResult(success=True)
        r2 = r.add_error("fail")
        assert r2.success is False
        assert "fail" in r2.errors

    def test_add_warning_keeps_success(self) -> None:
        r = BuildResult(success=True)
        r2 = r.add_warning("caution")
        assert r2.success is True
        assert "caution" in r2.warnings


class TestPreparedSlotMutants:
    """Kill mutants in PreparedSlot: get_data_to_write, get_size."""

    def _slot_meta(self) -> Any:
        from flavor.psp.format_2025.slots import SlotMetadata

        return SlotMetadata(index=0, id="t", source="", target="t", size=0, checksum="00")

    def test_get_data_to_write_compressed(self) -> None:
        ps = PreparedSlot(metadata=self._slot_meta(), data=b"raw", compressed_data=b"comp")
        assert ps.get_data_to_write() == b"comp"

    def test_get_data_to_write_raw(self) -> None:
        ps = PreparedSlot(metadata=self._slot_meta(), data=b"raw", compressed_data=None)
        assert ps.get_data_to_write() == b"raw"

    def test_get_size(self) -> None:
        ps = PreparedSlot(metadata=self._slot_meta(), data=b"raw123", compressed_data=b"cp")
        assert ps.get_size() == 2  # len(b"cp")


class TestKeyConfigMutants:
    """Kill mutants in KeyConfig: has_explicit_keys, has_seed, has_path."""

    def test_has_explicit_keys(self) -> None:
        kc = KeyConfig(private_key=b"p", public_key=b"q")
        assert kc.has_explicit_keys() is True

    def test_has_explicit_keys_partial(self) -> None:
        kc = KeyConfig(private_key=b"p", public_key=None)
        assert kc.has_explicit_keys() is False

    def test_has_seed(self) -> None:
        assert KeyConfig(key_seed="s").has_seed() is True
        assert KeyConfig().has_seed() is False

    def test_has_path(self) -> None:
        assert KeyConfig(key_path=Path("/k")).has_path() is True
        assert KeyConfig().has_path() is False


class TestBuildSpecMutants:
    """Kill mutants in BuildSpec: has_required_metadata, with_metadata."""

    def test_has_required_metadata_true(self) -> None:
        spec = BuildSpec(metadata={"name": "test"})
        assert spec.has_required_metadata() is True

    def test_has_required_metadata_nested(self) -> None:
        spec = BuildSpec(metadata={"package": {"name": "test"}})
        assert spec.has_required_metadata() is True

    def test_has_required_metadata_empty(self) -> None:
        spec = BuildSpec(metadata={})
        assert spec.has_required_metadata() is False

    def test_with_metadata_merges(self) -> None:
        spec = BuildSpec(metadata={"a": 1})
        spec2 = spec.with_metadata(b=2)
        assert spec2.metadata == {"a": 1, "b": 2}

    def test_with_slot_appends(self) -> None:
        from flavor.psp.format_2025.slots import SlotMetadata

        slot = SlotMetadata(index=0, id="s", source="", target="t", size=0, checksum="00")
        spec = BuildSpec()
        spec2 = spec.with_slot(slot)
        assert len(spec2.slots) == 1
        assert len(spec.slots) == 0  # Original unchanged


# 🌶️📦🔚
