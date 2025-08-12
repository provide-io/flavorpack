"""Tests for PSPF v1.0 footer."""

import pytest

from flavor.models import (
    PSPF_VERSION_NUMBER,
    PSPFV1Footer,
)


class TestPSPFV1Footer:
    """Test PSPF v1.0 footer structure."""

    def test_footer_size(self) -> None:
        """Footer should be exactly 120 bytes."""
        footer = PSPFV1Footer(
            uv_offset=0,
            uv_size=0,
            python_offset=0,
            python_size=0,
            metadata_offset=0,
            metadata_size=0,
            payload_offset=0,
            payload_size=0,
            signature_offset=0,
            signature_size=0,
            public_key_offset=0,
            public_key_size=0,
        )
        assert len(footer.pack()) == 120

    def test_simplified_field_names(self) -> None:
        """Test that simplified field names work correctly."""
        footer = PSPFV1Footer(
            uv_offset=100,
            uv_size=200,
            python_offset=300,
            python_size=400,
            metadata_offset=500,
            metadata_size=600,
            payload_offset=700,
            payload_size=800,
            signature_offset=900,
            signature_size=1000,
            public_key_offset=1100,
            public_key_size=1200,
        )

        # Check fields are set correctly
        assert footer.uv_offset == 100
        assert footer.python_size == 400
        assert footer.metadata_offset == 500
        assert footer.payload_size == 800
        assert footer.signature_offset == 900
        assert footer.public_key_size == 1200

    def test_pack_unpack_roundtrip(self) -> None:
        """Test packing and unpacking preserves data."""
        original = PSPFV1Footer(
            uv_offset=1000,
            uv_size=2000,
            python_offset=3000,
            python_size=4000,
            metadata_offset=5000,
            metadata_size=6000,
            payload_offset=7000,
            payload_size=8000,
            signature_offset=9000,
            signature_size=10000,
            public_key_offset=11000,
            public_key_size=12000,
            flags=0b0000000000000011,  # UV compressed, Python included
        )

        packed = original.pack()
        unpacked = PSPFV1Footer.unpack(packed)

        assert unpacked.uv_offset == original.uv_offset
        assert unpacked.python_size == original.python_size
        assert unpacked.payload_offset == original.payload_offset
        assert unpacked.flags == original.flags
        assert unpacked.pspf_version == PSPF_VERSION_NUMBER

    def test_flags_interpretation(self) -> None:
        """Test flag bit interpretation."""
        # UV compressed, Python included, ECDSA sig, prod mode
        flags = 0b0000000000000011

        assert flags & 0x0001  # UV compressed
        assert flags & 0x0002  # Python included
        assert not (flags & 0x0004)  # ECDSA (not RSA)
        assert not (flags & 0x0008)  # Production (not dev)

        # Dev mode, platform specific, tar.zst format
        flags = 0b0000000000111000

        assert not (flags & 0x0001)  # UV not compressed
        assert not (flags & 0x0002)  # No Python
        assert flags & 0x0008  # Dev mode
        assert flags & 0x0010  # Platform specific
        assert (flags >> 5) & 0x07 == 1  # tar.zst format

    def test_invalid_magic_rejected(self) -> None:
        """Test that invalid magic number is rejected."""
        footer = PSPFV1Footer(
            uv_offset=0,
            uv_size=0,
            python_offset=0,
            python_size=0,
            metadata_offset=0,
            metadata_size=0,
            payload_offset=0,
            payload_size=0,
            signature_offset=0,
            signature_size=0,
            public_key_offset=0,
            public_key_size=0,
            magic=0xDEADBEEF,  # Invalid magic
        )

        packed = footer.pack()
        with pytest.raises(ValueError, match="Invalid magic"):
            PSPFV1Footer.unpack(packed)
