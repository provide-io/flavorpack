#!/usr/bin/env python3
# src/flavor/psp/format_2025/constants.py
# PSPF 2025 Format Constants - Enhanced Memory-Mapped Version

import sys

# Format constants
PSPF_MAGIC = b"PSPF2025"  # 8 bytes, standard format
PSPF_VERSION = 0x20250001  # Keep as v1
HEADER_SIZE = 8192  # Future-proof 8KB index block
SLOT_DESCRIPTOR_SIZE = 64  # Descriptor size
TRAILING_MAGIC_SIZE = 8  # 📦🪄 = 8 bytes UTF-8
SLOT_ALIGNMENT = 8  # Minimum alignment

# Platform-specific page sizes
if sys.platform == "darwin":
    # macOS, especially M1/M2, uses 16KB pages
    PAGE_SIZE = 16384
    CACHE_LINE = 128
elif sys.platform == "linux" or sys.platform == "win32":
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
EMOJI_MAGIC_SIZE = len(TRAILING_MAGIC.encode("utf-8"))  # Size in bytes

# Encoding types - describe the actual format of slot data
ENCODING_RAW = 0  # Raw uncompressed data
ENCODING_TAR = 1  # Uncompressed tar archive
ENCODING_GZIP = 2  # Gzipped single file
ENCODING_TGZ = 3  # Tar archive, then gzipped (tar.gz)

# Future encoding formats (not implemented yet):
# ENCODING_ZSTD = 4     # Zstd compressed single file
# ENCODING_TZST = 5     # Tar archive, then zstd compressed
# ENCODING_BROTLI = 6   # Brotli compressed single file
# ENCODING_TBR = 7      # Tar archive, then brotli compressed
# ENCODING_ZIP = 8      # Zip archive (would need zipfile module)
# ENCODING_7Z = 9       # 7-zip archive (would need py7zr module)

# Checksum algorithms
CHECKSUM_ADLER32 = 0  # Default, fast
CHECKSUM_CRC32 = 1  # More robust than Adler-32
CHECKSUM_SHA256 = 2  # First 4 bytes of SHA256
CHECKSUM_XXHASH = 3  # Very fast, good distribution

# Purpose types (expanded)
PURPOSE_DATA = 0  # General data files
PURPOSE_CODE = 1  # Executable code
PURPOSE_CONFIG = 2  # Configuration files
PURPOSE_MEDIA = 3  # Media/assets

# Lifecycle types (new system with 11 values)
# Timing-based
LIFECYCLE_INIT = 0  # First run only, removed after initialization
LIFECYCLE_STARTUP = 1  # Extracted/executed at every startup
LIFECYCLE_RUNTIME = 2  # Available during application execution (default)
LIFECYCLE_SHUTDOWN = 3  # Executed during cleanup/exit phase
# Retention-based
LIFECYCLE_CACHE = 4  # Kept for performance, can be regenerated
LIFECYCLE_TEMPORARY = 5  # Removed after current session ends
# Access-based
LIFECYCLE_LAZY = 6  # Loaded on-demand, not extracted initially
LIFECYCLE_EAGER = 7  # Loaded immediately on startup
# Environment-based
LIFECYCLE_DEV = 8  # Only extracted in development/debug mode
LIFECYCLE_CONFIG = 9  # User-modifiable configuration files
LIFECYCLE_PLATFORM = 10  # Platform/OS specific content

# Legacy lifecycle values (deprecated - for backward compatibility only)
LIFECYCLE_PERMANENT = 2  # Maps to LIFECYCLE_RUNTIME
LIFECYCLE_CACHED = 4  # Maps to LIFECYCLE_CACHE
LIFECYCLE_TEMP = 5  # Maps to LIFECYCLE_TEMPORARY (deprecated)
LIFECYCLE_STREAM = 6  # Maps to LIFECYCLE_LAZY

# Access modes
ACCESS_FILE = 0  # Traditional file I/O
ACCESS_MMAP = 1  # Memory-mapped access
ACCESS_AUTO = 2  # Choose based on size/system
ACCESS_STREAM = 3  # Streaming access

# Cache priorities
CACHE_LOW = 0  # Evict first
CACHE_NORMAL = 1  # Standard caching
CACHE_HIGH = 2  # Keep in memory
CACHE_CRITICAL = 3  # Never evict

# Access hints (bit flags for slot descriptor)
ACCESS_HINT_SEQUENTIAL = 0  # Sequential access pattern
ACCESS_HINT_RANDOM = 1  # Random access pattern
ACCESS_HINT_ONCE = 2  # Access once then discard
ACCESS_HINT_PREFETCH = 3  # Prefetch next slot

# Feature flags for capabilities field
CAPABILITY_MMAP = 1 << 0  # Has memory-mapped support
CAPABILITY_PAGE_ALIGNED = 1 << 1  # Page-aligned slots
CAPABILITY_COMPRESSED_INDEX = 1 << 2  # Compressed index
CAPABILITY_STREAMING = 1 << 3  # Streaming-optimized
CAPABILITY_PREFETCH = 1 << 4  # Has prefetch hints
CAPABILITY_CACHE_AWARE = 1 << 5  # Cache-aware layout
CAPABILITY_ENCRYPTED = 1 << 6  # Has encrypted slots
CAPABILITY_SIGNED = 1 << 7  # Digitally signed

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
DEFAULT_MIN_MEMORY = 8 * 1024 * 1024  # 8MB
DEFAULT_CHUNK_SIZE = 64 * 1024  # 64KB for streaming

# Default permissions (secure by default)
DEFAULT_FILE_PERMS = 0o600  # Read/write for owner only
DEFAULT_EXECUTABLE_PERMS = 0o700  # Read/write/execute for owner only
DEFAULT_DIR_PERMS = 0o700  # Read/write/execute for owner only

# Backwards compatibility - map old names
INDEX_SIZE = HEADER_SIZE  # For existing code (now 8192 bytes)
EMOJI_MAGIC_SIZE = 8  # Always 8 bytes for 📦🪄

# Old purpose/lifecycle names for compatibility
PURPOSE_PAYLOAD = PURPOSE_DATA
PURPOSE_RUNTIME = PURPOSE_CODE
PURPOSE_TOOL = PURPOSE_CONFIG
LIFECYCLE_PERSISTENT = LIFECYCLE_PERMANENT
LIFECYCLE_VOLATILE = LIFECYCLE_CACHED
LIFECYCLE_INSTALL = LIFECYCLE_TEMPORARY

# 📦💾🔍🪄
