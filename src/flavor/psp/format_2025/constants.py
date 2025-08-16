#!/usr/bin/env python3
# src/flavor/psp/format_2025/constants.py
# PSPF 2025 Format Constants - Enhanced Memory-Mapped Version

import platform
import sys

# Format constants
PSPF_MAGIC = b"PSPF2025-MM\x00\x00\x00\x00\x00"  # 16 bytes with MM marker
PSPF_VERSION = 0x20250001  # Keep as v1
HEADER_SIZE = 512  # Expanded from 256
SLOT_DESCRIPTOR_SIZE = 64  # Expanded from 24
TRAILING_MAGIC_SIZE = 16  # Expanded from 4
SLOT_ALIGNMENT = 8  # Minimum alignment

# Platform-specific page sizes
if sys.platform == "darwin":
    # macOS, especially M1/M2, uses 16KB pages
    PAGE_SIZE = 16384
    CACHE_LINE = 128
elif sys.platform == "linux":
    PAGE_SIZE = 4096
    CACHE_LINE = 64
elif sys.platform == "win32":
    PAGE_SIZE = 4096
    CACHE_LINE = 64
else:
    # Default fallback
    PAGE_SIZE = 4096
    CACHE_LINE = 64

# Magic endings - package and wand emojis
PACKAGE_EMOJI = "📦"
MAGIC_WAND_EMOJI = "🪄"
TRAILING_MAGIC = "📦🪄"  # Both emojis at end of bundle
EMOJI_MAGIC_SIZE = len(TRAILING_MAGIC.encode('utf-8'))  # Size in bytes

# Compression types
COMPRESSION_NONE = 0
COMPRESSION_GZIP = 1
COMPRESSION_ZSTD = 2
COMPRESSION_BROTLI = 3

# Checksum algorithms
CHECKSUM_ADLER32 = 0   # Default, fast
CHECKSUM_CRC32 = 1     # More robust than Adler-32
CHECKSUM_SHA256 = 2    # First 4 bytes of SHA256
CHECKSUM_XXHASH = 3    # Very fast, good distribution

# Purpose types (expanded)
PURPOSE_DATA = 0     # General data files
PURPOSE_CODE = 1     # Executable code
PURPOSE_CONFIG = 2   # Configuration files
PURPOSE_MEDIA = 3    # Media/assets

# Lifecycle types (refined)
LIFECYCLE_PERMANENT = 0   # Never remove, always cached
LIFECYCLE_CACHED = 1      # Cache between runs
LIFECYCLE_TEMPORARY = 2   # Remove after use
LIFECYCLE_STREAM = 3      # Never fully load

# Access modes
ACCESS_FILE = 0      # Traditional file I/O
ACCESS_MMAP = 1      # Memory-mapped access
ACCESS_AUTO = 2      # Choose based on size/system
ACCESS_STREAM = 3    # Streaming access

# Cache priorities
CACHE_LOW = 0        # Evict first
CACHE_NORMAL = 1     # Standard caching
CACHE_HIGH = 2       # Keep in memory
CACHE_CRITICAL = 3   # Never evict

# Access hints (bit flags for slot descriptor)
ACCESS_HINT_SEQUENTIAL = 0   # Sequential access pattern
ACCESS_HINT_RANDOM = 1       # Random access pattern
ACCESS_HINT_ONCE = 2         # Access once then discard
ACCESS_HINT_PREFETCH = 3     # Prefetch next slot

# Feature flags for capabilities field
CAPABILITY_MMAP = 1 << 0           # Has memory-mapped support
CAPABILITY_PAGE_ALIGNED = 1 << 1   # Page-aligned slots
CAPABILITY_COMPRESSED_INDEX = 1 << 2  # Compressed index
CAPABILITY_STREAMING = 1 << 3      # Streaming-optimized
CAPABILITY_PREFETCH = 1 << 4       # Has prefetch hints
CAPABILITY_CACHE_AWARE = 1 << 5    # Cache-aware layout
CAPABILITY_ENCRYPTED = 1 << 6      # Has encrypted slots
CAPABILITY_SIGNED = 1 << 7         # Digitally signed

# Signature algorithms
SIGNATURE_NONE = b"\x00" * 8
SIGNATURE_ED25519 = b"ED25519\x00"
SIGNATURE_RSA4096 = b"RSA4096\x00"

# Metadata formats
METADATA_JSON = b"JSON\x00\x00\x00\x00"
METADATA_CBOR = b"CBOR\x00\x00\x00\x00"
METADATA_MSGPACK = b"MSGPACK\x00"

# Default values
DEFAULT_MAX_MEMORY = 128 * 1024 * 1024  # 128MB
DEFAULT_MIN_MEMORY = 8 * 1024 * 1024    # 8MB
DEFAULT_CHUNK_SIZE = 64 * 1024          # 64KB for streaming

# Backwards compatibility - map old names
INDEX_SIZE = HEADER_SIZE  # For existing code
EMOJI_MAGIC_SIZE = len(TRAILING_MAGIC.encode('utf-8'))

# Old purpose/lifecycle names for compatibility
PURPOSE_PAYLOAD = PURPOSE_DATA
PURPOSE_RUNTIME = PURPOSE_CODE
PURPOSE_TOOL = PURPOSE_CONFIG
LIFECYCLE_PERSISTENT = LIFECYCLE_PERMANENT
LIFECYCLE_VOLATILE = LIFECYCLE_CACHED
LIFECYCLE_INSTALL = LIFECYCLE_TEMPORARY

# 📦💾🔍🪄
