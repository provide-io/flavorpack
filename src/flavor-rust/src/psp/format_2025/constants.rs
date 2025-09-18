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
pub const PurposeData: u8 = 0;   // General data files
pub const PurposeCode: u8 = 1;   // Executable code  
pub const PurposeConfig: u8 = 2; // Configuration files
pub const PurposeMedia: u8 = 3;  // Media/assets

// Legacy aliases
pub const PurposePayload: u8 = PurposeData;   // Deprecated: use PurposeData
pub const PurposeRuntime: u8 = PurposeCode;   // Deprecated: use PurposeCode
pub const PurposeTool: u8 = PurposeConfig;    // Deprecated: use PurposeConfig

// Lifecycle types - part of format spec
pub const LifecycleInit: u8 = 0;      // First run only, removed after initialization
pub const LifecycleStartup: u8 = 1;   // Extracted/executed at every startup
pub const LifecycleRuntime: u8 = 2;   // Available during application execution (default)
pub const LifecycleShutdown: u8 = 3;  // Executed during cleanup/exit phase
pub const LifecycleCache: u8 = 4;     // Kept for performance, can be regenerated
pub const LifecycleTemporary: u8 = 5; // Removed after current session ends
pub const LifecycleLazy: u8 = 6;      // Loaded on-demand, not extracted initially
pub const LifecycleEager: u8 = 7;     // Loaded immediately on startup
pub const LifecycleDev: u8 = 8;       // Only extracted in development/debug mode
pub const LifecycleConfig: u8 = 9;    // User-modifiable configuration files
pub const LifecyclePlatform: u8 = 10; // Platform/OS specific content

// 📦💾🔍🪄