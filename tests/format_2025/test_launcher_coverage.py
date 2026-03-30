#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""Tests for PSPFLauncher coverage — decompression, checksum, permissions, integrity."""

from __future__ import annotations

import gzip
import hashlib
import io
from pathlib import Path
import tarfile
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from flavor.psp.format_2025.launcher import PSPFLauncher

# ---------------------------------------------------------------------------
# Helpers to build minimal fake slot tables
# ---------------------------------------------------------------------------


def _make_launcher(bundle_path: Path) -> PSPFLauncher:
    """Create a PSPFLauncher instance bypassing the full init chain."""

    with (
        patch("flavor.psp.format_2025.launcher.ensure_dir"),
        patch("flavor.psp.format_2025.launcher.WorkEnvManager"),
    ):
        launcher = PSPFLauncher.__new__(PSPFLauncher)
        object.__setattr__(launcher, "bundle_path", bundle_path)
        launcher.cache_dir = bundle_path.parent
        launcher._workenv_manager = MagicMock()
    return launcher


def _make_raw_slot_entry(
    offset: int = 0,
    size: int = 0,
    checksum: int = 0,
    operations: int = 0,
    purpose: int = 0,
    lifecycle: int = 0,
) -> dict[str, int]:
    return {
        "index": 0,
        "offset": offset,
        "size": size,
        "checksum": checksum,
        "operations": operations,
        "purpose": purpose,
        "lifecycle": lifecycle,
    }


@pytest.mark.unit
class TestExtractSlotGzip:
    """Test extract_slot with gzip-compressed data (operations=0x10)."""

    def test_gzip_decompression(self, tmp_path: Path) -> None:

        raw = b"Hello from gzip"
        compressed = gzip.compress(raw)

        bundle = tmp_path / "test.psp"
        bundle.write_bytes(compressed)

        launcher = _make_launcher(bundle)

        slot_entry = _make_raw_slot_entry(offset=0, size=len(compressed), operations=0x10)

        metadata = {"slots": [{"target": "hello.txt"}]}
        with (
            patch.object(launcher, "read_slot_table", return_value=[slot_entry]),
            patch.object(launcher, "read_metadata", return_value=metadata),
            patch("flavor.psp.format_2025.launcher.atomic_write") as mock_write,
            patch("flavor.psp.format_2025.launcher.ensure_parent_dir"),
        ):
            object.__setattr__(launcher, "_apply_slot_permissions", MagicMock())
            launcher.extract_slot(0, tmp_path)

        written_data = mock_write.call_args[0][1]
        assert written_data == raw


@pytest.mark.unit
class TestExtractSlotTarGz:
    """Test extract_slot with tar.gz data (operations=0x1001)."""

    def test_targz_extraction(self, tmp_path: Path) -> None:
        # Build an in-memory tar.gz
        buf = io.BytesIO()
        content = b"hello tarball"
        with tarfile.open(fileobj=buf, mode="w:gz") as tf:
            info = tarfile.TarInfo(name="file.txt")
            info.size = len(content)
            tf.addfile(info, io.BytesIO(content))
        buf.seek(0)
        tgz_data = buf.read()

        bundle = tmp_path / "test.psp"
        bundle.write_bytes(tgz_data)

        launcher = _make_launcher(bundle)

        slot_entry = _make_raw_slot_entry(offset=0, size=len(tgz_data), operations=0x1001)
        metadata: dict[str, Any] = {"slots": []}
        workenv = tmp_path / "workenv"
        workenv.mkdir()

        with (
            patch.object(launcher, "read_slot_table", return_value=[slot_entry]),
            patch.object(launcher, "read_metadata", return_value=metadata),
        ):
            launcher.extract_slot(0, workenv)

        assert (workenv / "file.txt").exists()


@pytest.mark.unit
class TestExtractSlotUnsupportedOps:
    """Test extract_slot raises ValueError for unsupported operations."""

    def test_unsupported_operations_raises(self, tmp_path: Path) -> None:
        bundle = tmp_path / "test.psp"
        bundle.write_bytes(b"garbage data")

        launcher = _make_launcher(bundle)

        slot_entry = _make_raw_slot_entry(offset=0, size=12, operations=0xDEAD)
        metadata: dict[str, Any] = {"slots": []}

        with (
            patch.object(launcher, "read_slot_table", return_value=[slot_entry]),
            patch.object(launcher, "read_metadata", return_value=metadata),
            pytest.raises(ValueError, match="Unsupported operations"),
        ):
            launcher.extract_slot(0, tmp_path)


@pytest.mark.unit
class TestExtractSlotInvalidIndex:
    """Test extract_slot raises ValueError for out-of-range slot index."""

    def test_negative_index_raises(self, tmp_path: Path) -> None:
        bundle = tmp_path / "test.psp"
        bundle.write_bytes(b"data")

        launcher = _make_launcher(bundle)

        with (
            patch.object(launcher, "read_slot_table", return_value=[]),
            pytest.raises(ValueError, match="Invalid slot index"),
        ):
            launcher.extract_slot(-1, tmp_path)

    def test_index_out_of_range_raises(self, tmp_path: Path) -> None:
        bundle = tmp_path / "test.psp"
        bundle.write_bytes(b"data")

        launcher = _make_launcher(bundle)

        slot_entry = _make_raw_slot_entry()
        with (
            patch.object(launcher, "read_slot_table", return_value=[slot_entry]),
            pytest.raises(ValueError, match="Invalid slot index"),
        ):
            launcher.extract_slot(5, tmp_path)


@pytest.mark.unit
class TestExtractSlotChecksum:
    """Test checksum verification paths."""

    def test_checksum_match_succeeds(self, tmp_path: Path) -> None:
        data = b"payload data"
        bundle = tmp_path / "test.psp"
        bundle.write_bytes(data)

        hash_bytes = hashlib.sha256(data).digest()[:8]
        checksum = int.from_bytes(hash_bytes, byteorder="little")

        launcher = _make_launcher(bundle)
        slot_entry = _make_raw_slot_entry(offset=0, size=len(data), checksum=checksum, operations=0)
        metadata: dict[str, Any] = {"slots": []}

        with (
            patch.object(launcher, "read_slot_table", return_value=[slot_entry]),
            patch.object(launcher, "read_metadata", return_value=metadata),
            patch("flavor.psp.format_2025.launcher.atomic_write"),
            patch("flavor.psp.format_2025.launcher.ensure_parent_dir"),
        ):
            object.__setattr__(launcher, "_apply_slot_permissions", MagicMock())
            # Should not raise
            launcher.extract_slot(0, tmp_path, verify_checksum=True)

    def test_checksum_mismatch_raises(self, tmp_path: Path) -> None:
        data = b"payload data"
        bundle = tmp_path / "test.psp"
        bundle.write_bytes(data)

        launcher = _make_launcher(bundle)
        slot_entry = _make_raw_slot_entry(offset=0, size=len(data), checksum=0xDEADBEEFCAFEBABE, operations=0)
        metadata: dict[str, Any] = {"slots": []}

        with (
            patch.object(launcher, "read_slot_table", return_value=[slot_entry]),
            patch.object(launcher, "read_metadata", return_value=metadata),
            pytest.raises(ValueError, match="Checksum mismatch"),
        ):
            launcher.extract_slot(0, tmp_path, verify_checksum=True)


@pytest.mark.unit
class TestApplySlotPermissions:
    """Test _apply_slot_permissions."""

    def test_valid_permissions_applied(self, tmp_path: Path) -> None:

        f = tmp_path / "exec.sh"
        f.write_text("#!/bin/sh\necho hi")

        launcher = _make_launcher(tmp_path / "bundle.psp")
        launcher._apply_slot_permissions(f, {"permissions": "755"})
        # Just verify no exception

    def test_no_permissions_key_is_noop(self, tmp_path: Path) -> None:
        f = tmp_path / "file.txt"
        f.write_text("data")

        launcher = _make_launcher(tmp_path / "bundle.psp")
        launcher._apply_slot_permissions(f, {})  # No exception

    def test_invalid_permissions_logs_warning(self, tmp_path: Path) -> None:
        f = tmp_path / "file.txt"
        f.write_text("data")

        launcher = _make_launcher(tmp_path / "bundle.psp")
        # "invalid" is not valid octal — should log warning, not raise
        launcher._apply_slot_permissions(f, {"permissions": "not_octal"})
        # No exception raised


@pytest.mark.unit
class TestNormalizeSlotTarget:
    """Test slot target normalization and rejection of unsafe paths."""

    def test_workenv_placeholder_is_preserved(self, tmp_path: Path) -> None:
        launcher = _make_launcher(tmp_path / "bundle.psp")
        assert launcher._normalize_slot_target("{workenv}") == "{workenv}"

    def test_workenv_prefix_is_stripped(self, tmp_path: Path) -> None:
        launcher = _make_launcher(tmp_path / "bundle.psp")
        assert launcher._normalize_slot_target("{workenv}/bin/tool") == "bin/tool"

    @pytest.mark.parametrize(
        "slot_target",
        [
            "/tmp/evil",
            "../../etc/passwd",
            "{workenv}/../../etc/passwd",
            "..\\..\\windows\\system32",
            "",
        ],
    )
    def test_unsafe_targets_raise_value_error(self, tmp_path: Path, slot_target: str) -> None:
        launcher = _make_launcher(tmp_path / "bundle.psp")
        with pytest.raises(ValueError, match="target"):
            launcher._normalize_slot_target(slot_target)


@pytest.mark.unit
class TestExtractSlotPathValidation:
    """Test extraction rejects metadata targets that escape the workenv."""

    def test_extract_slot_rejects_unsafe_target(self, tmp_path: Path) -> None:
        bundle = tmp_path / "test.psp"
        bundle.write_bytes(b"payload")

        launcher = _make_launcher(bundle)
        slot_entry = _make_raw_slot_entry(offset=0, size=7, operations=0)
        metadata = {"slots": [{"target": "../../etc/passwd"}]}

        with (
            patch.object(launcher, "read_slot_table", return_value=[slot_entry]),
            patch.object(launcher, "read_metadata", return_value=metadata),
            pytest.raises(ValueError, match="target"),
        ):
            launcher.extract_slot(0, tmp_path)


@pytest.mark.unit
class TestVerifyIntegrity:
    """Test verify_integrity()."""

    def test_empty_bundle_path_returns_invalid(self, tmp_path: Path) -> None:

        launcher = _make_launcher(tmp_path / "bundle.psp")
        object.__setattr__(launcher, "bundle_path", "")

        result = launcher.verify_integrity()
        assert result["valid"] is False
        assert result["tamper_detected"] is True

    def test_delegates_to_verify_package_integrity(self, tmp_path: Path) -> None:
        bundle = tmp_path / "bundle.psp"
        bundle.write_bytes(b"fake")

        launcher = _make_launcher(bundle)

        fake_result = {"valid": True, "signature_valid": True, "tamper_detected": False}
        with patch("flavor.psp.security.verify_package_integrity", return_value=fake_result):
            result = launcher.verify_integrity()

        assert result["valid"] is True
        assert result["tamper_detected"] is False
