// helpers/flavor-rs/src/psp/format_2025/slots.rs
// PSPF 2025 Slot Management - Enhanced 64-byte descriptors

use super::constants::*;
use std::path::PathBuf;

/// Slot descriptor - 64 bytes total
#[repr(C, packed)]
#[derive(Clone, Copy, Debug)]
pub struct SlotDescriptor {
    // Identity (16 bytes)
    pub id: u64,        // Unique slot ID
    pub name_hash: u64, // xxHash64 of slot name

    // Location (16 bytes)
    pub offset: u64, // Byte offset in file
    pub size: u64,   // Size as stored (compressed)

    // Properties (16 bytes)
    pub original_size: u64, // Uncompressed size
    pub checksum: u32,      // Adler-32 of stored data
    pub encoding: u8,       // 0=raw, 1=tar, 2=gzip, 3=tgz
    pub encryption: u8,     // 0=none, 1=aes256-gcm
    pub alignment: u16,     // Required alignment

    // Semantics (8 bytes)
    pub purpose: u8,      // 0=data, 1=code, 2=config, 3=media
    pub lifecycle: u8,    // 0=permanent, 1=cached, 2=temporary
    pub access_hint: u8,  // 0=sequential, 1=random, 2=once
    pub priority: u8,     // 0-255 (higher = keep in memory)
    pub permissions: u16, // Unix-style permissions
    pub platform: u16,    // Platform requirements

    // Extended info (8 bytes)
    pub extended_offset: u32, // Offset to extended metadata
    pub extended_size: u32,   // Size of extended metadata
}

impl SlotDescriptor {
    /// Create a new slot descriptor
    pub fn new(id: u64) -> Self {
        SlotDescriptor {
            id,
            name_hash: 0,
            offset: 0,
            size: 0,
            original_size: 0,
            checksum: 0,
            encoding: ENCODING_RAW,
            encryption: 0,
            alignment: SLOT_ALIGNMENT as u16,
            purpose: PURPOSE_PAYLOAD,
            lifecycle: LIFECYCLE_CACHE,
            access_hint: ACCESS_HINT_SEQUENTIAL,
            priority: CACHE_NORMAL,
            permissions: 0o644,
            platform: 0,
            extended_offset: 0,
            extended_size: 0,
        }
    }

    /// Hash a slot name using SHA256 (first 8 bytes)
    pub fn hash_name(name: &str) -> u64 {
        use sha2::{Digest, Sha256};

        let mut hasher = Sha256::new();
        hasher.update(name.as_bytes());
        let result = hasher.finalize();

        // Take first 8 bytes as u64
        let mut bytes = [0u8; 8];
        bytes.copy_from_slice(&result[..8]);
        u64::from_le_bytes(bytes)
    }

    /// Set the slot name and compute hash
    pub fn with_name(mut self, name: &str) -> Self {
        self.name_hash = Self::hash_name(name);
        self
    }

    /// Pack descriptor to bytes
    pub fn to_bytes(&self) -> [u8; SLOT_DESCRIPTOR_SIZE] {
        let mut bytes = [0u8; SLOT_DESCRIPTOR_SIZE];

        // Safety: We're writing to a properly sized buffer
        unsafe {
            std::ptr::write_unaligned(bytes.as_mut_ptr() as *mut SlotDescriptor, *self);
        }

        bytes
    }

    /// Parse descriptor from bytes
    pub fn from_bytes(data: &[u8]) -> Option<Self> {
        if data.len() != SLOT_DESCRIPTOR_SIZE {
            return None;
        }

        // Safety: We've verified the size matches our struct
        let descriptor =
            unsafe { std::ptr::read_unaligned(data.as_ptr() as *const SlotDescriptor) };

        Some(descriptor)
    }
}


/// Slot encoding types
#[repr(u8)]
#[derive(Clone, Copy, Debug, PartialEq)]
pub enum Encoding {
    None = 0,
    Gzip = 1,
    Zstd = 2,
    Brotli = 3,
}

/// Slot purpose types
#[repr(u8)]
#[derive(Clone, Copy, Debug, PartialEq)]
pub enum Purpose {
    Data = 0,
    Code = 1,
    Config = 2,
    Media = 3,
}

/// Slot lifecycle types
#[repr(u8)]
#[derive(Clone, Copy, Debug, PartialEq)]
pub enum Lifecycle {
    Permanent = 0,
    Cached = 1,
    Temporary = 2,
    Stream = 3,
}

/// Slot metadata for runtime use
pub struct SlotMetadata {
    pub descriptor: SlotDescriptor,
    pub name: String,
    pub path: Option<PathBuf>,
}

impl SlotMetadata {
    /// Create new metadata from descriptor
    pub fn new(descriptor: SlotDescriptor, name: String) -> Self {
        SlotMetadata {
            descriptor,
            name,
            path: None,
        }
    }

    /// Set the source path
    pub fn with_path(mut self, path: PathBuf) -> Self {
        self.path = Some(path);
        self
    }
}

/// Align offset to boundary
pub fn align_offset(offset: u64, alignment: u64) -> u64 {
    (offset + alignment - 1) & !(alignment - 1)
}

/// Align offset to page boundary for optimal mmap
pub fn align_to_page(offset: u64) -> u64 {
    align_offset(offset, PAGE_SIZE as u64)
}

// 📦🎰🗂️🪄
