// helpers/flavor-rs/src/psp/format_2025/index.rs
// PSPF 2025 Index Block - Future-proof 4096-byte Header

use super::constants::{HEADER_SIZE, PSPF_VERSION};
use crate::exceptions::{FlavorError, Result};

/// PSPF/2025 index structure (8192 bytes total)
#[repr(C, packed)]
#[derive(Clone, Debug)]
pub struct Index {
    // Core identification (8 bytes)
    pub format_version: u32, // 0x20250001
    pub index_checksum: u32, // Adler-32 of index block (with this field as 0)

    // File structure (48 bytes)
    pub package_size: u64,      // Total file size
    pub launcher_size: u64,     // Size of launcher binary
    pub metadata_offset: u64,   // Offset to metadata archive
    pub metadata_size: u64,     // Size of metadata archive
    pub slot_table_offset: u64, // Offset to slot table
    pub slot_table_size: u64,   // Size of slot table

    // Slot information (8 bytes)
    pub slot_count: u32, // Number of slots
    pub flags: u32,      // Feature flags

    // Security (576 bytes)
    pub public_key: [u8; 32], // Ed25519 public key for signature verification
    pub metadata_checksum: [u8; 32], // SHA256 of metadata
    pub integrity_signature: [u8; 512], // Signature of metadata (Ed25519 uses first 64 bytes)

    // Performance hints (64 bytes)
    pub access_mode: u8,        // 0=auto, 1=mmap, 2=file, 3=stream
    pub cache_strategy: u8,     // 0=none, 1=lazy, 2=eager, 3=critical
    pub encryption_type: u8,    // 0=none, 1=aes256-gcm, 2=chacha20
    pub reserved_hint: u8,      // Reserved for future use
    pub page_size: u32,         // Optimal page size for alignment
    pub max_memory: u64,        // Suggested maximum memory usage
    pub min_memory: u64,        // Minimum required memory
    pub cpu_features: u64,      // Required CPU features (bit flags)
    pub gpu_requirements: u64,  // GPU requirements (bit flags)
    pub numa_hints: u64,        // NUMA topology hints
    pub stream_chunk_size: u32, // Optimal streaming chunk size
    pub padding1: [u8; 12],     // Alignment padding

    // Extended metadata (128 bytes)
    pub build_timestamp: u64,      // Unix timestamp of build
    pub build_machine: [u8; 32],   // Build machine identifier
    pub source_hash: [u8; 32],     // Hash of source code/inputs
    pub dependency_hash: [u8; 32], // Hash of all dependencies
    pub license_id: [u8; 16],      // SPDX license identifier
    pub provenance_uri: [u8; 8],   // Short URI to provenance data

    // Capabilities (32 bytes)
    pub capabilities: u64,     // What this package can do
    pub requirements: u64,     // What this package needs
    pub extensions: u64,       // Extended features
    pub compatibility: u32,    // Minimum reader version
    pub protocol_version: u32, // Protocol version for negotiation

    // Future cryptography space (512 bytes)
    pub future_crypto: [u8; 512], // Reserved for post-quantum signatures

    // Reserved for future use (6808 bytes)
    pub reserved: [u8; 6816], // Large buffer for future expansion
}

impl Index {
    /// Create a new index with defaults
    pub fn new() -> Self {
        Index {
            format_version: PSPF_VERSION,
            index_checksum: 0,
            package_size: 0,
            launcher_size: 0,
            metadata_offset: 0,
            metadata_size: 0,
            slot_table_offset: 0,
            slot_table_size: 0,
            slot_count: 0,
            flags: 0,
            public_key: [0; 32],
            metadata_checksum: [0; 32],
            integrity_signature: [0; 512],
            access_mode: 0,
            cache_strategy: 0,
            encryption_type: 0,
            reserved_hint: 0,
            page_size: 4096,
            max_memory: 0,
            min_memory: 0,
            cpu_features: 0,
            gpu_requirements: 0,
            numa_hints: 0,
            stream_chunk_size: 0,
            padding1: [0; 12],
            build_timestamp: 0,
            build_machine: [0; 32],
            source_hash: [0; 32],
            dependency_hash: [0; 32],
            license_id: [0; 16],
            provenance_uri: [0; 8],
            capabilities: 0,
            requirements: 0,
            extensions: 0,
            compatibility: PSPF_VERSION,
            protocol_version: 1,
            future_crypto: [0; 512],
            reserved: [0; 6816],
        }
    }

    /// Unpack index from bytes
    pub fn unpack(data: &[u8]) -> Result<Self> {
        if data.len() != HEADER_SIZE {
            return Err(FlavorError::Generic(format!(
                "Invalid index size: {} != {}",
                data.len(),
                HEADER_SIZE
            )));
        }

        // Parse fields manually to ensure correct byte order
        use log::debug;
        use std::convert::TryInto;

        let mut index = Index::new();
        index.format_version = u32::from_le_bytes(
            data[0..4]
                .try_into()
                .map_err(|_| FlavorError::Generic("Invalid format version bytes".into()))?,
        );
        index.index_checksum = u32::from_le_bytes(
            data[4..8]
                .try_into()
                .map_err(|_| FlavorError::Generic("Invalid index checksum bytes".into()))?,
        );
        index.package_size = u64::from_le_bytes(
            data[8..16]
                .try_into()
                .map_err(|_| FlavorError::Generic("Invalid package size bytes".into()))?,
        );
        index.launcher_size = u64::from_le_bytes(
            data[16..24]
                .try_into()
                .map_err(|_| FlavorError::Generic("Invalid launcher size bytes".into()))?,
        );

        // Debug: Log the raw bytes we're parsing for metadata offset and size
        debug!(
            "Raw bytes at offset 24-32 (metadata_offset): {:02x?}",
            &data[24..32]
        );
        debug!(
            "Raw bytes at offset 32-40 (metadata_size): {:02x?}",
            &data[32..40]
        );

        index.metadata_offset = u64::from_le_bytes(
            data[24..32]
                .try_into()
                .map_err(|_| FlavorError::Generic("Invalid metadata offset bytes".into()))?,
        );
        index.metadata_size = u64::from_le_bytes(
            data[32..40]
                .try_into()
                .map_err(|_| FlavorError::Generic("Invalid metadata size bytes".into()))?,
        );

        // Copy to locals before logging to avoid alignment issues
        let meta_off = index.metadata_offset;
        let meta_sz = index.metadata_size;
        debug!("Parsed metadata_offset: 0x{:016x} ({})", meta_off, meta_off);
        debug!("Parsed metadata_size: {} bytes", meta_sz);
        index.slot_table_offset = u64::from_le_bytes(
            data[40..48]
                .try_into()
                .map_err(|_| FlavorError::Generic("Invalid slot table offset bytes".into()))?,
        );
        index.slot_table_size = u64::from_le_bytes(
            data[48..56]
                .try_into()
                .map_err(|_| FlavorError::Generic("Invalid slot table size bytes".into()))?,
        );
        index.slot_count = u32::from_le_bytes(
            data[56..60]
                .try_into()
                .map_err(|_| FlavorError::Generic("Invalid slot count bytes".into()))?,
        );
        index.flags = u32::from_le_bytes(
            data[60..64]
                .try_into()
                .map_err(|_| FlavorError::Generic("Invalid flags bytes".into()))?,
        );
        index.public_key.copy_from_slice(&data[64..96]);
        index.metadata_checksum.copy_from_slice(&data[96..128]);
        index.integrity_signature.copy_from_slice(&data[128..640]);

        // Parse performance hints
        index.access_mode = data[640];
        index.cache_strategy = data[641];
        index.encryption_type = data[642];
        index.reserved_hint = data[643];
        index.page_size = u32::from_le_bytes(
            data[644..648]
                .try_into()
                .map_err(|_| FlavorError::Generic("Invalid page size bytes".into()))?,
        );
        index.max_memory = u64::from_le_bytes(
            data[648..656]
                .try_into()
                .map_err(|_| FlavorError::Generic("Invalid max memory bytes".into()))?,
        );
        index.min_memory = u64::from_le_bytes(
            data[656..664]
                .try_into()
                .map_err(|_| FlavorError::Generic("Invalid min memory bytes".into()))?,
        );
        index.cpu_features = u64::from_le_bytes(
            data[664..672]
                .try_into()
                .map_err(|_| FlavorError::Generic("Invalid CPU features bytes".into()))?,
        );
        index.gpu_requirements = u64::from_le_bytes(
            data[672..680]
                .try_into()
                .map_err(|_| FlavorError::Generic("Invalid GPU requirements bytes".into()))?,
        );
        index.numa_hints = u64::from_le_bytes(
            data[680..688]
                .try_into()
                .map_err(|_| FlavorError::Generic("Invalid NUMA hints bytes".into()))?,
        );
        index.stream_chunk_size = u32::from_le_bytes(
            data[688..692]
                .try_into()
                .map_err(|_| FlavorError::Generic("Invalid stream chunk size bytes".into()))?,
        );
        index.padding1.copy_from_slice(&data[692..704]);

        // Parse extended metadata
        index.build_timestamp = u64::from_le_bytes(
            data[704..712]
                .try_into()
                .map_err(|_| FlavorError::Generic("Invalid build timestamp bytes".into()))?,
        );
        index.build_machine.copy_from_slice(&data[712..744]);
        index.source_hash.copy_from_slice(&data[744..776]);
        index.dependency_hash.copy_from_slice(&data[776..808]);
        index.license_id.copy_from_slice(&data[808..824]);
        index.provenance_uri.copy_from_slice(&data[824..832]);

        // Parse capabilities
        index.capabilities = u64::from_le_bytes(
            data[832..840]
                .try_into()
                .map_err(|_| FlavorError::Generic("Invalid capabilities bytes".into()))?,
        );
        index.requirements = u64::from_le_bytes(
            data[840..848]
                .try_into()
                .map_err(|_| FlavorError::Generic("Invalid requirements bytes".into()))?,
        );
        index.extensions = u64::from_le_bytes(
            data[848..856]
                .try_into()
                .map_err(|_| FlavorError::Generic("Invalid extensions bytes".into()))?,
        );
        index.compatibility = u32::from_le_bytes(
            data[856..860]
                .try_into()
                .map_err(|_| FlavorError::Generic("Invalid compatibility bytes".into()))?,
        );
        index.protocol_version = u32::from_le_bytes(
            data[860..864]
                .try_into()
                .map_err(|_| FlavorError::Generic("Invalid protocol version bytes".into()))?,
        );

        // Parse future crypto and reserved
        index.future_crypto.copy_from_slice(&data[864..1376]);
        index.reserved.copy_from_slice(&data[1376..8192]);

        Ok(index)
    }

    /// Pack index to bytes
    pub fn pack(&self) -> Vec<u8> {
        let mut bytes = vec![0u8; HEADER_SIZE];

        // Pack fields manually to ensure correct byte order
        bytes[0..4].copy_from_slice(&self.format_version.to_le_bytes());
        bytes[4..8].copy_from_slice(&self.index_checksum.to_le_bytes());
        bytes[8..16].copy_from_slice(&self.package_size.to_le_bytes());
        bytes[16..24].copy_from_slice(&self.launcher_size.to_le_bytes());
        bytes[24..32].copy_from_slice(&self.metadata_offset.to_le_bytes());
        bytes[32..40].copy_from_slice(&self.metadata_size.to_le_bytes());
        bytes[40..48].copy_from_slice(&self.slot_table_offset.to_le_bytes());
        bytes[48..56].copy_from_slice(&self.slot_table_size.to_le_bytes());
        bytes[56..60].copy_from_slice(&self.slot_count.to_le_bytes());
        bytes[60..64].copy_from_slice(&self.flags.to_le_bytes());
        bytes[64..96].copy_from_slice(&self.public_key);
        bytes[96..128].copy_from_slice(&self.metadata_checksum);
        bytes[128..640].copy_from_slice(&self.integrity_signature);

        // Pack performance hints
        bytes[640] = self.access_mode;
        bytes[641] = self.cache_strategy;
        bytes[642] = self.encryption_type;
        bytes[643] = self.reserved_hint;
        bytes[644..648].copy_from_slice(&self.page_size.to_le_bytes());
        bytes[648..656].copy_from_slice(&self.max_memory.to_le_bytes());
        bytes[656..664].copy_from_slice(&self.min_memory.to_le_bytes());
        bytes[664..672].copy_from_slice(&self.cpu_features.to_le_bytes());
        bytes[672..680].copy_from_slice(&self.gpu_requirements.to_le_bytes());
        bytes[680..688].copy_from_slice(&self.numa_hints.to_le_bytes());
        bytes[688..692].copy_from_slice(&self.stream_chunk_size.to_le_bytes());
        bytes[692..704].copy_from_slice(&self.padding1);

        // Pack extended metadata
        bytes[704..712].copy_from_slice(&self.build_timestamp.to_le_bytes());
        bytes[712..744].copy_from_slice(&self.build_machine);
        bytes[744..776].copy_from_slice(&self.source_hash);
        bytes[776..808].copy_from_slice(&self.dependency_hash);
        bytes[808..824].copy_from_slice(&self.license_id);
        bytes[824..832].copy_from_slice(&self.provenance_uri);

        // Pack capabilities
        bytes[832..840].copy_from_slice(&self.capabilities.to_le_bytes());
        bytes[840..848].copy_from_slice(&self.requirements.to_le_bytes());
        bytes[848..856].copy_from_slice(&self.extensions.to_le_bytes());
        bytes[856..860].copy_from_slice(&self.compatibility.to_le_bytes());
        bytes[860..864].copy_from_slice(&self.protocol_version.to_le_bytes());

        // Pack future crypto and reserved
        bytes[864..1376].copy_from_slice(&self.future_crypto);
        bytes[1376..8192].copy_from_slice(&self.reserved);

        // Calculate and update checksum (with checksum field zeroed)
        bytes[4..8].copy_from_slice(&[0, 0, 0, 0]);
        let checksum = adler::adler32_slice(&bytes[..]);
        bytes[4..8].copy_from_slice(&checksum.to_le_bytes());

        bytes
    }

    /// Verify index checksum against raw data
    pub fn verify_checksum_raw(&self, raw_data: &[u8]) -> bool {
        use log::debug;

        if raw_data.len() != HEADER_SIZE {
            let size = raw_data.len();
            debug!("Index size mismatch: {} != {}", size, HEADER_SIZE);
            return false;
        }

        // Make a copy to zero out checksum field
        let mut data_copy = raw_data.to_vec();

        // Log the checksum bytes before zeroing
        let checksum_bytes = &raw_data[4..8];
        debug!(
            "Checksum bytes in index: {:02x} {:02x} {:02x} {:02x}",
            checksum_bytes[0], checksum_bytes[1], checksum_bytes[2], checksum_bytes[3]
        );

        data_copy[4..8].copy_from_slice(&[0, 0, 0, 0]);

        // Log first 72 bytes of the index (core fields)
        debug!("First 72 bytes of index (with checksum zeroed):");
        let mut hex_line = String::new();
        for (i, byte) in data_copy.iter().enumerate().take(72) {
            if i % 16 == 0 {
                if !hex_line.is_empty() {
                    debug!("{hex_line}");
                    hex_line.clear();
                }
                hex_line = format!("  {:04x}: ", i);
            }
            hex_line.push_str(&format!("{byte:02x} "));
        }
        if !hex_line.is_empty() {
            debug!("{hex_line}");
        }

        let calculated = adler::adler32_slice(&data_copy);
        let expected = self.index_checksum;
        debug!(
            "Checksum verification - Expected: {} (0x{:08x}), Calculated: {} (0x{:08x})",
            expected, expected, calculated, calculated
        );
        calculated == expected
    }

    /// Verify index checksum (deprecated - use verify_checksum_raw)
    pub fn verify_checksum(&self) -> bool {
        let mut bytes = self.pack();

        // Zero out checksum field (bytes 4-8)
        bytes[4..8].copy_from_slice(&[0, 0, 0, 0]);

        let calculated = adler::adler32_slice(&bytes[..]);
        calculated == self.index_checksum
    }
}

impl Default for Index {
    fn default() -> Self {
        Self::new()
    }
}

// 📦🔧🏗️🪄
