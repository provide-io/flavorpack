"""
PSPF 2025 Format Implementation

Progressive Secure Package Format (2025 Edition)
"""

import hashlib
import json
import os
import random
import struct
import tarfile
import tempfile
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import BinaryIO
import zlib


# Format constants
PSPF_MAGIC = b"PSPF2025"
PSPF_VERSION = 0x20250001
INDEX_SIZE = 256
EMOJI_MAGIC_SIZE = 16
SLOT_ALIGNMENT = 8

# Launcher emojis by language
LAUNCHER_EMOJIS = {
    'go': '🐹',
    'rust': '🦀', 
    'python': '🐍',
    'node': '🟢',
    'generic': '📄'
}

# Random emojis for variety
RANDOM_EMOJIS = ['🌮', '🍕', '🎉', '🚀', '🌟', '💎', '🎨', '🔥', '⚡', '🌈']


@dataclass
class SlotMetadata:
    """Metadata for a single slot."""
    index: int
    name: str
    size: int
    compressed_size: int
    checksum: str
    compression: str
    purpose: str
    lifecycle: str
    path: Path | None = None
    platform: str | None = None
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        d = asdict(self)
        if d['path']:
            d['path'] = str(d['path'])
        return d


class PSPFIndex:
    """PSPF Index Block Structure."""
    
    FORMAT = (
        '<'     # Little-endian
        '8s'    # format_magic
        'I'     # format_version
        'I'     # index_checksum
        'Q'     # package_size
        'Q'     # launcher_size
        'Q'     # metadata_offset
        'Q'     # metadata_size
        'Q'     # slot_table_offset
        'Q'     # slot_table_size
        'I'     # slot_count
        'I'     # flags
        '32s'   # ephemeral_public_key
        '32s'   # metadata_checksum
        '120s'  # reserved (reduced from 128 to make total 256)
    )
    
    def __init__(self):
        self.format_magic = PSPF_MAGIC
        self.format_version = PSPF_VERSION
        self.index_checksum = 0
        self.package_size = 0
        self.launcher_size = 0
        self.metadata_offset = 0
        self.metadata_size = 0
        self.slot_table_offset = 0
        self.slot_table_size = 0
        self.slot_count = 0
        self.flags = 0
        self.ephemeral_public_key = b'\x00' * 32
        self.metadata_checksum = b'\x00' * 32
        self.reserved = b'\x00' * 120
    
    def pack(self) -> bytes:
        """Pack index into binary format."""
        data = struct.pack(
            self.FORMAT,
            self.format_magic,
            self.format_version,
            0,  # Checksum placeholder
            self.package_size,
            self.launcher_size,
            self.metadata_offset,
            self.metadata_size,
            self.slot_table_offset,
            self.slot_table_size,
            self.slot_count,
            self.flags,
            self.ephemeral_public_key,
            self.metadata_checksum,
            self.reserved
        )
        
        # Calculate checksum with checksum field set to 0
        checksum = zlib.crc32(data)
        # Update checksum field in data
        self.index_checksum = checksum
        data = struct.pack(
            self.FORMAT,
            self.format_magic,
            self.format_version,
            checksum,  # Actual checksum
            self.package_size,
            self.launcher_size,
            self.metadata_offset,
            self.metadata_size,
            self.slot_table_offset,
            self.slot_table_size,
            self.slot_count,
            self.flags,
            self.ephemeral_public_key,
            self.metadata_checksum,
            self.reserved
        )
        
        return data
    
    @classmethod
    def unpack(cls, data: bytes) -> 'PSPFIndex':
        """Unpack index from binary data."""
        if len(data) != INDEX_SIZE:
            raise ValueError(f"Index must be {INDEX_SIZE} bytes")
            
        unpacked = struct.unpack(cls.FORMAT, data)
        
        index = cls()
        index.format_magic = unpacked[0]
        index.format_version = unpacked[1]
        index.index_checksum = unpacked[2]
        index.package_size = unpacked[3]
        index.launcher_size = unpacked[4]
        index.metadata_offset = unpacked[5]
        index.metadata_size = unpacked[6]
        index.slot_table_offset = unpacked[7]
        index.slot_table_size = unpacked[8]
        index.slot_count = unpacked[9]
        index.flags = unpacked[10]
        index.ephemeral_public_key = unpacked[11]
        index.metadata_checksum = unpacked[12]
        index.reserved = unpacked[13]
        
        return index


def ephemeral_key_pair() -> tuple[bytes, bytes]:
    """Generate ephemeral key pair for integrity sealing."""
    # Mock implementation - in real version would use cryptography
    private_key = os.urandom(32)
    public_key = os.urandom(32)
    return private_key, public_key


def align_offset(offset: int, alignment: int = SLOT_ALIGNMENT) -> int:
    """Align offset to boundary."""
    return (offset + alignment - 1) & ~(alignment - 1)


class PSPFBuilder:
    """Build PSPF bundles."""
    
    def __init__(self):
        self.temp_dir = Path(tempfile.mkdtemp())
    
    def build(self, output_path: Path, metadata: dict | None = None,
              slots: list[SlotMetadata] | None = None,
              launcher_type: str = "go", emoji_seed: str | None = None,
              manifest_path: Path | None = None) -> None:
        """Build a PSPF bundle."""
        
        # Load from manifest if provided
        if manifest_path:
            metadata, slots = self._load_manifest(manifest_path)
        
        # Ensure metadata has slots array if not provided
        if metadata and 'slots' not in metadata and slots:
            metadata['slots'] = [slot.to_dict() for slot in slots]
        
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
        with open(output_path, 'wb') as f:
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
                for slot in slots:
                    slot_offset = align_offset(f.tell())
                    f.seek(slot_offset)
                    
                    slot_data = self._compress_slot(slot)
                    f.write(slot_data)
                    
                    slot_offsets.append((slot_offset, len(slot_data), 
                                       zlib.crc32(slot_data)))
                
                # Write slot table
                slot_table_offset = align_offset(f.tell())
                f.seek(slot_table_offset)
                
                for offset, size, checksum in slot_offsets:
                    f.write(struct.pack('<QQI', offset, size, checksum))
                
                index.slot_table_offset = slot_table_offset
                index.slot_table_size = len(slot_offsets) * 20
                index.slot_count = len(slots)
            
            # Write emoji magic
            package_emoji = '📦'
            launcher_emoji = LAUNCHER_EMOJIS.get(launcher_type, '📄')
            random_emoji = random.choice(RANDOM_EMOJIS) if not emoji_seed else emoji_seed
            magic_wand = '🪄'
            
            emoji_magic = f"{package_emoji}{launcher_emoji}{random_emoji}{magic_wand}"
            emoji_bytes = emoji_magic.encode('utf-8')
            
            # Pad to exactly 16 bytes
            if len(emoji_bytes) < EMOJI_MAGIC_SIZE:
                emoji_bytes += b'\x00' * (EMOJI_MAGIC_SIZE - len(emoji_bytes))
            elif len(emoji_bytes) > EMOJI_MAGIC_SIZE:
                raise ValueError(f"Emoji magic too long: {len(emoji_bytes)} > {EMOJI_MAGIC_SIZE}")
            
            f.write(emoji_bytes)
            
            # Update package size
            index.package_size = f.tell()
            
            # Write index block
            f.seek(index_offset)
            f.write(index.pack())
    
    def _get_launcher(self, launcher_type: str) -> bytes:
        """Get launcher binary."""
        # Mock implementation - return dummy launcher
        return b"LAUNCHER_BINARY_" + launcher_type.encode() + b"\x00" * 1000
    
    def _write_metadata(self, f: BinaryIO, metadata: dict, 
                       private_key: bytes, public_key: bytes) -> int:
        """Write metadata archive."""
        start_pos = f.tell()
        
        # Create metadata archive in memory
        archive_data = self._create_metadata_archive(metadata, private_key, public_key)
        f.write(archive_data)
        
        return len(archive_data)
    
    def _create_metadata_archive(self, metadata: dict, 
                                private_key: bytes, public_key: bytes) -> bytes:
        """Create metadata.tgz archive."""
        import io
        buffer = io.BytesIO()
        
        with tarfile.open(fileobj=buffer, mode='w:gz') as tar:
            # Add psp.json
            psp_data = json.dumps(metadata, indent=2).encode()
            psp_info = tarfile.TarInfo('psp.json')
            psp_info.size = len(psp_data)
            tar.addfile(psp_info, fileobj=io.BytesIO(psp_data))
            
            # Add integrity seal
            seal_sig = self._sign_data(psp_data, private_key)
            
            sig_info = tarfile.TarInfo('integrity/seal.sig')
            sig_info.size = len(seal_sig)
            tar.addfile(sig_info, fileobj=io.BytesIO(seal_sig))
            
            key_info = tarfile.TarInfo('integrity/seal.pem')
            key_info.size = len(public_key)
            tar.addfile(key_info, fileobj=io.BytesIO(public_key))
        
        buffer.seek(0)
        return buffer.read()
    
    def _sign_data(self, data: bytes, private_key: bytes) -> bytes:
        """Sign data with private key."""
        # Mock implementation
        return hashlib.sha256(data + private_key).digest()
    
    def _compress_slot(self, slot: SlotMetadata) -> bytes:
        """Compress slot data."""
        if slot.path and slot.path.exists():
            data = slot.path.read_bytes()
        else:
            data = b"MOCK_SLOT_DATA"
        
        if slot.compression == 'gzip':
            return zlib.compress(data)
        elif slot.compression == 'none':
            return data
        else:
            return data
    
    def _load_manifest(self, manifest_path: Path) -> tuple[dict, list[SlotMetadata]]:
        """Load manifest file."""
        import tomllib
        
        with open(manifest_path, 'rb') as f:
            manifest = tomllib.load(f)
        
        # Create metadata
        metadata = {
            "format": "PSPF/2025",
            "package": {
                "name": manifest.get("name", "unknown"),
                "version": manifest.get("version", "0.0.0")
            }
        }
        
        # Create slots
        slots = []
        for i, slot_data in enumerate(manifest.get("slots", [])):
            slot_path = Path(slot_data["path"])
            if slot_path.exists():
                slots.append(SlotMetadata(
                    index=i,
                    name=slot_path.stem,
                    size=slot_path.stat().st_size,
                    compressed_size=0,
                    checksum="",
                    compression="gzip",
                    purpose=slot_data.get("purpose", "payload"),
                    lifecycle=slot_data.get("lifecycle", "persistent"),
                    path=slot_path
                ))
        
        return metadata, slots


class PSPFReader:
    """Read PSPF bundles."""
    
    def __init__(self, bundle_path: Path):
        self.bundle_path = bundle_path
        self._file = None
        self._index = None
        self._metadata = None
    
    def verify_magic(self) -> bool:
        """Verify emoji magic at end of file."""
        with open(self.bundle_path, 'rb') as f:
            f.seek(-EMOJI_MAGIC_SIZE, 2)
            magic = f.read(EMOJI_MAGIC_SIZE)
            
            try:
                magic_str = magic.decode('utf-8')
                # Check for package emoji and magic wand
                return ('📦' in magic_str and '🪄' in magic_str)
            except:
                return False
    
    def detect_launcher_size(self) -> int:
        """Detect launcher size by finding index block."""
        with open(self.bundle_path, 'rb') as f:
            # Search for PSPF magic
            data = f.read(1024 * 1024)  # Read first 1MB
            
            pos = data.find(PSPF_MAGIC)
            if pos >= 0:
                return pos
            
        return 0
    
    def read_index(self) -> PSPFIndex:
        """Read and verify index block."""
        if self._index:
            return self._index
            
        launcher_size = self.detect_launcher_size()
        
        with open(self.bundle_path, 'rb') as f:
            f.seek(launcher_size)
            index_data = f.read(INDEX_SIZE)
            
        self._index = PSPFIndex.unpack(index_data)
        
        # Verify checksum (Adler-32 with checksum field as 0)
        expected_crc = self._index.index_checksum
        # Use the raw index data, set checksum field to 0
        data_for_check = bytearray(index_data)
        data_for_check[12:16] = b'\x00\x00\x00\x00'
        actual_crc = zlib.adler32(data_for_check)
        
        if expected_crc != actual_crc:
            raise ValueError("Index checksum mismatch")
            
        return self._index
    
    def read_metadata(self) -> dict:
        """Read and parse metadata."""
        if self._metadata:
            return self._metadata
            
        index = self.read_index()
        
        with open(self.bundle_path, 'rb') as f:
            f.seek(index.metadata_offset)
            archive_data = f.read(index.metadata_size)
        
        # Extract psp.json from archive
        import io
        with tarfile.open(fileobj=io.BytesIO(archive_data), mode='r:gz') as tar:
            psp_member = tar.getmember('psp.json')
            psp_data = tar.extractfile(psp_member).read()
            
        self._metadata = json.loads(psp_data)
        return self._metadata
    
    def read_slot(self, slot_index: int) -> bytes:
        """Read a specific slot."""
        # Mock implementation
        return b"SLOT_DATA"
    
    def verify_all_checksums(self) -> bool:
        """Verify all slot checksums."""
        # Mock implementation
        return True


class PSPFLauncher:
    """Launch PSPF bundles."""
    
    def __init__(self, bundle_path: Path | None = None):
        self.bundle_path = bundle_path
        self.cache_dir = Path.home() / '.cache' / 'pspf'
        self.cache_dir.mkdir(parents=True, exist_ok=True)
    
    def extract_all_slots(self) -> dict[int, Path]:
        """Extract all slots to cache."""
        # Mock implementation - create the slot
        slot_path = self.cache_dir / "slot0"
        slot_path.mkdir(parents=True, exist_ok=True)
        return {0: slot_path}
    
    def extract_slot(self, slot: SlotMetadata, cache_dir: Path) -> Path:
        """Extract a single slot."""
        slot_path = cache_dir / slot.name
        slot_path.write_bytes(b"EXTRACTED_SLOT_DATA")
        return slot_path
    
    def execute(self, args: list[str] | None = None) -> dict:
        """Execute the bundle."""
        # Mock implementation
        return {
            'executed': True,
            'pid': os.getpid(),
            'error': None
        }
    
    def verify_integrity(self) -> dict:
        """Verify bundle integrity."""
        # Mock implementation
        return {
            'valid': True,
            'signature_valid': True,
            'tamper_detected': False
        }