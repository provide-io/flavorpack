#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""Tests for flavor.psp.format_2025.spec — BuildSpec, BuildOptions, KeyConfig, PreparedSlot."""

from __future__ import annotations

from pathlib import Path

import pytest

from flavor.psp.format_2025.slots import SlotMetadata
from flavor.psp.format_2025.spec import BuildOptions, BuildResult, BuildSpec, KeyConfig, PreparedSlot


@pytest.mark.unit
class TestKeyConfig:
    """Tests for KeyConfig."""

    def test_default_no_keys(self) -> None:
        """Default KeyConfig has no keys."""
        kc = KeyConfig()
        assert not kc.has_explicit_keys()
        assert not kc.has_seed()
        assert not kc.has_path()

    def test_explicit_keys(self) -> None:
        """KeyConfig with both keys reports has_explicit_keys."""
        kc = KeyConfig(private_key=b"\x01" * 32, public_key=b"\x02" * 32)
        assert kc.has_explicit_keys()

    def test_only_private_not_explicit(self) -> None:
        """Only private key is not considered explicit."""
        kc = KeyConfig(private_key=b"\x01" * 32)
        assert not kc.has_explicit_keys()

    def test_only_public_not_explicit(self) -> None:
        """Only public key is not considered explicit."""
        kc = KeyConfig(public_key=b"\x02" * 32)
        assert not kc.has_explicit_keys()

    def test_has_seed(self) -> None:
        """KeyConfig with seed reports has_seed."""
        kc = KeyConfig(key_seed="my-seed")
        assert kc.has_seed()

    def test_has_path(self, tmp_path: Path) -> None:
        """KeyConfig with path reports has_path."""
        kc = KeyConfig(key_path=tmp_path)
        assert kc.has_path()

    def test_is_frozen(self) -> None:
        """KeyConfig is immutable."""
        kc = KeyConfig(key_seed="seed")
        with pytest.raises(AttributeError):
            kc.key_seed = "other"  # type: ignore[misc]


@pytest.mark.unit
class TestBuildOptions:
    """Tests for BuildOptions."""

    def test_defaults(self) -> None:
        """Default BuildOptions has expected values."""
        opts = BuildOptions()
        assert opts.compression == "gzip"
        assert opts.compression_level == 6
        assert opts.enable_mmap is True

    @pytest.mark.parametrize("compression", ["none", "gzip", "zstd", "brotli"])
    def test_valid_compressions(self, compression: str) -> None:
        """Valid compression values are accepted."""
        opts = BuildOptions(compression=compression)
        assert opts.compression == compression

    def test_invalid_compression_raises(self) -> None:
        """Invalid compression raises ValueError."""
        with pytest.raises((ValueError, Exception)):
            BuildOptions(compression="lzma")

    def test_with_compression(self) -> None:
        """with_compression returns new BuildOptions."""
        opts = BuildOptions()
        new_opts = opts.with_compression("zstd", level=3)
        assert new_opts.compression == "zstd"
        assert new_opts.compression_level == 3
        # Original unchanged
        assert opts.compression == "gzip"

    def test_with_compression_no_level(self) -> None:
        """with_compression without level keeps existing level."""
        opts = BuildOptions(compression_level=9)
        new_opts = opts.with_compression("none")
        assert new_opts.compression_level == 9

    def test_is_frozen(self) -> None:
        """BuildOptions is immutable."""
        opts = BuildOptions()
        with pytest.raises(AttributeError):
            opts.compression = "none"  # type: ignore[misc]


@pytest.mark.unit
class TestBuildSpec:
    """Tests for BuildSpec."""

    def test_defaults(self) -> None:
        """Default BuildSpec is empty."""
        spec = BuildSpec()
        assert spec.metadata == {}
        assert spec.slots == []
        assert not spec.has_required_metadata()

    def test_with_metadata(self) -> None:
        """with_metadata merges metadata."""
        spec = BuildSpec()
        spec2 = spec.with_metadata(name="test", version="1.0")
        assert spec2.metadata["name"] == "test"
        assert spec2.metadata["version"] == "1.0"
        # Original unchanged
        assert spec.metadata == {}

    def test_with_metadata_merges(self) -> None:
        """with_metadata merges with existing metadata."""
        spec = BuildSpec(metadata={"a": 1})
        spec2 = spec.with_metadata(b=2)
        assert spec2.metadata == {"a": 1, "b": 2}

    def test_has_required_metadata_with_name(self) -> None:
        """has_required_metadata returns True when name present."""
        spec = BuildSpec(metadata={"name": "mypkg"})
        assert spec.has_required_metadata()

    def test_has_required_metadata_nested_package(self) -> None:
        """has_required_metadata works with nested package dict."""
        spec = BuildSpec(metadata={"package": {"name": "mypkg"}})
        assert spec.has_required_metadata()

    def test_has_required_metadata_false_no_name(self) -> None:
        """has_required_metadata returns False without name."""
        spec = BuildSpec(metadata={"version": "1.0"})
        assert not spec.has_required_metadata()

    def test_with_slot(self) -> None:
        """with_slot appends a slot."""
        slot = SlotMetadata(index=0, id="s", source="/tmp/x", target="x", size=0, checksum="abc")
        spec = BuildSpec().with_slot(slot)
        assert len(spec.slots) == 1

    def test_with_slots(self) -> None:
        """with_slots appends multiple slots."""
        slots = [
            SlotMetadata(index=i, id=f"s{i}", source="/tmp/x", target="x", size=0, checksum="abc")
            for i in range(3)
        ]
        spec = BuildSpec().with_slots(*slots)
        assert len(spec.slots) == 3

    def test_replace_slots(self) -> None:
        """replace_slots replaces existing slots."""
        slot = SlotMetadata(index=0, id="s", source="/tmp/x", target="x", size=0, checksum="abc")
        spec = BuildSpec().with_slot(slot)
        spec2 = spec.replace_slots([])
        assert spec2.slots == []

    def test_with_keys(self) -> None:
        """with_keys returns new spec with updated keys."""
        kc = KeyConfig(key_seed="myseed")
        spec = BuildSpec().with_keys(kc)
        assert spec.keys.key_seed == "myseed"

    def test_with_options(self) -> None:
        """with_options returns new spec with updated options."""
        opts = BuildOptions(compression="zstd")
        spec = BuildSpec().with_options(opts)
        assert spec.options.compression == "zstd"

    def test_is_frozen(self) -> None:
        """BuildSpec is immutable."""
        spec = BuildSpec()
        with pytest.raises(AttributeError):
            spec.metadata = {"new": "value"}  # type: ignore[misc]


@pytest.mark.unit
class TestBuildResult:
    """Tests for BuildResult."""

    def test_success_result(self) -> None:
        """Successful result has no errors."""
        result = BuildResult(success=True)
        assert not result.has_errors()
        assert not result.has_warnings()

    def test_add_error(self) -> None:
        """add_error appends error and sets success=False."""
        result = BuildResult(success=True)
        result2 = result.add_error("something went wrong")
        assert result2.has_errors()
        assert not result2.success
        # Original unchanged
        assert not result.has_errors()

    def test_add_warning(self) -> None:
        """add_warning appends warning, keeps success unchanged."""
        result = BuildResult(success=True)
        result2 = result.add_warning("heads up")
        assert result2.has_warnings()
        assert result2.success  # Still successful

    def test_with_metadata(self) -> None:
        """with_metadata merges metadata."""
        result = BuildResult(success=True)
        result2 = result.with_metadata(key="value")
        assert result2.metadata["key"] == "value"

    def test_is_frozen(self) -> None:
        """BuildResult is immutable."""
        result = BuildResult(success=True)
        with pytest.raises(AttributeError):
            result.success = False  # type: ignore[misc]


@pytest.mark.unit
class TestPreparedSlot:
    """Tests for PreparedSlot."""

    def _make_slot_metadata(self) -> SlotMetadata:
        return SlotMetadata(index=0, id="test", source="/tmp/x", target="test.txt", size=10, checksum="abcdef")

    def test_basic_construction(self) -> None:
        """PreparedSlot can be constructed with required fields."""
        meta = self._make_slot_metadata()
        ps = PreparedSlot(metadata=meta, data=b"hello world")
        assert ps.data == b"hello world"
        assert ps.compressed_data is None
        assert ps.operations == 0
        assert ps.offset is None

    def test_get_data_to_write_uncompressed(self) -> None:
        """get_data_to_write returns raw data when no compressed data."""
        meta = self._make_slot_metadata()
        ps = PreparedSlot(metadata=meta, data=b"raw")
        assert ps.get_data_to_write() == b"raw"

    def test_get_data_to_write_compressed(self) -> None:
        """get_data_to_write returns compressed data when available."""
        meta = self._make_slot_metadata()
        ps = PreparedSlot(metadata=meta, data=b"raw", compressed_data=b"compressed")
        assert ps.get_data_to_write() == b"compressed"

    def test_get_size(self) -> None:
        """get_size returns length of data to write."""
        meta = self._make_slot_metadata()
        ps = PreparedSlot(metadata=meta, data=b"hello world")
        assert ps.get_size() == 11

    def test_get_size_compressed(self) -> None:
        """get_size returns length of compressed data when available."""
        meta = self._make_slot_metadata()
        ps = PreparedSlot(metadata=meta, data=b"hello world", compressed_data=b"cmp")
        assert ps.get_size() == 3

    def test_with_codec(self) -> None:
        """with_codec returns new PreparedSlot with codec applied."""
        meta = self._make_slot_metadata()
        ps = PreparedSlot(metadata=meta, data=b"raw")
        ps2 = ps.with_codec(b"compressed", operations=0x10)
        assert ps2.compressed_data == b"compressed"
        assert ps2.operations == 0x10
        # Original unchanged
        assert ps.compressed_data is None

    def test_with_offset(self) -> None:
        """with_offset returns new PreparedSlot with offset set."""
        meta = self._make_slot_metadata()
        ps = PreparedSlot(metadata=meta, data=b"raw")
        ps2 = ps.with_offset(1024)
        assert ps2.offset == 1024
        # Original unchanged
        assert ps.offset is None

    def test_is_frozen(self) -> None:
        """PreparedSlot is immutable."""
        meta = self._make_slot_metadata()
        ps = PreparedSlot(metadata=meta, data=b"raw")
        with pytest.raises(AttributeError):
            ps.data = b"other"  # type: ignore[misc]


# 🌶️📦🔚
