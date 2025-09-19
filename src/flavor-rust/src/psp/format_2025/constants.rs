// ingredients/flavor-rs/src/psp/format_2025/constants.rs
// Core format constants that never change
// For defaults and configuration, see defaults.rs

// Individual emoji bytes for MagicTrailer bookends
pub const PACKAGE_EMOJI_BYTES: &[u8] = &[0xF0, 0x9F, 0x93, 0xA6];  // 📦 as bytes (MagicTrailer start)
pub const MAGIC_WAND_EMOJI_BYTES: &[u8] = &[0xF0, 0x9F, 0xAA, 0x84];  // 🪄 as bytes (MagicTrailer end)

// Format version - immutable
pub const PSPF_VERSION: u32 = 0x20250001;
pub const FORMAT_VERSION: u32 = PSPF_VERSION; // Alias for compatibility

// Fixed sizes - part of the format specification
pub const HEADER_SIZE: usize = 8192; // Index block size
pub const SLOT_DESCRIPTOR_SIZE: usize = 64; // Slot descriptor size
pub const MAGIC_TRAILER_SIZE: usize = 8200; // 📦 (4) + index (8192) + 🪄 (4)
pub const SLOT_ALIGNMENT: u64 = 8; // Slots must be 8-byte aligned

// Operation codes - part of format spec
pub const OP_NONE: u8 = 0x00;  // No operation
pub const OP_TAR: u8 = 0x01;   // POSIX TAR archive (REQUIRED)
pub const OP_GZIP: u8 = 0x10;  // GZIP compression (REQUIRED)
pub const OP_BZIP2: u8 = 0x13; // BZIP2 compression (REQUIRED)
pub const OP_XZ: u8 = 0x16;    // XZ/LZMA2 compression (REQUIRED)
pub const OP_ZSTD: u8 = 0x1B;  // Zstandard compression (REQUIRED)

// Legacy codec constants (for compatibility)
pub const CODEC_RAW: u8 = 0;
pub const CODEC_GZIP: u8 = 1;
pub const CODEC_TAR: u8 = 2;
pub const CODEC_TGZ: u8 = 3;

// Purpose types - part of format spec
pub const PURPOSE_DATA: u8 = 0;   // General data files
pub const PURPOSE_CODE: u8 = 1;   // Executable code
pub const PURPOSE_CONFIG: u8 = 2; // Configuration files
pub const PURPOSE_MEDIA: u8 = 3;  // Media/assets

// Legacy aliases
pub const PURPOSE_PAYLOAD: u8 = PURPOSE_DATA;   // Deprecated: use PURPOSE_DATA
pub const PURPOSE_RUNTIME: u8 = PURPOSE_CODE;   // Deprecated: use PURPOSE_CODE
pub const PURPOSE_TOOL: u8 = PURPOSE_CONFIG;    // Deprecated: use PURPOSE_CONFIG

// Lifecycle types - part of format spec
pub const LIFECYCLE_INIT: u8 = 0;      // First run only, removed after initialization
pub const LIFECYCLE_STARTUP: u8 = 1;   // Extracted/executed at every startup
pub const LIFECYCLE_RUNTIME: u8 = 2;   // Available during application execution (default)
pub const LIFECYCLE_SHUTDOWN: u8 = 3;  // Executed during cleanup/exit phase
pub const LIFECYCLE_CACHE: u8 = 4;     // Kept for performance, can be regenerated
pub const LIFECYCLE_TEMPORARY: u8 = 5; // Removed after current session ends
pub const LIFECYCLE_LAZY: u8 = 6;      // Loaded on-demand, not extracted initially
pub const LIFECYCLE_EAGER: u8 = 7;     // Loaded immediately on startup
pub const LIFECYCLE_DEV: u8 = 8;       // Only extracted in development/debug mode
pub const LIFECYCLE_CONFIG: u8 = 9;    // User-modifiable configuration files
pub const LIFECYCLE_PLATFORM: u8 = 10; // Platform/OS specific content

// 📦💾🔍🪄