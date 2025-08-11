"""
Additional tests for `models.py` to improve test coverage, focusing on
the FlavorFooter.unpack error handling.
"""

import pytest

from flavor.models import FOOTER_SIZE, PSPF_VERSION_NUMBER, PSPFV1Footer, PSPF_INTERNAL_FOOTER_MAGIC_NUMBER


@pytest.fixture
def valid_footer_data() -> dict[str, int]:
    """Provides a dictionary of valid data for creating a FlavorFooter."""
    return {
        "uv_offset": 1,
        "uv_size": 2,
        "python_offset": 3,
        "python_size": 4,
        "metadata_offset": 5,
        "metadata_size": 6,
        "payload_offset": 7,
        "payload_size": 8,
        "signature_offset": 9,
        "signature_size": 10,
        "public_key_offset": 11,
        "public_key_size": 12,
        "pspf_version": PSPF_VERSION_NUMBER,
        "flags": 0,
        "internal_footer_magic": PSPF_INTERNAL_FOOTER_MAGIC_NUMBER,
    }


def test_unpack_invalid_buffer_size() -> None:
    """
    Tests that FlavorFooter.unpack raises ValueError for a buffer of the wrong size.
    """
    with pytest.raises(ValueError, match=f"Buffer size 10 != {FOOTER_SIZE}"):
        PSPFV1Footer.unpack(b"\x00" * 10)


def test_unpack_checksum_mismatch(valid_footer_data: dict[str, int]) -> None:
    """
    Tests that FlavorFooter.unpack raises ValueError for a checksum mismatch.
    """
    footer = PSPFV1Footer(**valid_footer_data)
    packed_bytes = list(footer.pack())
    packed_bytes[100] = (packed_bytes[100] + 1) % 256
    corrupted_buffer = bytes(packed_bytes)
    with pytest.raises(ValueError, match="Footer checksum mismatch"):
        PSPFV1Footer.unpack(corrupted_buffer)


def test_unpack_bad_magic_number(valid_footer_data: dict[str, int]) -> None:
    """
    Tests that FlavorFooter.unpack raises ValueError for an invalid magic number.
    """
    valid_footer_data["internal_footer_magic"] = 0xBADCAFE
    footer = PSPFV1Footer(**valid_footer_data)
    with pytest.raises(ValueError, match="Invalid InternalFooterMagic"):
        PSPFV1Footer.unpack(footer.pack())


def test_unpack_bad_version(valid_footer_data: dict[str, int]) -> None:
    """
    Tests that FlavorFooter.unpack raises ValueError for an unexpected version.
    """
    valid_footer_data["pspf_version"] = 9999
    footer = PSPFV1Footer(**valid_footer_data)
    with pytest.raises(ValueError, match="Unexpected PSPF version"):
        PSPFV1Footer.unpack(footer.pack())


# 📦🍜🧪🪄
