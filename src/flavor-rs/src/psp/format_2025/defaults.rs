// helpers/flavor-rs/src/psp/format_2025/defaults.rs
// Centralized default values matching Python defaults.py

// =================================
// PSPF Format defaults
// =================================
pub const DEFAULT_PSPF_VERSION: u32 = 0x20250001; // Format version v1
pub const DEFAULT_HEADER_SIZE: usize = 8192; // Future-proof 8KB index block
pub const DEFAULT_SLOT_DESCRIPTOR_SIZE: usize = 64; // Descriptor size
pub const DEFAULT_MAGIC_TRAILER_SIZE: usize = 8200; // Index block with markers
pub const DEFAULT_SLOT_ALIGNMENT: u64 = 8; // Minimum alignment

// Platform-specific page sizes
#[cfg(target_os = "macos")]
pub const DEFAULT_PAGE_SIZE: usize = 16384; // macOS, especially M1/M2
#[cfg(target_os = "linux")]
pub const DEFAULT_PAGE_SIZE: usize = 4096;
#[cfg(target_os = "windows")]
pub const DEFAULT_PAGE_SIZE: usize = 4096;
#[cfg(not(any(target_os = "macos", target_os = "linux", target_os = "windows")))]
pub const DEFAULT_PAGE_SIZE: usize = 4096; // Default fallback

// Cache line sizes
#[cfg(target_os = "macos")]
pub const DEFAULT_CACHE_LINE: usize = 128;
#[cfg(not(target_os = "macos"))]
pub const DEFAULT_CACHE_LINE: usize = 64;

// =================================
// File permissions defaults
// =================================
pub const DEFAULT_FILE_PERMS: u16 = 0o600; // Read/write for owner only
pub const DEFAULT_EXECUTABLE_PERMS: u16 = 0o700; // Read/write/execute for owner only
pub const DEFAULT_DIR_PERMS: u16 = 0o700; // Read/write/execute for owner only

// =================================
// Disk and memory defaults
// =================================
pub const DEFAULT_DISK_SPACE_MULTIPLIER: u64 = 2; // Require 2x compressed size for extraction
pub const DEFAULT_MAX_MEMORY: u64 = 128 * 1024 * 1024; // 128MB
pub const DEFAULT_MIN_MEMORY: u64 = 8 * 1024 * 1024; // 8MB
pub const DEFAULT_CHUNK_SIZE: usize = 64 * 1024; // 64KB for streaming

// =================================
// Path constants
// =================================
pub const DEFAULT_PSPF_HIDDEN_PREFIX: &str = ".";
pub const DEFAULT_PSPF_SUFFIX: &str = ".pspf";
pub const DEFAULT_INSTANCE_DIR: &str = "instance";
pub const DEFAULT_PACKAGE_DIR: &str = "package";
pub const DEFAULT_TMP_DIR: &str = "tmp";
pub const DEFAULT_EXTRACT_DIR: &str = "extract";
pub const DEFAULT_LOG_DIR: &str = "log";
pub const DEFAULT_LOCK_FILE: &str = "lock";
pub const DEFAULT_COMPLETE_FILE: &str = "complete";
pub const DEFAULT_PACKAGE_CHECKSUM_FILE: &str = "package.checksum";
pub const DEFAULT_PSP_METADATA_FILE: &str = "psp.json";
pub const DEFAULT_INDEX_METADATA_FILE: &str = "index.json";
pub const DEFAULT_CACHE_SUBDIR: &str = ".cache/flavor/workenv";

// =================================
// Checksum algorithms
// =================================
pub const CHECKSUM_ADLER32: u8 = 0; // Default, fast
pub const CHECKSUM_CRC32: u8 = 1; // More robust than Adler-32
pub const CHECKSUM_SHA256: u8 = 2; // First 4 bytes of SHA256
pub const CHECKSUM_XXHASH: u8 = 3; // Very fast, good distribution

// =================================
// Purpose types
// =================================
pub const DEFAULT_PURPOSE_DATA: u8 = 0; // General data files
pub const DEFAULT_PURPOSE_CODE: u8 = 1; // Executable code
pub const DEFAULT_PURPOSE_CONFIG: u8 = 2; // Configuration files
pub const DEFAULT_PURPOSE_MEDIA: u8 = 3; // Media/assets

// =================================
// Lifecycle types
// =================================
// Timing-based
pub const DEFAULT_LIFECYCLE_INIT: u8 = 0; // First run only, removed after initialization
pub const DEFAULT_LIFECYCLE_STARTUP: u8 = 1; // Extracted/executed at every startup
pub const DEFAULT_LIFECYCLE_RUNTIME: u8 = 2; // Available during application execution (default)
pub const DEFAULT_LIFECYCLE_SHUTDOWN: u8 = 3; // Executed during cleanup/exit phase

// Retention-based
pub const DEFAULT_LIFECYCLE_CACHE: u8 = 4; // Kept for performance, can be regenerated
pub const DEFAULT_LIFECYCLE_TEMPORARY: u8 = 5; // Removed after current session ends

// Access-based
pub const DEFAULT_LIFECYCLE_LAZY: u8 = 6; // Loaded on-demand, not extracted initially
pub const DEFAULT_LIFECYCLE_EAGER: u8 = 7; // Loaded immediately on startup

// Environment-based
pub const DEFAULT_LIFECYCLE_DEV: u8 = 8; // Only extracted in development/debug mode
pub const DEFAULT_LIFECYCLE_CONFIG: u8 = 9; // User-modifiable configuration files
pub const DEFAULT_LIFECYCLE_PLATFORM: u8 = 10; // Platform/OS specific content

// =================================
// Access modes
// =================================
pub const ACCESS_FILE: u8 = 0; // Traditional file I/O
pub const ACCESS_MMAP: u8 = 1; // Memory-mapped access
pub const ACCESS_AUTO: u8 = 2; // Choose based on size/system
pub const ACCESS_STREAM: u8 = 3; // Streaming access

// =================================
// Cache priorities
// =================================
pub const CACHE_LOW: u8 = 0; // Evict first
pub const CACHE_NORMAL: u8 = 1; // Standard caching
pub const CACHE_HIGH: u8 = 2; // Keep in memory
pub const CACHE_CRITICAL: u8 = 3; // Never evict

// =================================
// Access hints (bit flags)
// =================================
pub const ACCESS_HINT_SEQUENTIAL: u8 = 0; // Sequential access pattern
pub const ACCESS_HINT_RANDOM: u8 = 1; // Random access pattern
pub const ACCESS_HINT_ONCE: u8 = 2; // Access once then discard
pub const ACCESS_HINT_PREFETCH: u8 = 3; // Prefetch next slot

// =================================
// Capability flags
// =================================
pub const CAPABILITY_MMAP: u64 = 1 << 0; // Has memory-mapped support
pub const CAPABILITY_PAGE_ALIGNED: u64 = 1 << 1; // Page-aligned slots
pub const CAPABILITY_COMPRESSED_INDEX: u64 = 1 << 2; // Compressed index
pub const CAPABILITY_STREAMING: u64 = 1 << 3; // Streaming-optimized
pub const CAPABILITY_PREFETCH: u64 = 1 << 4; // Has prefetch hints
pub const CAPABILITY_CACHE_AWARE: u64 = 1 << 5; // Cache-aware layout
pub const CAPABILITY_ENCRYPTED: u64 = 1 << 6; // Has encrypted slots
pub const CAPABILITY_SIGNED: u64 = 1 << 7; // Digitally signed

// =================================
// Signature algorithms
// =================================
pub const SIGNATURE_NONE: [u8; 8] = *b"\x00\x00\x00\x00\x00\x00\x00\x00";
pub const SIGNATURE_ED25519: [u8; 8] = *b"ED25519\x00";
pub const SIGNATURE_RSA4096: [u8; 8] = *b"RSA4096\x00";

// =================================
// Metadata formats
// =================================
pub const METADATA_JSON: [u8; 8] = *b"JSON\x00\x00\x00\x00";
pub const METADATA_CBOR: [u8; 8] = *b"CBOR\x00\x00\x00\x00";
pub const METADATA_MSGPACK: [u8; 8] = *b"MSGPACK\x00";

// =================================
// Build configuration defaults
// =================================
pub const DEFAULT_BUILD_USE_ISOLATION: bool = true;
pub const DEFAULT_BUILD_NO_DEPS: bool = false;
pub const DEFAULT_BUILD_RESOLVER: &str = "backtracking";

// =================================
// Package configuration defaults
// =================================
pub const DEFAULT_PACKAGE_VERSION: &str = "0.0.1";
pub const DEFAULT_PACKAGE_AUTHOR: &str = "Unknown";

// =================================
// Extraction defaults
// =================================
pub const DEFAULT_EXTRACT_VERIFY: bool = true;
pub const DEFAULT_EXTRACT_OVERWRITE: bool = false;

// =================================
// Launcher defaults
// =================================
pub const DEFAULT_LAUNCHER_LOG_LEVEL: &str = "INFO";
pub const DEFAULT_LAUNCHER_TIMEOUT: f64 = 30.0; // seconds

// =================================
// Validation defaults
// =================================
pub const DEFAULT_VALIDATION_LEVEL: &str = "standard"; // Default validation level

/// ValidationLevel represents different levels of security validation
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum ValidationLevel {
    /// Full security checks, fail on any issue (most secure)
    Strict,
    /// Normal validation, warnings for minor issues (default)
    Standard,
    /// Skip signature checks, warn on checksum mismatches
    Relaxed,
    /// Only critical checks, continue on most warnings
    Minimal,
    /// Skip all validation (testing only, NOT RECOMMENDED)
    None,
}

impl ValidationLevel {
    /// Parse validation level from string (case insensitive)
    #[must_use]
    pub fn parse(s: &str) -> Option<Self> {
        match s.to_lowercase().as_str() {
            "strict" => Some(Self::Strict),
            "standard" => Some(Self::Standard),
            "relaxed" => Some(Self::Relaxed),
            "minimal" => Some(Self::Minimal),
            "none" => Some(Self::None),
            _ => None,
        }
    }

    /// Convert validation level to string
    pub fn as_str(&self) -> &'static str {
        match self {
            ValidationLevel::Strict => "strict",
            ValidationLevel::Standard => "standard",
            ValidationLevel::Relaxed => "relaxed",
            ValidationLevel::Minimal => "minimal",
            ValidationLevel::None => "none",
        }
    }
}

/// Get the current validation level from environment or default
pub fn get_validation_level() -> ValidationLevel {
    use std::env;

    // Check FLAVOR_VALIDATION variable
    if let Ok(val) = env::var("FLAVOR_VALIDATION") {
        if let Some(level) = ValidationLevel::parse(&val) {
            return level;
        }
    }

    // Use default from constants
    ValidationLevel::parse(DEFAULT_VALIDATION_LEVEL).unwrap_or(ValidationLevel::Standard)
}
