from pathlib import Path

import pytest

from flavor.exceptions import InvalidFooterError, VerificationError
from flavor.packaging.reader import FlavorReader


def test_reader_file_not_found() -> None:
    """
    Tests that verify() raises VerificationError for a non-existent path.
    """
    non_existent_path = Path("/non/existent/file.pspf")
    reader = FlavorReader(non_existent_path)
    with pytest.raises(VerificationError, match="Failed to read or unpack footer"):
        reader.verify()


def test_reader_invalid_eof_magic(tmp_path: Path) -> None:
    """
    Tests that FlavorReader.verify raises InvalidFooterError for a bad EOF magic.
    """
    bad_magic_file = tmp_path / "bad_magic.pspf"
    bad_magic_file.write_bytes(b"\x00" * 200)
    reader = FlavorReader(bad_magic_file)

    with pytest.raises(InvalidFooterError, match="Invalid PSPF EOF Magic"):
        reader.verify()


# 📦🍜🧪🪄
