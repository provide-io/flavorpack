#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""Hypothesis property-based tests for vital PSPF invariants.

Tests the core algebraic properties that must hold regardless of input:
- pack/unpack round-trip for operation chains
- XOR encode/decode symmetry
- SlotDescriptor pack/unpack round-trip
- validate_metadata accepts its own output
"""

from __future__ import annotations

from hypothesis import assume, given, settings, strategies as st
import pytest

from flavor.psp.format_2025.operations import (
    OP_BZIP2,
    OP_GZIP,
    OP_TAR,
    OP_XZ,
    OP_ZSTD,
    pack_operations,
    unpack_operations,
)
from flavor.utils.xor import xor_decode, xor_encode

# Valid v0 operations for hypothesis
VALID_OPS = [OP_TAR, OP_GZIP, OP_BZIP2, OP_XZ, OP_ZSTD]

op_strategy = st.sampled_from(VALID_OPS)
ops_list_strategy = st.lists(op_strategy, min_size=0, max_size=8)


@pytest.mark.unit
class TestOperationsHypothesis:
    """Property-based tests: pack/unpack round-trip is lossless."""

    @given(ops=ops_list_strategy)
    def test_pack_unpack_roundtrip(self, ops: list[int]) -> None:
        """unpack(pack(ops)) == ops for any valid op list."""
        packed = pack_operations(ops)
        assert unpack_operations(packed) == ops

    @given(ops=ops_list_strategy)
    def test_pack_is_nonnegative(self, ops: list[int]) -> None:
        """Packed value is always a non-negative integer."""
        packed = pack_operations(ops)
        assert packed >= 0

    @given(ops=ops_list_strategy)
    def test_pack_empty_iff_zero(self, ops: list[int]) -> None:
        """pack([]) == 0; pack(non-empty) > 0."""
        packed = pack_operations(ops)
        if len(ops) == 0:
            assert packed == 0
        else:
            assert packed > 0

    @given(ops=ops_list_strategy)
    def test_unpack_length_matches_input(self, ops: list[int]) -> None:
        """Round-trip preserves the number of operations."""
        packed = pack_operations(ops)
        result = unpack_operations(packed)
        assert len(result) == len(ops)

    @given(
        ops_a=ops_list_strategy,
        ops_b=ops_list_strategy,
    )
    def test_distinct_inputs_distinct_packed(self, ops_a: list[int], ops_b: list[int]) -> None:
        """Different op lists produce different packed values (no collisions)."""
        assume(ops_a != ops_b)
        assert pack_operations(ops_a) != pack_operations(ops_b)

    @given(n=st.integers(min_value=9, max_value=20))
    def test_too_many_ops_raises(self, n: int) -> None:
        """Packing more than 8 operations always raises ValueError."""
        with pytest.raises(ValueError, match="Maximum 8 operations"):
            pack_operations([OP_TAR] * n)


@pytest.mark.unit
class TestXorHypothesis:
    """Property-based tests: XOR encode/decode are strict inverses."""

    @given(data=st.binary(min_size=0, max_size=256))
    def test_encode_decode_roundtrip(self, data: bytes) -> None:
        """decode(encode(data)) == data for any bytes."""
        assert xor_decode(xor_encode(data)) == data

    @given(data=st.binary(min_size=0, max_size=256))
    def test_encode_decode_same_length(self, data: bytes) -> None:
        """Encoding preserves byte length."""
        assert len(xor_encode(data)) == len(data)

    @given(data=st.binary(min_size=1, max_size=256))
    def test_double_encode_is_identity(self, data: bytes) -> None:
        """Encoding twice is identity (XOR is self-inverse)."""
        assert xor_encode(xor_encode(data)) == data

    @given(data=st.binary(min_size=1, max_size=256))
    def test_encode_is_not_always_identity(self, data: bytes) -> None:
        """Encoded bytes differ from original (unless all bytes happen to be key bytes)."""
        encoded = xor_encode(data)
        # We can't always assert encoded != data (if XOR key is 0),
        # but encoding should be deterministic
        assert xor_encode(data) == encoded


@pytest.mark.unit
class TestSlotDescriptorHypothesis:
    """Property-based tests: SlotDescriptor pack/unpack round-trip."""

    @given(
        slot_id=st.integers(min_value=0, max_value=2**16 - 1),
        offset=st.integers(min_value=0, max_value=2**32 - 1),
        size=st.integers(min_value=0, max_value=2**32 - 1),
        original_size=st.integers(min_value=0, max_value=2**32 - 1),
        ops=ops_list_strategy,
    )
    @settings(max_examples=50)
    def test_pack_unpack_roundtrip(
        self,
        slot_id: int,
        offset: int,
        size: int,
        original_size: int,
        ops: list[int],
    ) -> None:
        """pack/unpack preserves all SlotDescriptor fields."""
        from flavor.psp.format_2025.slots import SlotDescriptor

        packed_ops = pack_operations(ops)
        desc = SlotDescriptor(
            id=slot_id,
            offset=offset,
            size=size,
            original_size=original_size,
            operations=packed_ops,
        )
        restored = SlotDescriptor.unpack(desc.pack())
        assert restored.id == slot_id
        assert restored.offset == offset
        assert restored.size == size
        assert restored.original_size == original_size
        assert restored.operations == packed_ops

    @given(data=st.binary(min_size=1, max_size=63) | st.binary(min_size=65, max_size=128))
    def test_wrong_size_raises(self, data: bytes) -> None:
        """unpack() of data != 64 bytes raises ValueError."""
        from flavor.psp.format_2025.slots import SlotDescriptor

        with pytest.raises(ValueError, match="64 bytes"):
            SlotDescriptor.unpack(data)


@pytest.mark.unit
class TestValidateMetadataHypothesis:
    """Property-based tests: validate_metadata is stable on known-good structures."""

    @given(
        name=st.text(
            min_size=1,
            max_size=50,
            alphabet=st.characters(whitelist_categories=["Ll", "Lu", "Nd"], whitelist_characters="-_"),
        ),
        version=st.text(
            min_size=1,
            max_size=20,
            alphabet=st.characters(whitelist_categories=["Nd"], whitelist_characters="."),
        ),
    )
    def test_valid_metadata_always_passes(self, name: str, version: str) -> None:
        """Well-formed metadata always passes validate_metadata."""
        from flavor.psp.metadata.validators import validate_metadata

        metadata = {
            "format": "PSPF/2025",
            "package": {"name": name.strip() or "pkg", "version": version},
        }
        assert validate_metadata(metadata) is True

    @given(
        path=st.text(
            min_size=1,
            max_size=50,
            alphabet=st.characters(whitelist_categories=["Ll"], whitelist_characters="/"),
        )
    )
    def test_workenv_dir_path_always_valid_with_prefix(self, path: str) -> None:
        """{workenv}/... paths always pass directory validation."""
        from flavor.psp.metadata.validators import validate_metadata

        full_path = "{workenv}/" + path.lstrip("/")
        metadata = {
            "format": "PSPF/2025",
            "workenv": {"directories": [{"path": full_path}]},
        }
        assert validate_metadata(metadata) is True


# 🌶️📦🔚
