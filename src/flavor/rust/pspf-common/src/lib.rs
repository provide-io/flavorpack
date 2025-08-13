#[repr(C, packed)]
pub struct PSPFIndex {
    pub format_magic: [u8; 8],        // "PSPF2025"
    pub format_version: u32,           // 0x20250001
    pub index_checksum: u32,           // Adler-32 of index block
    pub package_size: u64,             // Total file size
    pub launcher_size: u64,            // Size of launcher binary
    pub metadata_offset: u64,          // Offset to metadata archive
    pub metadata_size: u64,            // Size of metadata archive
    pub slot_table_offset: u64,        // Offset to slot table
    pub slot_table_size: u64,          // Size of slot table
    pub slot_count: u32,               // Number of slots
    pub flags: u32,                    // Feature flags
    pub ephemeral_public_key: [u8; 32], // Ephemeral public key
    pub metadata_checksum: [u8; 32],   // SHA256 of metadata
    pub reserved: [u8; 120],           // Reserved for future use
}

pub const INDEX_SIZE: u64 = 256;
pub const SLOT_ALIGNMENT: u64 = 8;
pub const EMOJI_MAGIC_SIZE: usize = 4;  // Just the magic wand emoji
