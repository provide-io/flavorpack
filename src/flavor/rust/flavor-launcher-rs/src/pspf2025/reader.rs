//! PSPF 2025 Bundle Reader

use crate::{
    errors::{FlavorError, Result},
    spec::*,
    EMOJI_MAGIC_SIZE, INDEX_SIZE, PSPF_MAGIC,
};
use flate2::read::GzDecoder;
use std::fs::File;
use std::io::{self, Read, Seek, SeekFrom};
use std::path::{Path, PathBuf};
use tar::Archive;

pub struct Reader {
    bundle_path: PathBuf,
    file: Option<File>,
    index: Option<PSPFIndex>,
    metadata: Option<Metadata>,
}

impl Reader {
    pub fn new(bundle_path: impl AsRef<Path>) -> Result<Self> {
        Ok(Self {
            bundle_path: bundle_path.as_ref().to_path_buf(),
            file: None,
            index: None,
            metadata: None,
        })
    }

    pub fn open(&mut self) -> Result<()> {
        if self.file.is_none() {
            self.file = Some(File::open(&self.bundle_path)?);
        }
        Ok(())
    }

    pub fn verify_magic(&mut self) -> Result<bool> {
        self.open()?;
        let file = self.file.as_mut().unwrap();
        
        // Seek to end minus emoji magic size
        file.seek(SeekFrom::End(-(EMOJI_MAGIC_SIZE as i64)))?;
        
        let mut magic = vec![0u8; EMOJI_MAGIC_SIZE];
        file.read_exact(&mut magic)?;
        
        // Check for package emoji and magic wand
        let magic_str = String::from_utf8_lossy(&magic);
        Ok(magic_str.contains("📦") && magic_str.contains("🪄"))
    }

    pub fn detect_launcher_size(&mut self) -> Result<u64> {
        self.open()?;
        let file = self.file.as_mut().unwrap();
        
        // Read first 1MB to search for PSPF magic
        file.seek(SeekFrom::Start(0))?;
        let mut data = vec![0u8; 1024 * 1024];
        let bytes_read = file.read(&mut data)?;
        data.truncate(bytes_read);
        
        // Search for PSPF magic
        if let Some(pos) = data.windows(8).position(|w| w == PSPF_MAGIC) {
            return Ok(pos as u64);
        }
        
        Err(FlavorError::InvalidMagic)
    }

    pub fn read_index(&mut self) -> Result<&PSPFIndex> {
        if self.index.is_some() {
            return Ok(self.index.as_ref().unwrap());
        }
        
        self.open()?;
        let launcher_size = self.detect_launcher_size()?;
        
        let file = self.file.as_mut().unwrap();
        file.seek(SeekFrom::Start(launcher_size))?;
        
        let mut index_data = vec![0u8; INDEX_SIZE];
        file.read_exact(&mut index_data)?;
        
        let index = PSPFIndex::unpack(&index_data)?;
        self.index = Some(index);
        
        Ok(self.index.as_ref().unwrap())
    }

    pub fn read_metadata(&mut self) -> Result<&Metadata> {
        if self.metadata.is_some() {
            return Ok(self.metadata.as_ref().unwrap());
        }
        
        let index = self.read_index()?.clone();
        self.open()?;
        
        let file = self.file.as_mut().unwrap();
        file.seek(SeekFrom::Start(index.metadata_offset))?;
        
        let mut archive_data = vec![0u8; index.metadata_size as usize];
        file.read_exact(&mut archive_data)?;
        
        // Extract psp.json from archive
        let decoder = GzDecoder::new(&archive_data[..]);
        let mut archive = Archive::new(decoder);
        
        for entry in archive.entries()? {
            let mut entry = entry?;
            if entry.path()?.to_str() == Some("psp.json") {
                let mut contents = String::new();
                entry.read_to_string(&mut contents)?;
                let metadata: Metadata = serde_json::from_str(&contents)?;
                self.metadata = Some(metadata);
                return Ok(self.metadata.as_ref().unwrap());
            }
        }
        
        Err(FlavorError::InvalidData("psp.json not found in metadata archive".to_string()))
    }

    pub fn read_slot(&mut self, slot_index: usize) -> Result<Vec<u8>> {
        let index = self.read_index()?.clone();
        
        if slot_index >= index.slot_count as usize {
            return Err(FlavorError::InvalidSlotIndex);
        }
        
        self.open()?;
        let file = self.file.as_mut().unwrap();
        
        // Read slot table entry
        let slot_table_entry_offset = index.slot_table_offset + (slot_index as u64 * 20);
        file.seek(SeekFrom::Start(slot_table_entry_offset))?;
        
        let mut entry_data = vec![0u8; 20];
        file.read_exact(&mut entry_data)?;
        
        let offset = u64::from_le_bytes(entry_data[0..8].try_into().unwrap());
        let size = u64::from_le_bytes(entry_data[8..16].try_into().unwrap());
        let checksum = u32::from_le_bytes(entry_data[16..20].try_into().unwrap());
        
        // Read slot data
        file.seek(SeekFrom::Start(offset))?;
        let mut slot_data = vec![0u8; size as usize];
        file.read_exact(&mut slot_data)?;
        
        // Verify checksum
        if adler32::adler32(&slot_data).unwrap() != checksum {
            return Err(FlavorError::ChecksumMismatch);
        }
        
        Ok(slot_data)
    }

    pub fn extract_slot(&mut self, slot_index: usize, dest_dir: &Path) -> Result<PathBuf> {
        let metadata = self.read_metadata()?.clone();
        
        if let Some(slots) = &metadata.slots {
            if slot_index >= slots.len() {
                return Err(FlavorError::InvalidSlotIndex);
            }
            
            let slot_meta = &slots[slot_index];
            let slot_data = self.read_slot(slot_index)?;
            
            // Decompress if needed
            let decompressed = match slot_meta.compression.as_str() {
                "gzip" => {
                    let mut decoder = GzDecoder::new(&slot_data[..]);
                    let mut decompressed = Vec::new();
                    decoder.read_to_end(&mut decompressed)?;
                    decompressed
                }
                "none" => slot_data,
                _ => slot_data,
            };
            
            // Write to destination
            let dest_path = dest_dir.join(&slot_meta.name);
            if let Some(parent) = dest_path.parent() {
                std::fs::create_dir_all(parent)?;
            }
            
            std::fs::write(&dest_path, decompressed)?;
            
            Ok(dest_path)
        } else {
            Err(FlavorError::SlotNotFound)
        }
    }

    pub fn verify_all_checksums(&mut self) -> Result<()> {
        let index = self.read_index()?.clone();
        
        for i in 0..index.slot_count as usize {
            self.read_slot(i)?;
        }
        
        Ok(())
    }
}