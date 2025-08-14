"""
PSPF 2025 Bundle Builder
"""

import io
import json
import struct
import tarfile
import tempfile
import zlib
from pathlib import Path
from typing import BinaryIO

from pyvider.telemetry import logger

from flavor.psp.format_2025.constants import (
    EMOJI_MAGIC_SIZE,
    INDEX_SIZE,
    MAGIC_WAND_EMOJI,
)
from flavor.psp.format_2025.crypto import ephemeral_key_pair, sign_data
from flavor.psp.format_2025.index import PSPFIndex
from flavor.psp.format_2025.slots import SlotMetadata, align_offset


class PSPFBuilder:
    """Build PSPF bundles."""

    def __init__(self):
        self.temp_dir = Path(tempfile.mkdtemp())

    def build(
        self,
        output_path: Path,
        metadata: dict | None = None,
        slots: list[SlotMetadata] | None = None,
        launcher_type: str = "rust",
        manifest_path: Path | None = None,
    ) -> None:
        """Build a PSPF bundle."""
        logger.info(f"🔨 Building PSPF bundle: {output_path}")

        # Load from manifest if provided
        if manifest_path:
            metadata, slots = self._load_manifest(manifest_path)

        # Ensure metadata has slots array if not provided
        if metadata and "slots" not in metadata and slots:
            metadata["slots"] = [slot.to_dict() for slot in slots]

        # Generate ephemeral keys
        private_key, public_key = ephemeral_key_pair()

        # Get launcher
        launcher_data = self._get_launcher(launcher_type)
        launcher_size = len(launcher_data)

        # Create index
        index = PSPFIndex()
        index.launcher_size = launcher_size
        index.ephemeral_public_key = public_key

        # Write launcher
        with open(output_path, "wb") as f:
            f.write(launcher_data)

            # Skip index block space
            index_offset = launcher_size
            f.seek(index_offset + INDEX_SIZE)

            # Write metadata archive
            metadata_offset = f.tell()
            metadata_size = self._write_metadata(f, metadata, private_key, public_key)

            index.metadata_offset = metadata_offset
            index.metadata_size = metadata_size

            # Write slots
            if slots:
                slot_table_offset = align_offset(f.tell())
                f.seek(slot_table_offset)

                slot_offsets = []
                for i, slot in enumerate(slots):
                    current_pos = f.tell()
                    slot_offset = align_offset(current_pos)
                    logger.trace(f"📍 Slot {i}: current_pos={current_pos}, aligned_offset={slot_offset}")
                    f.seek(slot_offset)

                    slot_data = self._compress_slot(slot)
                    f.write(slot_data)

                    # NOTE: Use adler32 to match Go/Rust implementations, not crc32
                    checksum = zlib.adler32(slot_data)
                    logger.trace(f"✏️ Slot {i}: wrote {len(slot_data)} bytes at offset {slot_offset}, adler32={checksum}")
                    
                    slot_offsets.append(
                        (slot_offset, len(slot_data), checksum)
                    )

                # Write slot table (24 bytes per entry)
                slot_table_offset = align_offset(f.tell())
                f.seek(slot_table_offset)

                for i, (offset, size, checksum) in enumerate(slot_offsets):
                    # Get slot metadata for compression and purpose info
                    slot = slots[i]
                    
                    # Map encoding strings to byte values
                    # Note: value 2 reserved for future use
                    encoding_map = {"none": 0, "gzip": 1}
                    encoding = encoding_map.get(slot.encoding, 0)
                    
                    # Get normalized purpose value
                    purpose = slot.get_purpose_value()
                    
                    # Map lifecycle strings to byte values
                    lifecycle_map = {"persistent": 0, "volatile": 1, "temporary": 2, "install": 3}
                    lifecycle = lifecycle_map.get(slot.lifecycle, 0)
                    
                    # Write 24-byte slot entry
                    # NOTE: This format must match Go/Rust implementations
                    # offset(8), size(8), checksum(4), encoding(1), purpose(1), lifecycle(1), reserved(1)
                    f.write(struct.pack("<QQIBBBB", offset, size, checksum, 
                                       encoding, purpose, lifecycle, 0))

                index.slot_table_offset = slot_table_offset
                index.slot_table_size = len(slot_offsets) * 24
                index.slot_count = len(slots)

            # Write magic wand emoji footer (4 bytes)
            emoji_bytes = MAGIC_WAND_EMOJI.encode("utf-8")
            
            # Should be exactly 4 bytes
            if len(emoji_bytes) != EMOJI_MAGIC_SIZE:
                raise ValueError(
                    f"Magic wand emoji size mismatch: {len(emoji_bytes)} != {EMOJI_MAGIC_SIZE}"
                )

            f.write(emoji_bytes)

            # Update package size
            index.package_size = f.tell()

            # Write index block
            f.seek(index_offset)
            f.write(index.pack())
            
        logger.info(f"✅ Built PSPF bundle: {output_path} ({index.package_size} bytes)")

    def _get_launcher(self, launcher_type: str) -> bytes:
        """Get launcher binary."""
        # Mock implementation - return dummy launcher
        logger.debug(f"🐹 Using {launcher_type} launcher (mock)")
        return b"LAUNCHER_BINARY_" + launcher_type.encode() + b"\x00" * 1000

    def _write_metadata(
        self, f: BinaryIO, metadata: dict, private_key: bytes, public_key: bytes
    ) -> int:
        """Write metadata archive."""
        start_pos = f.tell()

        # Create metadata archive in memory
        archive_data = self._create_metadata_archive(metadata, private_key, public_key)
        f.write(archive_data)

        return len(archive_data)

    def _create_metadata_archive(
        self, metadata: dict, private_key: bytes, public_key: bytes
    ) -> bytes:
        """Create metadata.tgz archive."""
        buffer = io.BytesIO()

        with tarfile.open(fileobj=buffer, mode="w:gz") as tar:
            # Add psp.json
            psp_data = json.dumps(metadata, indent=2).encode()
            psp_info = tarfile.TarInfo("psp.json")
            psp_info.size = len(psp_data)
            tar.addfile(psp_info, fileobj=io.BytesIO(psp_data))

            # Add integrity seal
            seal_sig = sign_data(psp_data, private_key)

            sig_info = tarfile.TarInfo("integrity/seal.sig")
            sig_info.size = len(seal_sig)
            tar.addfile(sig_info, fileobj=io.BytesIO(seal_sig))

            key_info = tarfile.TarInfo("integrity/seal.pem")
            key_info.size = len(public_key)
            tar.addfile(key_info, fileobj=io.BytesIO(public_key))

        buffer.seek(0)
        return buffer.read()

    def _compress_slot(self, slot: SlotMetadata) -> bytes:
        """Compress slot data."""
        if slot.path and slot.path.exists():
            data = slot.path.read_bytes()
        else:
            data = b"MOCK_SLOT_DATA"

        if slot.encoding == "gzip":
            return zlib.compress(data)
        else:  # none
            return data

    def _load_manifest(self, manifest_path: Path) -> tuple[dict, list[SlotMetadata]]:
        """Load manifest file."""
        import tomllib

        with open(manifest_path, "rb") as f:
            manifest = tomllib.load(f)

        # Create metadata
        metadata = {
            "format": "PSPF/2025",
            "package": {
                "name": manifest.get("name", "unknown"),
                "version": manifest.get("version", "0.0.0"),
            },
        }

        # Create slots
        slots = []
        for i, slot_data in enumerate(manifest.get("slots", [])):
            slot_path = Path(slot_data["path"])
            if slot_path.exists():
                slots.append(
                    SlotMetadata(
                        index=i,
                        name=slot_path.stem,
                        size=slot_path.stat().st_size,
                        compressed_size=0,
                        checksum="",
                        encoding="gzip",
                        purpose=slot_data.get("purpose", "payload"),
                        lifecycle=slot_data.get("lifecycle", "persistent"),
                        path=slot_path,
                    )
                )

        return metadata, slots