#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""Centralized default values for FlavorPack configuration."""

from __future__ import annotations

import sys

# Note: PSPF format constants have been moved to flavor.psp.format_2025.constants
# to avoid duplication and maintain single source of truth

# =================================
# Platform-specific defaults
# =================================
if sys.platform == "darwin":
    # macOS, especially M1/M2, uses 16KB pages
    DEFAULT_PAGE_SIZE = 16384
    DEFAULT_CACHE_LINE = 128
elif sys.platform == "linux" or sys.platform == "win32":
    DEFAULT_PAGE_SIZE = 4096
    DEFAULT_CACHE_LINE = 64
else:
    # Default fallback
    DEFAULT_PAGE_SIZE = 4096
    DEFAULT_CACHE_LINE = 64

# =================================
# File permissions defaults
# =================================
DEFAULT_FILE_PERMS = 0o600  # Read/write for owner only
DEFAULT_EXECUTABLE_PERMS = 0o700  # Read/write/execute for owner only
DEFAULT_DIR_PERMS = 0o700  # Read/write/execute for owner only

# =================================
# Disk defaults
# =================================
DEFAULT_DISK_SPACE_MULTIPLIER = 2  # Require 2x compressed size for extraction
# Note: Memory defaults moved to flavor.psp.format_2025.constants

# =================================
# Path constants
# =================================
PSPF_HIDDEN_PREFIX = "."
PSPF_SUFFIX = ".pspf"
INSTANCE_DIR = "instance"
PACKAGE_DIR = "package"
TMP_DIR = "tmp"
EXTRACT_DIR = "extract"
LOG_DIR = "log"
LOCK_FILE = "lock"
COMPLETE_FILE = "complete"
PACKAGE_CHECKSUM_FILE = "package.checksum"
PSP_METADATA_FILE = "psp.json"
INDEX_METADATA_FILE = "index.json"

# =================================
# Checksum algorithms
# =================================
CHECKSUM_ADLER32 = 0  # Default, fast
CHECKSUM_CRC32 = 1  # More robust than Adler-32
CHECKSUM_SHA256 = 2  # First 4 bytes of SHA256
CHECKSUM_XXHASH = 3  # Very fast, good distribution

# Note: Purpose and Lifecycle types moved to flavor.psp.format_2025.constants

# =================================
# Access modes
# =================================
ACCESS_FILE = 0  # Traditional file I/O
ACCESS_MMAP = 1  # Memory-mapped access
ACCESS_AUTO = 2  # Choose based on size/system
ACCESS_STREAM = 3  # Streaming access

# =================================
# Cache priorities
# =================================
CACHE_LOW = 0  # Evict first
CACHE_NORMAL = 1  # Standard caching
CACHE_HIGH = 2  # Keep in memory
CACHE_CRITICAL = 3  # Never evict

# =================================
# Access hints (bit flags)
# =================================
ACCESS_HINT_SEQUENTIAL = 0  # Sequential access pattern
ACCESS_HINT_RANDOM = 1  # Random access pattern
ACCESS_HINT_ONCE = 2  # Access once then discard
ACCESS_HINT_PREFETCH = 3  # Prefetch next slot

# =================================
# Capability flags
# =================================
CAPABILITY_MMAP = 1 << 0  # Has memory-mapped support
CAPABILITY_PAGE_ALIGNED = 1 << 1  # Page-aligned slots
CAPABILITY_COMPRESSED_INDEX = 1 << 2  # Compressed index
CAPABILITY_STREAMING = 1 << 3  # Streaming-optimized
CAPABILITY_PREFETCH = 1 << 4  # Has prefetch hints
CAPABILITY_CACHE_AWARE = 1 << 5  # Cache-aware layout
CAPABILITY_ENCRYPTED = 1 << 6  # Has encrypted slots
CAPABILITY_SIGNED = 1 << 7  # Digitally signed

# =================================
# Signature algorithms
# =================================
SIGNATURE_NONE = b"\x00" * 8
SIGNATURE_ED25519 = b"ED25519\x00"
SIGNATURE_RSA4096 = b"RSA4096\x00"

# =================================
# Metadata formats
# =================================
METADATA_JSON = b"JSON\x00\x00\x00\x00"
METADATA_CBOR = b"CBOR\x00\x00\x00\x00"
METADATA_MSGPACK = b"MSGPACK\x00"

# =================================
# Build configuration defaults
# =================================
DEFAULT_BUILD_USE_ISOLATION = True
DEFAULT_BUILD_NO_DEPS = False
DEFAULT_BUILD_RESOLVER = "backtracking"

# =================================
# Package configuration defaults
# =================================
DEFAULT_PACKAGE_VERSION = "0.0.1"
DEFAULT_PACKAGE_AUTHOR = "Unknown"

# =================================
# Extraction defaults
# =================================
DEFAULT_EXTRACT_VERIFY = True
DEFAULT_EXTRACT_OVERWRITE = False

# =================================
# Launcher defaults
# =================================
DEFAULT_LAUNCHER_LOG_LEVEL = "INFO"
DEFAULT_LAUNCHER_TIMEOUT = 30.0

# =================================
# Validation defaults
# =================================
DEFAULT_VALIDATION_LEVEL = "standard"  # Default validation level

# Validation levels (matching Go/Rust implementations)
VALIDATION_STRICT = "strict"  # Full security, fail on any issue
VALIDATION_STANDARD = "standard"  # Normal validation, warn on minor issues
VALIDATION_RELAXED = "relaxed"  # Skip signatures, warn on checksums
VALIDATION_MINIMAL = "minimal"  # Critical checks only
VALIDATION_NONE = "none"  # Skip all (testing only)

VALIDATION_LEVELS = {
    VALIDATION_STRICT: 0,
    VALIDATION_STANDARD: 1,
    VALIDATION_RELAXED: 2,
    VALIDATION_MINIMAL: 3,
    VALIDATION_NONE: 4,
}

# 🌶️📦🔚
