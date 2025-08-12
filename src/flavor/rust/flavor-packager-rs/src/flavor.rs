//
// flavor/rust/flavor-packager-rs/src/flavor.rs
//
use anyhow::{Context, Result};
use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};
use std::fs::File;
use std::io::{Read, Seek, SeekFrom, Write};
use std::path::Path;

// Flavor Constants
pub const FLAVOR_VERSION: u16 = 1;
pub const FLAVOR_INTERNAL_FOOTER_MAGIC: u32 = 0x30505350; // '0PSP' in little endian
pub const FLAVOR_MAGIC_EOF_STRING: &[u8] = "📦FLAVOR📦".as_bytes(); // UTF-8 encoded
pub const FOOTER_SIZE: i64 = 120;

// Emoji constants for structured logging
pub const EMOJI_RUST: &str = "🦀";
pub const EMOJI_PACKAGER: &str = "📦";
pub const EMOJI_PAYLOAD: &str = "🗃️";

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct FlavorFooter {
    // All offsets and sizes are relative to the beginning of the Flavor data section
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
    
    // Footer metadata
    pub flavor_version: u16,
    pub flags: u16,
    pub footer_struct_checksum: u32,
    pub internal_footer_magic: u32,
    pub language_emoji: [u8; 4],
    pub type_emoji_1: [u8; 4],
    pub type_emoji_2: [u8; 4],
}

impl FlavorFooter {
    pub fn new() -> Self {
        Self {
            uv_binary_offset: 0,
            uv_binary_size: 0,
            python_install_tgz_offset: 0,
            python_install_tgz_size: 0,
            metadata_tgz_offset: 0,
            metadata_tgz_size: 0,
            payload_tgz_offset: 0,
            payload_tgz_size: 0,
            package_signature_offset: 0,
            package_signature_size: 0,
            public_key_pem_offset: 0,
            public_key_pem_size: 0,
            flavor_version: FLAVOR_VERSION,
            flags: 0,
            footer_struct_checksum: 0,
            internal_footer_magic: FLAVOR_INTERNAL_FOOTER_MAGIC,
            language_emoji: [0; 4],
            type_emoji_1: [0; 4],
            type_emoji_2: [0; 4],
        }
    }
    
    pub fn calculate_checksum(&self) -> u32 {
        let mut hasher = Sha256::new();
        
        // Create a 120-byte buffer with the footer data in the exact layout
        let mut buf = vec![0u8; 120];
        
        // 12 uint64 fields (96 bytes)
        buf[0..8].copy_from_slice(&self.uv_binary_offset.to_le_bytes());
        buf[8..16].copy_from_slice(&self.uv_binary_size.to_le_bytes());
        buf[16..24].copy_from_slice(&self.python_install_tgz_offset.to_le_bytes());
        buf[24..32].copy_from_slice(&self.python_install_tgz_size.to_le_bytes());
        buf[32..40].copy_from_slice(&self.metadata_tgz_offset.to_le_bytes());
        buf[40..48].copy_from_slice(&self.metadata_tgz_size.to_le_bytes());
        buf[48..56].copy_from_slice(&self.payload_tgz_offset.to_le_bytes());
        buf[56..64].copy_from_slice(&self.payload_tgz_size.to_le_bytes());
        buf[64..72].copy_from_slice(&self.package_signature_offset.to_le_bytes());
        buf[72..80].copy_from_slice(&self.package_signature_size.to_le_bytes());
        buf[80..88].copy_from_slice(&self.public_key_pem_offset.to_le_bytes());
        buf[88..96].copy_from_slice(&self.public_key_pem_size.to_le_bytes());
        
        // Final 24 bytes: version(2) + flags(2) + checksum(4) + magic(4) + lang_emoji(4) + type_emoji_1(4) + type_emoji_2(4)
        buf[96..98].copy_from_slice(&self.flavor_version.to_le_bytes());
        buf[98..100].copy_from_slice(&self.flags.to_le_bytes());
        buf[100..104].copy_from_slice(&0u32.to_le_bytes()); // checksum = 0 for calculation
        buf[104..108].copy_from_slice(&self.internal_footer_magic.to_le_bytes());
        buf[108..112].copy_from_slice(&self.language_emoji);
        buf[112..116].copy_from_slice(&self.type_emoji_1);
        buf[116..120].copy_from_slice(&self.type_emoji_2);
        
        hasher.update(&buf);
        let result = hasher.finalize();
        
        // Return first 4 bytes as u32
        u32::from_le_bytes([result[0], result[1], result[2], result[3]])
    }
    
    pub fn to_bytes(&self) -> Vec<u8> {
        let mut buf = vec![0u8; 120];
        
        // 12 uint64 fields (96 bytes)
        buf[0..8].copy_from_slice(&self.uv_binary_offset.to_le_bytes());
        buf[8..16].copy_from_slice(&self.uv_binary_size.to_le_bytes());
        buf[16..24].copy_from_slice(&self.python_install_tgz_offset.to_le_bytes());
        buf[24..32].copy_from_slice(&self.python_install_tgz_size.to_le_bytes());
        buf[32..40].copy_from_slice(&self.metadata_tgz_offset.to_le_bytes());
        buf[40..48].copy_from_slice(&self.metadata_tgz_size.to_le_bytes());
        buf[48..56].copy_from_slice(&self.payload_tgz_offset.to_le_bytes());
        buf[56..64].copy_from_slice(&self.payload_tgz_size.to_le_bytes());
        buf[64..72].copy_from_slice(&self.package_signature_offset.to_le_bytes());
        buf[72..80].copy_from_slice(&self.package_signature_size.to_le_bytes());
        buf[80..88].copy_from_slice(&self.public_key_pem_offset.to_le_bytes());
        buf[88..96].copy_from_slice(&self.public_key_pem_size.to_le_bytes());
        
        // Final 24 bytes: version(2) + flags(2) + checksum(4) + magic(4) + lang_emoji(4) + type_emoji_1(4) + type_emoji_2(4)
        buf[96..98].copy_from_slice(&self.flavor_version.to_le_bytes());
        buf[98..100].copy_from_slice(&self.flags.to_le_bytes());
        buf[100..104].copy_from_slice(&self.footer_struct_checksum.to_le_bytes());
        buf[104..108].copy_from_slice(&self.internal_footer_magic.to_le_bytes());
        buf[108..112].copy_from_slice(&self.language_emoji);
        buf[112..116].copy_from_slice(&self.type_emoji_1);
        buf[116..120].copy_from_slice(&self.type_emoji_2);
        
        buf
    }
    
    pub fn from_bytes(data: &[u8]) -> Result<Self> {
        if data.len() != 120 {
            anyhow::bail!("Invalid footer size: {} bytes (expected 120)", data.len());
        }
        
        let footer = Self {
            uv_binary_offset: u64::from_le_bytes(data[0..8].try_into().unwrap()),
            uv_binary_size: u64::from_le_bytes(data[8..16].try_into().unwrap()),
            python_install_tgz_offset: u64::from_le_bytes(data[16..24].try_into().unwrap()),
            python_install_tgz_size: u64::from_le_bytes(data[24..32].try_into().unwrap()),
            metadata_tgz_offset: u64::from_le_bytes(data[32..40].try_into().unwrap()),
            metadata_tgz_size: u64::from_le_bytes(data[40..48].try_into().unwrap()),
            payload_tgz_offset: u64::from_le_bytes(data[48..56].try_into().unwrap()),
            payload_tgz_size: u64::from_le_bytes(data[56..64].try_into().unwrap()),
            package_signature_offset: u64::from_le_bytes(data[64..72].try_into().unwrap()),
            package_signature_size: u64::from_le_bytes(data[72..80].try_into().unwrap()),
            public_key_pem_offset: u64::from_le_bytes(data[80..88].try_into().unwrap()),
            public_key_pem_size: u64::from_le_bytes(data[88..96].try_into().unwrap()),
            flavor_version: u16::from_le_bytes(data[96..98].try_into().unwrap()),
            flags: u16::from_le_bytes(data[98..100].try_into().unwrap()),
            footer_struct_checksum: u32::from_le_bytes(data[100..104].try_into().unwrap()),
            internal_footer_magic: u32::from_le_bytes(data[104..108].try_into().unwrap()),
            language_emoji: data[108..112].try_into().unwrap(),
            type_emoji_1: data[112..116].try_into().unwrap(),
            type_emoji_2: data[116..120].try_into().unwrap(),
        };
        
        // Validate magic
        if footer.internal_footer_magic != FLAVOR_INTERNAL_FOOTER_MAGIC {
            anyhow::bail!(
                "Invalid internal footer magic number: expected {:08x}, got {:08x}",
                FLAVOR_INTERNAL_FOOTER_MAGIC,
                footer.internal_footer_magic
            );
        }
        
        // Validate version
        if footer.flavor_version != FLAVOR_VERSION {
            anyhow::bail!("Unsupported Flavor version: {}", footer.flavor_version);
        }
        
        // Validate checksum
        let calculated_checksum = footer.calculate_checksum();
        if footer.footer_struct_checksum != calculated_checksum {
            anyhow::bail!(
                "Footer checksum mismatch: expected {}, got {}",
                footer.footer_struct_checksum,
                calculated_checksum
            );
        }
        
        Ok(footer)
    }
}

pub fn read_footer_from_file<P: AsRef<Path>>(path: P) -> Result<(FlavorFooter, i64)> {
    let mut file = File::open(&path)
        .with_context(|| format!("Failed to open file: {:?}", path.as_ref()))?;
    
    let file_size = file.metadata()?.len() as i64;
    
    // Check EOF magic
    let mut eof_magic = vec![0u8; FLAVOR_MAGIC_EOF_STRING.len()];
    file.seek(SeekFrom::End(-(FLAVOR_MAGIC_EOF_STRING.len() as i64)))?;
    file.read_exact(&mut eof_magic)?;
    
    if eof_magic != FLAVOR_MAGIC_EOF_STRING {
        anyhow::bail!("Invalid EOF magic string");
    }
    
    // Read footer
    let footer_offset = file_size - FOOTER_SIZE - FLAVOR_MAGIC_EOF_STRING.len() as i64;
    if footer_offset < 0 {
        anyhow::bail!("File too small to contain valid footer");
    }
    
    file.seek(SeekFrom::Start(footer_offset as u64))?;
    let mut footer_bytes = vec![0u8; FOOTER_SIZE as usize];
    file.read_exact(&mut footer_bytes)?;
    
    let footer = FlavorFooter::from_bytes(&footer_bytes)?;
    
    // Calculate Flavor data offset
    let max_end = [
        footer.uv_binary_offset + footer.uv_binary_size,
        footer.python_install_tgz_offset + footer.python_install_tgz_size,
        footer.metadata_tgz_offset + footer.metadata_tgz_size,
        footer.payload_tgz_offset + footer.payload_tgz_size,
        footer.package_signature_offset + footer.package_signature_size,
        footer.public_key_pem_offset + footer.public_key_pem_size,
    ].iter().max().copied().unwrap_or(0);
    
    let total_flavor_size = max_end as i64 + FOOTER_SIZE + FLAVOR_MAGIC_EOF_STRING.len() as i64;
    let flavor_data_offset = file_size - total_flavor_size;
    
    Ok((footer, flavor_data_offset))
}


// 📦🍜📄🪄
