//! PSPF bundle reading and extraction functionality

use anyhow::{anyhow, Context, Result};
use flavor_common::{PSPFIndex, INDEX_SIZE};
use flate2::read::GzDecoder;
use sha2::{Digest, Sha256};
use std::fs::File;
use std::io::{Read, Seek, SeekFrom};
use std::path::{Path, PathBuf};
use tar::Archive;

use crate::metadata::Metadata;

/// Reader for PSPF bundles
pub struct Reader {
    pub file: File,
}

impl Reader {
    /// Create a new reader for a PSPF bundle
    pub fn new(path: &Path) -> Result<Self> {
        let file = File::open(path)
            .with_context(|| format!("Failed to open bundle: {:?}", path))?;
        Ok(Self {
            file,
        })
    }

    /// Read the PSPF index from the bundle
    pub fn read_index(&mut self) -> Result<PSPFIndex> {
        // Read launcher size to find index location
        let launcher_size = self.detect_launcher_size()?;
        
        // Seek to index position
        self.file.seek(SeekFrom::Start(launcher_size))?;
        
        // Read index bytes
        let mut index_bytes = vec![0u8; INDEX_SIZE as usize];
        self.file.read_exact(&mut index_bytes)?;
        
        // Parse index manually from bytes
        let mut index = PSPFIndex {
            format_magic: [0; 8],
            format_version: 0,
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
        };

        index.format_magic.copy_from_slice(&index_bytes[0..8]);
        index.format_version = u32::from_le_bytes(index_bytes[8..12].try_into()?);
        index.index_checksum = u32::from_le_bytes(index_bytes[12..16].try_into()?);
        index.package_size = u64::from_le_bytes(index_bytes[16..24].try_into()?);
        index.launcher_size = u64::from_le_bytes(index_bytes[24..32].try_into()?);
        index.metadata_offset = u64::from_le_bytes(index_bytes[32..40].try_into()?);
        index.metadata_size = u64::from_le_bytes(index_bytes[40..48].try_into()?);
        index.slot_table_offset = u64::from_le_bytes(index_bytes[48..56].try_into()?);
        index.slot_table_size = u64::from_le_bytes(index_bytes[56..64].try_into()?);
        index.slot_count = u32::from_le_bytes(index_bytes[64..68].try_into()?);
        index.flags = u32::from_le_bytes(index_bytes[68..72].try_into()?);
        index.ephemeral_public_key.copy_from_slice(&index_bytes[72..104]);
        index.metadata_checksum.copy_from_slice(&index_bytes[104..136]);
        index.reserved.copy_from_slice(&index_bytes[136..256]);
        
        // Verify magic
        if &index.format_magic != b"PSPF2025" {
            return Err(anyhow!("Invalid PSPF magic"));
        }
        
        Ok(index)
    }

    /// Read and parse metadata from the bundle
    pub fn read_metadata(&mut self) -> Result<Metadata> {
        let index = self.read_index()?;
        
        // Read metadata archive
        self.file.seek(SeekFrom::Start(index.metadata_offset))?;
        let mut metadata_data = vec![0u8; index.metadata_size as usize];
        self.file.read_exact(&mut metadata_data)?;
        
        // Verify metadata checksum
        let calculated_checksum = Sha256::digest(&metadata_data);
        if calculated_checksum.as_slice() != &index.metadata_checksum {
            log::warn!("Metadata checksum mismatch");
        }
        
        // Extract metadata from tar.gz
        let gz = GzDecoder::new(&metadata_data[..]);
        let mut tar = Archive::new(gz);
        
        for entry in tar.entries()? {
            let mut entry = entry?;
            let path = entry.path()?;
            
            if path.to_str() == Some("psp.json") {
                let mut content = String::new();
                entry.read_to_string(&mut content)?;
                let metadata: Metadata = serde_json::from_str(&content)
                    .context("Failed to parse metadata JSON")?;
                log::debug!("✅ Successfully parsed metadata for package: {} v{}", 
                    metadata.package.name, metadata.package.version);
                return Ok(metadata);
            }
        }
        
        Err(anyhow!("Metadata not found in archive"))
    }

    /// Extract a slot to a directory
    pub fn extract_slot(&mut self, slot_index: usize, output_dir: &Path) -> Result<PathBuf> {
        let index = self.read_index()?;
        let metadata = self.read_metadata()?;
        
        if slot_index >= metadata.slots.len() {
            return Err(anyhow!("Slot index {} out of range", slot_index));
        }
        
        let slot = &metadata.slots[slot_index];
        
        // Read slot table to get offset
        self.file.seek(SeekFrom::Start(index.slot_table_offset))?;
        
        // Each slot entry is 24 bytes
        let slot_entry_offset = index.slot_table_offset + (slot_index as u64 * 24);
        self.file.seek(SeekFrom::Start(slot_entry_offset))?;
        
        let mut offset_bytes = [0u8; 8];
        self.file.read_exact(&mut offset_bytes)?;
        let slot_offset = u64::from_le_bytes(offset_bytes);
        
        // Read slot data
        self.file.seek(SeekFrom::Start(slot_offset))?;
        let mut slot_data = vec![0u8; slot.size as usize];
        self.file.read_exact(&mut slot_data)?;
        
        // Determine output path based on extract_to
        let extract_path = if let Some(ref extract_to) = slot.extract_to {
            if extract_to == "." {
                output_dir.to_path_buf()
            } else {
                output_dir.join(extract_to)
            }
        } else {
            output_dir.join(&slot.name)
        };
        
        // Create parent directories
        if let Some(parent) = extract_path.parent() {
            std::fs::create_dir_all(parent)?;
        }
        
        // Handle different encodings and formats
        match slot.encoding.as_str() {
            "gzip" => {
                // Decompress first to check if it's a tar
                let mut gz = GzDecoder::new(&slot_data[..]);
                let mut decompressed = Vec::new();
                gz.read_to_end(&mut decompressed)?;
                
                // Check if the decompressed data is a tar archive
                if is_tar(&decompressed) {
                    // It's a tar archive - extract it
                    log::debug!("📦 Slot {} is a tarball, extracting...", slot_index);
                    let mut tar = Archive::new(&decompressed[..]);
                    tar.unpack(&extract_path)?;
                } else {
                    // Just a gzipped file - write it
                    // If extract_to is "." and it's not a tar, we still need a filename
                    let file_path = if slot.extract_to.as_deref() == Some(".") {
                        output_dir.join(&slot.name)
                    } else {
                        extract_path.clone()
                    };
                    std::fs::write(&file_path, decompressed)?;
                }
            },
            _ => {
                // Check if it's an uncompressed tar
                if is_tar(&slot_data) {
                    log::debug!("📦 Slot {} is an uncompressed tarball, extracting...", slot_index);
                    let mut tar = Archive::new(&slot_data[..]);
                    tar.unpack(&extract_path)?;
                } else {
                    // Just write the file as-is
                    std::fs::write(&extract_path, slot_data)?;
                }
            }
        }
        
        Ok(extract_path)
    }

    /// Verify the magic emoji at the end of the bundle
    pub fn verify_magic(&mut self) -> Result<()> {
        // Seek to end minus 4 bytes (emoji size)
        self.file.seek(SeekFrom::End(-4))?;
        
        let mut magic = [0u8; 4];
        self.file.read_exact(&mut magic)?;
        
        // Check for magic wand emoji 🪄 (U+1FA84)
        if magic != [0xF0, 0x9F, 0xAA, 0x84] {
            return Err(anyhow!("Invalid magic emoji"));
        }
        
        Ok(())
    }

    /// Detect launcher size by looking for PSPF magic
    fn detect_launcher_size(&mut self) -> Result<u64> {
        const SEARCH_WINDOW: usize = 1024 * 1024 * 10; // 10MB max launcher size
        const CHUNK_SIZE: usize = 4096;
        
        let mut buffer = vec![0u8; CHUNK_SIZE];
        let mut position = 0u64;
        
        self.file.seek(SeekFrom::Start(0))?;
        
        while position < SEARCH_WINDOW as u64 {
            let bytes_read = self.file.read(&mut buffer)?;
            if bytes_read == 0 {
                break;
            }
            
            // Look for PSPF2025 magic
            if let Some(idx) = buffer.windows(8)
                .position(|w| w == b"PSPF2025") {
                return Ok(position + idx as u64);
            }
            
            position += bytes_read as u64;
            
            // Overlap to handle boundary cases
            if bytes_read == CHUNK_SIZE {
                self.file.seek(SeekFrom::Current(-8))?;
                position -= 8;
            }
        }
        
        Err(anyhow!("PSPF magic not found"))
    }
}

/// Check if data looks like a tar archive
fn is_tar(data: &[u8]) -> bool {
    // Tar files have "ustar" at offset 257
    if data.len() > 262 {
        &data[257..262] == b"ustar"
    } else {
        false
    }
}