#
# flavor/models.py
#
import struct
import zlib

from attrs import define, field

# Canonical PSPF v0.1 Specification Constants
PSPF_VERSION_NUMBER: int = 0x0001  # PSPF Version 0.1
PSPF_INTERNAL_FOOTER_MAGIC_NUMBER: int = (
    0x30505350  # '0PSP' - PSPF magic number for footer validation
)
# Flavor v0.1 Multi-Component Emoji Footer Design
# 🏗️ Crane for builder, 📦 Package for Flavor file, 🚀 Rocket for launcher
FLAVOR_BUILDER_MAGIC: bytes = (
    b"\xf0\x9f\x8f\x97\xef\xb8\x8fFLAVOR\xf0\x9f\x8f\x97\xef\xb8\x8f"  # 🏗️FLAVOR🏗️
)
FLAVOR_PACKAGE_MAGIC: bytes = b"\xf0\x9f\x93\xa6FLAVOR\xf0\x9f\x93\xa6"  # 📦FLAVOR📦
FLAVOR_LAUNCHER_MAGIC: bytes = b"\xf0\x9f\x9a\x80FLAVOR\xf0\x9f\x9a\x80"  # 🚀FLAVOR🚀

# Use package magic as default for Flavor files
FLAVOR_EOF_MAGIC_STRING: bytes = FLAVOR_PACKAGE_MAGIC

# Emoji constants (4 bytes each for common emojis)
EMOJI_PYTHON: bytes = b"\xf0\x9f\x90\x8d"  # 🐍
EMOJI_GO: bytes = b"\xf0\x9f\x90\xb9"  # 🐹
EMOJI_RUST: bytes = b"\xf0\x9f\xa6\x80"  # 🦀

EMOJI_LAUNCHER: bytes = b"\xf0\x9f\x9a\x80"  # 🚀
EMOJI_PACKAGER: bytes = b"\xf0\x9f\x93\xa6"  # 📦
EMOJI_METADATA: bytes = b"\xf0\x9f\x93\x8b"  # 📝
EMOJI_PAYLOAD: bytes = b"\xf0\x9f\x92\xbe"  # 💾

# Format for 12 uint64, 2 uint16, 2 uint32, and 3 * 4 bytes for emojis
# Total: 12*8 + 2*2 + 2*4 + 3*4 = 96 + 4 + 8 + 12 = 120 bytes
FOOTER_STRUCT_FORMAT = "<QQQQQQQQQQQQHHII4s4s4s"
FOOTER_SIZE = struct.calcsize(FOOTER_STRUCT_FORMAT)

if FOOTER_SIZE != 120:
    raise AssertionError(
        f"Calculated Flavor footer size is {FOOTER_SIZE}, expected 120."
    )


@define(frozen=True, slots=True)
class PSPFooter:
    uv_offset: int
    uv_size: int
    python_offset: int
    python_size: int
    metadata_offset: int
    metadata_size: int
    payload_offset: int
    payload_size: int
    signature_offset: int
    signature_size: int
    public_key_offset: int
    public_key_size: int
    pspf_version: int = field(default=PSPF_VERSION_NUMBER)
    flags: int = field(default=0)
    footer_struct_checksum: int = field(init=False)
    internal_footer_magic: int = field(default=PSPF_INTERNAL_FOOTER_MAGIC_NUMBER)
    language_emoji: bytes = field(
        default=b"\x00\x00\x00\x00"
    )  # 4 bytes, default to null bytes
    type_emoji_1: bytes = field(default=b"\x00\x00\x00\x00")
    type_emoji_2: bytes = field(default=b"\x00\x00\x00\x00")

    @property
    def is_uv_binary_compressed(self) -> bool:
        """Checks if the UV binary compression flag is set."""
        return (self.flags & 0x0001) != 0

    def __attrs_post_init__(self) -> None:
        data_to_checksum = struct.pack(
            FOOTER_STRUCT_FORMAT,
            self.uv_offset,
            self.uv_size,
            self.python_offset,
            self.python_size,
            self.metadata_offset,
            self.metadata_size,
            self.payload_offset,
            self.payload_size,
            self.signature_offset,
            self.signature_size,
            self.public_key_offset,
            self.public_key_size,
            self.pspf_version,
            self.flags,
            0,  # Checksum field is 0 for calculation
            self.internal_footer_magic,
            self.language_emoji,
            self.type_emoji_1,
            self.type_emoji_2,
        )
        # Use Adler-32, which is standard in both Python and Go.
        # The bitmask ensures the result is an unsigned 32-bit integer.
        calculated_checksum = zlib.adler32(data_to_checksum) & 0xFFFFFFFF
        object.__setattr__(self, "footer_struct_checksum", calculated_checksum)

    def pack(self) -> bytes:
        return struct.pack(
            FOOTER_STRUCT_FORMAT,
            self.uv_offset,
            self.uv_size,
            self.python_offset,
            self.python_size,
            self.metadata_offset,
            self.metadata_size,
            self.payload_offset,
            self.payload_size,
            self.signature_offset,
            self.signature_size,
            self.public_key_offset,
            self.public_key_size,
            self.pspf_version,
            self.flags,
            self.footer_struct_checksum,
            self.internal_footer_magic,
            self.language_emoji,
            self.type_emoji_1,
            self.type_emoji_2,
        )

    @classmethod
    def unpack(cls, buffer: bytes) -> "PSPFooter":
        if len(buffer) != FOOTER_SIZE:
            raise ValueError(f"Buffer size {len(buffer)} != {FOOTER_SIZE}")

        unpacked = struct.unpack(FOOTER_STRUCT_FORMAT, buffer)

        footer_instance = cls(
            uv_offset=unpacked[0],
            uv_size=unpacked[1],
            python_offset=unpacked[2],
            python_size=unpacked[3],
            metadata_offset=unpacked[4],
            metadata_size=unpacked[5],
            payload_offset=unpacked[6],
            payload_size=unpacked[7],
            signature_offset=unpacked[8],
            signature_size=unpacked[9],
            public_key_offset=unpacked[10],
            public_key_size=unpacked[11],
            pspf_version=unpacked[12],
            flags=unpacked[13],
            internal_footer_magic=unpacked[15],
            language_emoji=unpacked[16],
            type_emoji_1=unpacked[17],
            type_emoji_2=unpacked[18],
        )

        read_checksum_from_buffer = unpacked[14]
        if footer_instance.footer_struct_checksum != read_checksum_from_buffer:
            raise ValueError("Footer checksum mismatch.")

        if footer_instance.internal_footer_magic != PSPF_INTERNAL_FOOTER_MAGIC_NUMBER:
            raise ValueError("Invalid InternalFooterMagic.")
        if footer_instance.pspf_version != PSPF_VERSION_NUMBER:
            raise ValueError("Unexpected PSPF version.")

        return footer_instance


# 📋 🗂️ 📊


# 📦🍜📊🪄
