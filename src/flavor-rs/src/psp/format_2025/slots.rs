// helpers/flavor-rs/src/psp/format_2025/slots.rs
// PSPF 2025 Slot Management - Enhanced 64-byte descriptors

use super::constants::{LifecycleCache, PurposeData, SLOT_DESCRIPTOR_SIZE};
use super::defaults::{CACHE_NORMAL, DEFAULT_FILE_PERMS, DEFAULT_PAGE_SIZE};
use log::trace;
use std::path::PathBuf;

/// Slot descriptor - 64 bytes total
#[repr(C, packed)]
#[derive(Clone, Copy, Debug)]
pub struct SlotDescriptor {
    // Core fields (56 bytes total - 7x uint64)
    pub id: u64,            // Unique slot ID
    pub name_hash: u64,     // xxHash64 of slot name
    pub offset: u64,        // Byte offset in file
    pub size: u64,          // Size as stored (compressed)
    pub original_size: u64, // Uncompressed size
    pub operations: u64,    // Packed operation chain (up to 8 ops)
    pub checksum: u64,      // SHA256 checksum (first 8 bytes)

    // Metadata fields (8 bytes total - 8x uint8)
    pub purpose: u8,          // 0=data, 1=code, 2=config, 3=media
    pub lifecycle: u8,        // 0=init, 1=startup, 2=runtime, etc.
    pub priority: u8,         // 0-255 (higher = keep in memory)
    pub platform: u8,         // Platform requirements
    pub reserved1: u8,        // Reserved for future use
    pub reserved2: u8,        // Reserved for future use
    pub permissions: u8,      // Unix-style permissions (low byte)
    pub permissions_high: u8, // Unix-style permissions (high byte)
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
            operations: 0, // No operations (raw data)
            checksum: 0,
            purpose: PurposeData,
            lifecycle: LifecycleCache,
            priority: CACHE_NORMAL,
            platform: 0,
            reserved1: 0,
            reserved2: 0,
            permissions: (DEFAULT_FILE_PERMS & 0xFF) as u8,
            permissions_high: ((DEFAULT_FILE_PERMS >> 8) & 0xFF) as u8,
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
    pub fn pack(&self) -> [u8; SLOT_DESCRIPTOR_SIZE] {
        let mut bytes = [0u8; SLOT_DESCRIPTOR_SIZE];

        // Pack 7x uint64 fields (56 bytes)
        bytes[0..8].copy_from_slice(&self.id.to_le_bytes());
        bytes[8..16].copy_from_slice(&self.name_hash.to_le_bytes());
        bytes[16..24].copy_from_slice(&self.offset.to_le_bytes());
        bytes[24..32].copy_from_slice(&self.size.to_le_bytes());
        bytes[32..40].copy_from_slice(&self.original_size.to_le_bytes());
        bytes[40..48].copy_from_slice(&self.operations.to_le_bytes());

        let checksum_val = self.checksum; // Copy to avoid packed alignment issues
        let checksum_bytes = checksum_val.to_le_bytes();
        trace!(
            "🦀 Packing checksum: value={:016x}, bytes={:02x?}",
            checksum_val, checksum_bytes
        );
        bytes[48..56].copy_from_slice(&checksum_bytes);

        // Pack 8x uint8 fields (8 bytes)
        bytes[56] = self.purpose;
        bytes[57] = self.lifecycle;
        bytes[58] = self.priority;
        bytes[59] = self.platform;
        bytes[60] = self.reserved1;
        bytes[61] = self.reserved2;
        bytes[62] = self.permissions;
        bytes[63] = self.permissions_high;

        bytes
    }

    /// Unpack descriptor from bytes
    pub fn unpack(data: &[u8]) -> Option<Self> {
        if data.len() != SLOT_DESCRIPTOR_SIZE {
            return None;
        }

        use std::convert::TryInto;

        // Unpack 7x uint64 fields (56 bytes)
        let id = u64::from_le_bytes(data[0..8].try_into().ok()?);
        let name_hash = u64::from_le_bytes(data[8..16].try_into().ok()?);
        let offset = u64::from_le_bytes(data[16..24].try_into().ok()?);
        let size = u64::from_le_bytes(data[24..32].try_into().ok()?);
        let original_size = u64::from_le_bytes(data[32..40].try_into().ok()?);
        let operations = u64::from_le_bytes(data[40..48].try_into().ok()?);
        let checksum = u64::from_le_bytes(data[48..56].try_into().ok()?);

        // Unpack 8x uint8 fields (8 bytes)
        let purpose = data[56];
        let lifecycle = data[57];
        let priority = data[58];
        let platform = data[59];
        let reserved1 = data[60];
        let reserved2 = data[61];
        let permissions = data[62];
        let permissions_high = data[63];

        Some(SlotDescriptor {
            id,
            name_hash,
            offset,
            size,
            original_size,
            operations,
            checksum,
            purpose,
            lifecycle,
            priority,
            platform,
            reserved1,
            reserved2,
            permissions,
            permissions_high,
        })
    }
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
#[derive(Debug)]
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
    align_offset(offset, DEFAULT_PAGE_SIZE as u64)
}

// 📦🎰🗂️🪄
