//! PSPF 2025 Bundle Builder

use super::{
    errors::{FlavorError, Result},
    spec::*,
    EMOJI_MAGIC_SIZE, INDEX_SIZE, PSPF_MAGIC, PSPF_VERSION, RANDOM_EMOJIS, SLOT_ALIGNMENT,
};
use flate2::write::GzEncoder;
use flate2::Compression;
use rand::Rng;
use sha2::{Digest, Sha256};
use std::fs::{self, File};
use std::io::{self, Seek, SeekFrom, Write};
use std::path::{Path, PathBuf};
use tar::Builder as TarBuilder;

pub struct Builder {
    temp_dir: PathBuf,
}

impl Builder {
    pub fn new() -> Result<Self> {
        let temp_dir = std::env::temp_dir().join(format!("pspf-build-{}", std::process::id()));
        fs::create_dir_all(&temp_dir)?;
        
        Ok(Self { temp_dir })
    }

    pub fn build(
        &self,
        output_path: &Path,
        metadata: &Metadata,
        slots: &[SlotMetadata],
        launcher_type: &str,
        emoji_seed: Option<&str>,
    ) -> Result<()> {
        // Generate ephemeral keys
        let (private_key, public_key) = generate_ephemeral_key_pair()?;
        
        // Get launcher binary
        let launcher_data = self.get_launcher(launcher_type)?;
        let launcher_size = launcher_data.len() as u64;
        
        // Create output file
        let mut out = File::create(output_path)?;
        
        // Write launcher
        out.write_all(&launcher_data)?;
        
        // Create index
        let mut index = PSPFIndex::new();
        index.launcher_size = launcher_size;
        index.ephemeral_public_key = public_key;
        
        // Skip index block space
        let index_offset = launcher_size;
        out.seek(SeekFrom::Start(index_offset + INDEX_SIZE as u64))?;
        
        // Write metadata archive
        let metadata_offset = out.stream_position()?;
        let metadata_size = self.write_metadata(&mut out, metadata, &private_key, &public_key)?;
        
        index.metadata_offset = metadata_offset;
        index.metadata_size = metadata_size;
        
        // Calculate metadata checksum
        let metadata_bytes = serde_json::to_vec(metadata)?;
        let mut hasher = Sha256::new();
        hasher.update(&metadata_bytes);
        let metadata_hash = hasher.finalize();
        index.metadata_checksum.copy_from_slice(&metadata_hash);
        
        // Write slots
        if !slots.is_empty() {
            let (slot_table_data, slot_table_offset) = self.write_slots(&mut out, slots)?;
            index.slot_table_offset = slot_table_offset;
            index.slot_table_size = slot_table_data.len() as u64;
            index.slot_count = slots.len() as u32;
        }
        
        // Write emoji magic
        let emoji_magic = generate_emoji_magic(launcher_type, emoji_seed);
        out.write_all(&emoji_magic)?;
        
        // Update package size
        let final_pos = out.stream_position()?;
        index.package_size = final_pos;
        
        // Write index block
        out.seek(SeekFrom::Start(index_offset))?;
        let index_bytes = index.pack();
        out.write_all(&index_bytes)?;
        
        // Ensure all data is written
        out.sync_all()?;
        
        Ok(())
    }

    fn get_launcher(&self, launcher_type: &str) -> Result<Vec<u8>> {
        // Mock implementation - in production, would return actual launcher binary
        Ok(format!("LAUNCHER_BINARY_{}\0", launcher_type).into_bytes())
    }

    fn write_metadata(
        &self,
        writer: &mut (impl Write + Seek),
        metadata: &Metadata,
        private_key: &[u8; 32],
        public_key: &[u8; 32],
    ) -> Result<u64> {
        let _start_pos = writer.stream_position()?;
        
        // Create metadata archive in memory
        let archive_data = self.create_metadata_archive(metadata, private_key, public_key)?;
        writer.write_all(&archive_data)?;
        
        Ok(archive_data.len() as u64)
    }

    fn create_metadata_archive(
        &self,
        metadata: &Metadata,
        private_key: &[u8; 32],
        public_key: &[u8; 32],
    ) -> Result<Vec<u8>> {
        let mut archive_buf = Vec::new();
        
        {
            let encoder = GzEncoder::new(&mut archive_buf, Compression::default());
            let mut tar = TarBuilder::new(encoder);
            
            // Add psp.json
            let psp_data = serde_json::to_vec_pretty(metadata)?;
            let mut header = tar::Header::new_gnu();
            header.set_path("psp.json")?;
            header.set_size(psp_data.len() as u64);
            header.set_mode(0o644);
            header.set_cksum();
            tar.append(&header, &psp_data[..])?;
            
            // Add integrity seal
            let seal_sig = sign_data(&psp_data, private_key);
            let mut sig_header = tar::Header::new_gnu();
            sig_header.set_path("integrity/seal.sig")?;
            sig_header.set_size(seal_sig.len() as u64);
            sig_header.set_mode(0o644);
            sig_header.set_cksum();
            tar.append(&sig_header, &seal_sig[..])?;
            
            // Add public key
            let mut key_header = tar::Header::new_gnu();
            key_header.set_path("integrity/seal.pem")?;
            key_header.set_size(public_key.len() as u64);
            key_header.set_mode(0o644);
            key_header.set_cksum();
            tar.append(&key_header, &public_key[..])?;
            
            tar.finish()?;
        }
        
        Ok(archive_buf)
    }

    fn write_slots(
        &self,
        writer: &mut (impl Write + Seek),
        slots: &[SlotMetadata],
    ) -> Result<(Vec<u8>, u64)> {
        let mut slot_entries = Vec::new();
        
        for slot in slots {
            // Align to 8-byte boundary
            let current_pos = writer.stream_position()?;
            let aligned_pos = align_offset(current_pos, SLOT_ALIGNMENT);
            if aligned_pos > current_pos {
                let padding = vec![0u8; (aligned_pos - current_pos) as usize];
                writer.write_all(&padding)?;
            }
            
            let slot_offset = aligned_pos;
            let slot_data = self.compress_slot(slot)?;
            writer.write_all(&slot_data)?;
            
            let checksum = adler32::adler32(slot_data.as_slice()).unwrap();
            
            slot_entries.push(SlotTableEntry {
                offset: slot_offset,
                size: slot_data.len() as u64,
                checksum,
            });
        }
        
        // Write slot table
        let current_pos = writer.stream_position()?;
        let slot_table_offset = align_offset(current_pos, SLOT_ALIGNMENT);
        writer.seek(SeekFrom::Start(slot_table_offset))?;
        
        let mut slot_table_buf = Vec::new();
        for entry in &slot_entries {
            slot_table_buf.extend_from_slice(&entry.offset.to_le_bytes());
            slot_table_buf.extend_from_slice(&entry.size.to_le_bytes());
            slot_table_buf.extend_from_slice(&entry.checksum.to_le_bytes());
        }
        
        writer.write_all(&slot_table_buf)?;
        
        Ok((slot_table_buf, slot_table_offset))
    }

    fn compress_slot(&self, slot: &SlotMetadata) -> Result<Vec<u8>> {
        // Mock implementation - in production would read from slot path
        let data = format!("SLOT_DATA_{}", slot.name).into_bytes();
        
        match slot.compression.as_str() {
            "gzip" => {
                let mut encoder = GzEncoder::new(Vec::new(), Compression::default());
                encoder.write_all(&data)?;
                Ok(encoder.finish()?)
            }
            "none" => Ok(data),
            _ => Ok(data),
        }
    }
}

impl Drop for Builder {
    fn drop(&mut self) {
        // Clean up temp directory
        let _ = fs::remove_dir_all(&self.temp_dir);
    }
}

fn generate_ephemeral_key_pair() -> Result<([u8; 32], [u8; 32])> {
    // Mock implementation - in production would use real crypto
    let mut rng = rand::thread_rng();
    let mut private_key = [0u8; 32];
    let mut public_key = [0u8; 32];
    
    rng.fill(&mut private_key);
    rng.fill(&mut public_key);
    
    Ok((private_key, public_key))
}

fn sign_data(data: &[u8], private_key: &[u8; 32]) -> Vec<u8> {
    // Mock implementation - in production would use real crypto
    let mut hasher = Sha256::new();
    hasher.update(data);
    hasher.update(private_key);
    hasher.finalize().to_vec()
}

fn generate_emoji_magic(launcher_type: &str, emoji_seed: Option<&str>) -> Vec<u8> {
    let package_emoji = "📦";
    let launcher_emoji = launcher_emoji(launcher_type);
    
    let random_emoji = if let Some(seed) = emoji_seed {
        seed
    } else {
        let mut rng = rand::thread_rng();
        RANDOM_EMOJIS[rng.gen_range(0..RANDOM_EMOJIS.len())]
    };
    
    let magic_wand = "🪄";
    
    let emoji_magic = format!("{}{}{}{}", package_emoji, launcher_emoji, random_emoji, magic_wand);
    let mut emoji_bytes = emoji_magic.into_bytes();
    
    // Pad to exactly 16 bytes
    emoji_bytes.resize(EMOJI_MAGIC_SIZE, 0);
    
    emoji_bytes
}