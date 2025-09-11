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

// 📦💾🔍🪄