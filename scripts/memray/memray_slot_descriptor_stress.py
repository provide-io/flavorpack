#!/usr/bin/env python3
"""
Memray stress test: SlotDescriptor pack/unpack hot path.

Profiles allocation patterns in:
- SlotDescriptor.pack() binary serialization
- SlotDescriptor.unpack() binary deserialization
- Round-trip pack -> unpack cycles (assert field equality)
"""

import os

os.environ.setdefault("LOG_LEVEL", "ERROR")

from flavor.psp.format_2025.slots import SlotDescriptor


def _make_descriptors(count: int = 10) -> list[SlotDescriptor]:
    """Create N descriptors with varying field values."""
    descriptors = []
    for i in range(count):
        descriptors.append(
            SlotDescriptor(
                id=i,
                name_hash=(i + 1) * 0x1234567890ABCDEF % (2**64),
                offset=(i + 1) * 4096,
                size=(i + 1) * 1024,
                original_size=(i + 1) * 2048,
                operations=0x1001 if i % 2 == 0 else 0x10,  # tar.gz or gzip
                checksum=(i + 1) * 0xDEADBEEF % (2**64),
            )
        )
    return descriptors


def stress_slot_descriptors() -> None:
    """Stress test SlotDescriptor pack/unpack hot paths."""
    descriptors = _make_descriptors(10)

    # Warmup - separate import-time allocations
    _ = descriptors[0].pack()
    _ = SlotDescriptor.unpack(descriptors[0].pack())

    # 50K pack cycles (10 descriptors x 5K each)
    for _ in range(5_000):
        for desc in descriptors:
            _ = desc.pack()

    # 50K unpack cycles from pre-packed data
    packed_data = [desc.pack() for desc in descriptors]
    for _ in range(5_000):
        for data in packed_data:
            _ = SlotDescriptor.unpack(data)

    # 25K round-trip cycles (10 descriptors x 2.5K each) - assert field equality
    for _ in range(2_500):
        for desc in descriptors:
            packed = desc.pack()
            unpacked = SlotDescriptor.unpack(packed)
            assert unpacked.id == desc.id, f"ID mismatch: {unpacked.id} != {desc.id}"
            assert unpacked.offset == desc.offset, "Offset mismatch"
            assert unpacked.size == desc.size, "Size mismatch"
            assert unpacked.original_size == desc.original_size, "Original size mismatch"
            assert unpacked.operations == desc.operations, "Operations mismatch"
            assert unpacked.checksum == desc.checksum, "Checksum mismatch"

    print("SlotDescriptor stress test complete: 125K cycles")


def main() -> None:
    """Entry point."""
    stress_slot_descriptors()


if __name__ == "__main__":
    main()
