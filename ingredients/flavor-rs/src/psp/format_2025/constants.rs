// helpers/flavor-rs/src/psp/format_2025/constants.rs
// PSPF 2025 Format Constants - Enhanced Memory-Mapped Version

/// Format magic bytes - using byte literals to prevent string from appearing in binary
pub const PSPF_MAGIC: [u8; 8] = [b'P', b'S', b'P', b'F', b'2', b'0', b'2', b'5'];

/// Format version - keeping as v1
pub const PSPF_VERSION: u32 = 0x20250001;
pub const FORMAT_VERSION: u32 = PSPF_VERSION; // Alias for compatibility

/// Size constants
pub const HEADER_SIZE: usize = 8192; // Future-proof 8KB index block
pub const INDEX_SIZE: usize = HEADER_SIZE; // Alias for compatibility
pub const SLOT_DESCRIPTOR_SIZE: usize = 64; // Descriptor size
pub const TRAILING_MAGIC_SIZE: usize = 8; // 📦🪄 = 8 bytes UTF-8
pub const SLOT_ALIGNMENT: u64 = 8;

// Platform-specific page sizes
#[cfg(target_os = "macos")]
pub const PAGE_SIZE: usize = 16384; // macOS, especially M1/M2
#[cfg(target_os = "linux")]
pub const PAGE_SIZE: usize = 4096;
#[cfg(target_os = "windows")]
pub const PAGE_SIZE: usize = 4096;
#[cfg(not(any(target_os = "macos", target_os = "linux", target_os = "windows")))]
pub const PAGE_SIZE: usize = 4096; // Default

/// Magic endings - package and wand emojis as bytes to avoid literal emojis in binary
/// 📦 = 0xF0 0x9F 0x93 0xA6 (UTF-8)
pub const PACKAGE_EMOJI_BYTES: &[u8] = &[0xF0, 0x9F, 0x93, 0xA6];
/// 🪄 = 0xF0 0x9F 0xAA 0x84 (UTF-8)  
pub const MAGIC_WAND_EMOJI_BYTES: &[u8] = &[0xF0, 0x9F, 0xAA, 0x84];
pub const EMOJI_MAGIC_SIZE: usize = 8; // Both emojis

/// Disk space safety multiplier - require 2x compressed size for extraction
pub const DISK_SPACE_MULTIPLIER: u64 = 2;

// ==================== Path Constants ====================
/// Hidden directory prefix for metadata
pub const PSPF_HIDDEN_PREFIX: &str = ".";

/// Suffix for metadata directory
pub const PSPF_SUFFIX: &str = ".pspf";

/// Instance metadata directory (persistent across extractions)
pub const INSTANCE_DIR: &str = "instance";

/// Package metadata directory (replaced each extraction)
pub const PACKAGE_DIR: &str = "package";

/// Temporary extraction directory
pub const TMP_DIR: &str = "tmp";

/// Extract operations directory (under instance)
pub const EXTRACT_DIR: &str = "extract";

/// Log directory (under instance)
pub const LOG_DIR: &str = "log";

/// Lock file name (in instance/extract/)
pub const LOCK_FILE: &str = "lock";

/// Completion marker file name (in instance/extract/)
pub const COMPLETE_FILE: &str = "complete";

/// Package checksum file name (in instance/)
pub const PACKAGE_CHECKSUM_FILE: &str = "package.checksum";

/// PSP metadata JSON file name (in package/)
pub const PSP_METADATA_FILE: &str = "psp.json";

/// Index metadata JSON file name (in instance/)
pub const INDEX_METADATA_FILE: &str = "index.json";

/// Encoding types - describe the actual format of slot data
pub const ENCODING_RAW: u8 = 0; // Raw uncompressed data
pub const ENCODING_TAR: u8 = 1; // Uncompressed tar archive
pub const ENCODING_GZIP: u8 = 2; // Gzipped single file
pub const ENCODING_TGZ: u8 = 3; // Tar archive, then gzipped (tar.gz)

// Future encoding formats (not implemented yet):
// pub const ENCODING_ZSTD: u8 = 4;     // Zstd compressed single file
// pub const ENCODING_TZST: u8 = 5;     // Tar archive, then zstd compressed
// pub const ENCODING_BROTLI: u8 = 6;   // Brotli compressed single file
// pub const ENCODING_TBR: u8 = 7;      // Tar archive, then brotli compressed
// pub const ENCODING_ZIP: u8 = 8;      // Zip archive
// pub const ENCODING_7Z: u8 = 9;       // 7-zip archive

/// Purpose types (expanded)
pub const PURPOSE_DATA: u8 = 0; // General data files
pub const PURPOSE_CODE: u8 = 1; // Executable code
pub const PURPOSE_CONFIG: u8 = 2; // Configuration files
pub const PURPOSE_MEDIA: u8 = 3; // Media/assets

/// Lifecycle types (refined)
pub const LIFECYCLE_PERMANENT: u8 = 0; // Never remove, always cached
pub const LIFECYCLE_CACHED: u8 = 1; // Cache between runs
pub const LIFECYCLE_TEMPORARY: u8 = 2; // Remove after use
pub const LIFECYCLE_STREAM: u8 = 3; // Never fully load

/// Access modes
pub const ACCESS_FILE: u8 = 0; // Traditional file I/O
pub const ACCESS_MMAP: u8 = 1; // Memory-mapped access
pub const ACCESS_AUTO: u8 = 2; // Choose based on size/system
pub const ACCESS_STREAM: u8 = 3; // Streaming access

/// Cache priorities
pub const CACHE_LOW: u8 = 0; // Evict first
pub const CACHE_NORMAL: u8 = 1; // Standard caching
pub const CACHE_HIGH: u8 = 2; // Keep in memory
pub const CACHE_CRITICAL: u8 = 3; // Never evict

/// Access hints (bit flags for slot descriptor)
pub const ACCESS_HINT_SEQUENTIAL: u8 = 0; // Sequential access pattern
pub const ACCESS_HINT_RANDOM: u8 = 1; // Random access pattern
pub const ACCESS_HINT_ONCE: u8 = 2; // Access once then discard
pub const ACCESS_HINT_PREFETCH: u8 = 3; // Prefetch next slot

/// Feature flags for capabilities field
pub const CAPABILITY_MMAP: u64 = 1 << 0; // Has memory-mapped support
pub const CAPABILITY_PAGE_ALIGNED: u64 = 1 << 1; // Page-aligned slots
pub const CAPABILITY_COMPRESSED_INDEX: u64 = 1 << 2; // Compressed index
pub const CAPABILITY_STREAMING: u64 = 1 << 3; // Streaming-optimized
pub const CAPABILITY_PREFETCH: u64 = 1 << 4; // Has prefetch hints
pub const CAPABILITY_CACHE_AWARE: u64 = 1 << 5; // Cache-aware layout
pub const CAPABILITY_ENCRYPTED: u64 = 1 << 6; // Has encrypted slots
pub const CAPABILITY_SIGNED: u64 = 1 << 7; // Digitally signed

/// Signature algorithms
pub const SIGNATURE_NONE: [u8; 8] = *b"\x00\x00\x00\x00\x00\x00\x00\x00";
pub const SIGNATURE_ED25519: [u8; 8] = *b"ED25519\x00";
pub const SIGNATURE_RSA4096: [u8; 8] = *b"RSA4096\x00";

/// Metadata formats
pub const METADATA_JSON: [u8; 8] = *b"JSON\x00\x00\x00\x00";
pub const METADATA_CBOR: [u8; 8] = *b"CBOR\x00\x00\x00\x00";
pub const METADATA_MSGPACK: [u8; 8] = *b"MSGPACK\x00";

/// Default values
pub const DEFAULT_MAX_MEMORY: u64 = 128 * 1024 * 1024; // 128MB
pub const DEFAULT_MIN_MEMORY: u64 = 8 * 1024 * 1024; // 8MB
pub const DEFAULT_CHUNK_SIZE: usize = 64 * 1024; // 64KB for streaming

/// Default file permissions (Unix-style)
pub const DEFAULT_FILE_PERMS: u16 = 0o600; // Read/write for owner only
pub const DEFAULT_EXECUTABLE_PERMS: u16 = 0o700; // Read/write/execute for owner only
pub const DEFAULT_DIR_PERMS: u16 = 0o700; // Read/write/execute for owner only (secure by default)

// Old purpose/lifecycle names for compatibility
pub const PURPOSE_PAYLOAD: u8 = PURPOSE_DATA;
pub const PURPOSE_RUNTIME: u8 = PURPOSE_CODE;
pub const PURPOSE_TOOL: u8 = PURPOSE_CONFIG;
pub const LIFECYCLE_PERSISTENT: u8 = LIFECYCLE_PERMANENT;
pub const LIFECYCLE_VOLATILE: u8 = LIFECYCLE_CACHED;
pub const LIFECYCLE_INSTALL: u8 = LIFECYCLE_TEMPORARY;

// 📦💾🔍🪄
