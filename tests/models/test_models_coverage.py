"""
Additional tests for `models.py` to improve test coverage, focusing on
the FlavorFooter.unpack error handling.
"""

import pytest

from flavor.models import (
    FOOTER_SIZE,
    PSPF_INTERNAL_FOOTER_MAGIC_NUMBER,
    PSPF_VERSION_NUMBER,
    FlavorFooter,
)


@pytest.fixture
def valid_footer_data() -> dict[str, int]:
    """Provides a dictionary of valid data for creating a FlavorFooter."""
    return {
        "uv_binary_offset": 1, "uv_binary_size": 2,
        "python_install_tgz_offset": 3, "python_install_tgz_size": 4,
        "metadata_tgz_offset": 5, "metadata_tgz_size": 6,
        "payload_tgz_offset": 7, "payload_tgz_size": 8,
        "package_signature_offset": 9, "package_signature_size": 10,
        "public_key_pem_offset": 11, "public_key_pem_size": 12,
        "flavor_version": FLAVOR_VERSION_NUMBER,
        "flags": 0,
        "internal_footer_magic": FLAVOR_INTERNAL_FOOTER_MAGIC_NUMBER,
    }


def test_unpack_invalid_buffer_size() -> None:
    """
    Tests that FlavorFooter.unpack raises ValueError for a buffer of the wrong size.
    """
    with pytest.raises(ValueError, match=f"Buffer size 10 != {FOOTER_SIZE}"):
        FlavorFooter.unpack(b"\x00" * 10)


def test_unpack_checksum_mismatch(valid_footer_data: dict[str, int]) -> None:
    """
    Tests that FlavorFooter.unpack raises ValueError for a checksum mismatch.
    """
    footer = FlavorFooter(**valid_footer_data)
    packed_bytes = list(footer.pack())
    packed_bytes[100] = (packed_bytes[100] + 1) % 256
    corrupted_buffer = bytes(packed_bytes)
    with pytest.raises(ValueError, match="Footer checksum mismatch"):
        FlavorFooter.unpack(corrupted_buffer)


def test_unpack_bad_magic_number(valid_footer_data: dict[str, int]) -> None:
    """
    Tests that FlavorFooter.unpack raises ValueError for an invalid magic number.
    """
    valid_footer_data["internal_footer_magic"] = 0xBADCAFE
    footer = FlavorFooter(**valid_footer_data)
    with pytest.raises(ValueError, match="Invalid InternalFooterMagic"):
        FlavorFooter.unpack(footer.pack())


def test_unpack_bad_version(valid_footer_data: dict[str, int]) -> None:
    """
    Tests that FlavorFooter.unpack raises ValueError for an unexpected version.
    """
    valid_footer_data["flavor_version"] = 9999
    footer = FlavorFooter(**valid_footer_data)
    with pytest.raises(ValueError, match="Unexpected PSPF version"):
        FlavorFooter.unpack(footer.pack())


# 📦🍜🧪🪄
