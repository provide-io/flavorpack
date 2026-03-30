"""Cross-language parity tests for PSPF extraction safety.

Tests the Python implementation of extraction-safety behaviours that must
be consistent across Python, Go and Rust launchers.
"""

from __future__ import annotations

import io
from pathlib import Path
import tarfile

import pytest

from flavor.psp.format_2025.targets import normalize_workenv_target


# ---------------------------------------------------------------------------
# Rejects .. traversal in slot targets
# ---------------------------------------------------------------------------
@pytest.mark.parity
@pytest.mark.parity_category("Extraction Safety")
@pytest.mark.parity_go("PASS")
@pytest.mark.parity_rust("PASS")
def test_rejects_dot_dot_traversal_in_slot_targets() -> None:
    """normalize_workenv_target rejects paths containing '..' components."""
    with pytest.raises(ValueError, match="path traversal"):
        normalize_workenv_target("../etc/passwd")

    with pytest.raises(ValueError, match="path traversal"):
        normalize_workenv_target("subdir/../../escape")

    with pytest.raises(ValueError, match="path traversal"):
        normalize_workenv_target("{workenv}/../outside")


# ---------------------------------------------------------------------------
# Rejects absolute paths
# ---------------------------------------------------------------------------
@pytest.mark.parity
@pytest.mark.parity_category("Extraction Safety")
@pytest.mark.parity_go("PASS")
@pytest.mark.parity_rust("PASS")
def test_rejects_absolute_paths() -> None:
    """normalize_workenv_target rejects absolute Unix paths."""
    with pytest.raises(ValueError, match="absolute paths"):
        normalize_workenv_target("/etc/passwd")

    with pytest.raises(ValueError, match="absolute paths"):
        normalize_workenv_target("/tmp/evil")


# ---------------------------------------------------------------------------
# Rejects Windows drive paths
# ---------------------------------------------------------------------------
@pytest.mark.parity
@pytest.mark.parity_category("Extraction Safety")
@pytest.mark.parity_go("PASS")
@pytest.mark.parity_rust("PASS")
def test_rejects_windows_drive_paths() -> None:
    """normalize_workenv_target rejects Windows drive-letter paths."""
    with pytest.raises(ValueError, match="absolute paths"):
        normalize_workenv_target("C:\\Windows\\System32")

    with pytest.raises(ValueError, match="absolute paths"):
        normalize_workenv_target("D:/data/file.txt")


# ---------------------------------------------------------------------------
# Rejects symlinks in tar (filter=data)
# ---------------------------------------------------------------------------
@pytest.mark.parity
@pytest.mark.parity_category("Extraction Safety")
@pytest.mark.parity_go("PASS")
@pytest.mark.parity_rust("PASS")
def test_rejects_symlinks_in_tar(tmp_path: Path) -> None:
    """Python tar extraction uses filter='data' which blocks symlinks."""
    # Build a tar archive containing a symlink
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        info = tarfile.TarInfo(name="evil_link")
        info.type = tarfile.SYMTYPE
        info.linkname = "/etc/passwd"
        tar.addfile(info)
    buf.seek(0)

    extract_dir = tmp_path / "extract"
    extract_dir.mkdir()

    with (
        tarfile.open(fileobj=buf, mode="r:gz") as tar,
        pytest.raises((tarfile.LinkOutsideDestinationError, tarfile.AbsolutePathError, Exception)),
    ):
        tar.extractall(path=extract_dir, filter="data")


# ---------------------------------------------------------------------------
# Validates disk space before extraction
# ---------------------------------------------------------------------------
@pytest.mark.parity
@pytest.mark.parity_category("Extraction Safety")
@pytest.mark.parity_go("PASS")
@pytest.mark.parity_rust("PASS")
def test_validates_disk_space_before_extraction(tmp_path: Path) -> None:
    """Python checks available disk space before attempting extraction."""
    from provide.foundation.file import check_disk_space

    # Requesting a reasonable amount of space should succeed
    check_disk_space(tmp_path, 1024)

    # Requesting an impossibly large amount should raise
    impossibly_large = 2**62  # ~4 exabytes
    with pytest.raises(OSError):
        check_disk_space(tmp_path, impossibly_large)
