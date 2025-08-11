"""
Additional tests for `packaging/reader.py` to improve test coverage,
focusing on error handling for corrupted or invalid files.
"""

from pathlib import Path
from unittest.mock import patch

import pytest

from flavor.exceptions import VerificationError, InvalidFooterError
from flavor.models import FLAVOR_EOF_MAGIC_STRING
from flavor.packaging.reader import FlavorReader


def test_reader_verify_file_too_small(tmp_path: Path) -> None:
    """
    Tests that FlavorReader.verify raises VerificationError if the file is too small.
    """
    small_file = tmp_path / "small.pspf"
    small_file.write_bytes(b"small")
    reader = FlavorReader(small_file)

    with pytest.raises(VerificationError, match="File is too small"):
        reader.verify()


def test_reader_verify_footer_unpack_fails(tmp_path: Path) -> None:
    """
    Tests that FlavorReader.verify handles exceptions from FlavorFooter.unpack.
    """
    bad_footer_file = tmp_path / "bad_footer.pspf"
    content = (b"\x00" * 108) + FLAVOR_EOF_MAGIC_STRING
    bad_footer_file.write_bytes(content)
    reader = FlavorReader(bad_footer_file)

    with patch(
        "flavor.models.FlavorFooter.unpack",
        side_effect=ValueError("mocked unpack error"),
    ) as mock_unpack:
        with pytest.raises(VerificationError, match="Failed to read or unpack footer: mocked unpack error"):
            reader.verify()
        mock_unpack.assert_called_once()


def test_reader_invalid_eof_magic(tmp_path: Path) -> None:
    """
    Tests that FlavorReader.verify raises InvalidFooterError for bad EOF magic.
    """
    bad_magic_file = tmp_path / "bad_magic.pspf"
    bad_magic_file.write_bytes(b"\x00" * 200)
    reader = FlavorReader(bad_magic_file)

    with pytest.raises(InvalidFooterError, match="Invalid PSPF EOF Magic"):
        reader.verify()


# 📦🍜🧪🪄
