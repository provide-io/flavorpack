//! PSPF 2025 Format Specification Structures

use serde::{Deserialize, Serialize};
use std::collections::HashMap;

/// PSPF 2025 Index Block (256 bytes)
#[repr(C, packed)]
#[derive(Debug, Clone, Copy)]
pub struct PSPFIndex {
    pub format_magic: [u8; 8],        // "PSPF2025"
    pub format_version: u32,          // 0x20250001
    pub index_checksum: u32,          // Adler-32 of index block
    pub package_size: u64,            // Total file size
    pub launcher_size: u64,           // Size of launcher binary
    pub metadata_offset: u64,         // Offset to metadata archive
    pub metadata_size: u64,           // Size of metadata archive
    pub slot_table_offset: u64,       // Offset to slot table
    pub slot_table_size: u64,         // Size of slot table
    pub slot_count: u32,              // Number of slots
    pub flags: u32,                   // Feature flags
    pub ephemeral_public_key: [u8; 32], // Ephemeral public key
    pub metadata_checksum: [u8; 32],  // SHA256 of metadata
    pub reserved: [u8; 120],          // Reserved for future use
}

impl PSPFIndex {
    pub fn new() -> Self {
        Self {
            format_magic: *b"PSPF2025",
            format_version: super::PSPF_VERSION,
            index_checksum: 0,
            package_size: 0,
            launcher_size: 0,
            metadata_offset: 0,
            metadata_size: 0,
            slot_table_offset: 0,
            slot_table_size: 0,
            slot_count: 0,
            flags: 0,
            ephemeral_public_key: [0; 32],
            metadata_checksum: [0; 32],
            reserved: [0; 120],
        }
    }

    /// Pack index to bytes
    pub fn pack(&self) -> Vec<u8> {
        let mut buf = vec![0u8; super::INDEX_SIZE];
        
        // Use unsafe to get raw bytes
        unsafe {
            let bytes = std::slice::from_raw_parts(
                self as *const Self as *const u8,
                std::mem::size_of::<Self>()
            );
            buf[..bytes.len()].copy_from_slice(bytes);
        }
        
        // Calculate and update checksum
        buf[12..16].copy_from_slice(&[0, 0, 0, 0]); // Zero checksum field
        let checksum = adler32::adler32(buf.as_slice()).unwrap();
        buf[12..16].copy_from_slice(&checksum.to_le_bytes());
        
        buf
    }

    /// Unpack index from bytes
    pub fn unpack(data: &[u8]) -> Result<Self, super::FlavorError> {
        if data.len() != super::INDEX_SIZE {
            return Err(super::FlavorError::InvalidIndexSize);
        }

        let index = unsafe {
            std::ptr::read_unaligned(data.as_ptr() as *const PSPFIndex)
        };

        // Verify checksum
        let mut temp_data = data.to_vec();
        temp_data[12..16].copy_from_slice(&[0, 0, 0, 0]);
        let expected_checksum = adler32::adler32(temp_data.as_slice()).unwrap();
        
        if index.index_checksum != expected_checksum {
            return Err(super::FlavorError::ChecksumMismatch);
        }

        Ok(index)
    }
}

/// Launcher emoji mappings
pub fn launcher_emoji(launcher_type: &str) -> &'static str {
    match launcher_type {
        "go" => "🐹",
        "rust" => "🦀",
        "python" => "🐍",
        "node" => "🟢",
        _ => "📄",
    }
}

/// Random emojis for variety
pub const RANDOM_EMOJIS: &[&str] = &["🌮", "🍕", "🎉", "🚀", "🌟", "💎", "🎨", "🔥", "⚡", "🌈"];

/// Slot metadata
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SlotMetadata {
    pub index: usize,
    pub name: String,
    pub size: u64,
    pub compressed_size: u64,
    pub checksum: String,
    pub compression: String,
    pub purpose: String,
    pub lifecycle: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub platform: Option<String>,
}

/// Slot table entry (binary format)
#[repr(C, packed)]
#[derive(Debug, Clone, Copy)]
pub struct SlotTableEntry {
    pub offset: u64,
    pub size: u64,
    pub checksum: u32,
}

/// Package metadata
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Metadata {
    pub format: String,
    pub package: PackageInfo,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub slots: Option<Vec<SlotMetadata>>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub execution: Option<ExecutionInfo>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub verification: Option<VerificationInfo>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub build: Option<BuildInfo>,
}

/// Package information
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PackageInfo {
    pub name: String,
    pub version: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub description: Option<String>,
}

/// Build information
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct BuildInfo {
    pub builder: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub version: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub timestamp: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub host: Option<String>,
}

/// Execution configuration
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ExecutionInfo {
    pub primary_slot: i32,
    pub command: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub env: Option<HashMap<String, String>>,
}

/// Verification requirements
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct VerificationInfo {
    pub integrity_seal: IntegritySealInfo,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub trust_signatures: Option<TrustSignatureInfo>,
}

/// Integrity seal configuration
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct IntegritySealInfo {
    pub required: bool,
    pub algorithm: String,
}

/// Trust signature configuration
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TrustSignatureInfo {
    pub required: bool,
    pub signers: Vec<SignerInfo>,
}

/// Signer information
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SignerInfo {
    pub name: String,
    pub key_id: String,
    pub algorithm: String,
}

/// Align offset to boundary
pub fn align_offset(offset: u64, alignment: u64) -> u64 {
    (offset + alignment - 1) & !(alignment - 1)
}

// V0.1 Compatibility structures

/// FlavorFooter for v0.1 compatibility
#[repr(C, packed)]
#[derive(Debug, Clone, Copy)]
pub struct FlavorFooter {
    pub uv_binary_offset: u64,
    pub uv_binary_size: u64,
    pub python_install_tgz_offset: u64,
    pub python_install_tgz_size: u64,
    pub metadata_tgz_offset: u64,
    pub metadata_tgz_size: u64,
    pub payload_tgz_offset: u64,
    pub payload_tgz_size: u64,
    pub package_signature_offset: u64,
    pub package_signature_size: u64,
    pub public_key_pem_offset: u64,
    pub public_key_pem_size: u64,
    pub flavor_version: u16,
    pub flags: u16,
    pub footer_struct_checksum: u32,
    pub internal_footer_magic: u32,
    pub language_emoji: [u8; 4],
    pub type_emoji_1: [u8; 4],
    pub type_emoji_2: [u8; 4],
}

impl FlavorFooter {
    /// Check if the UV binary compression flag is set
    pub fn is_uv_binary_compressed(&self) -> bool {
        (self.flags & 0x0001) != 0
    }
}