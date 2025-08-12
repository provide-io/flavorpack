use anyhow::{anyhow, Result};
use serde_json::json;
use std::fs::File;
use std::io::{Read, Seek, SeekFrom};
use std::path::Path;
use adler::Adler32;
use sha2::{Sha256, Digest};
use ed25519_dalek::{PublicKey, Signature, Verifier};
use flate2::read::GzDecoder;
use tar::Archive;

const INDEX_SIZE: usize = 256;

pub fn verify_package(package_path: &Path) -> Result<()> {
    let mut file = File::open(package_path)?;
    
    // Get file size
    let file_size = file.metadata()?.len();
    
    // Try to find PSPF2025 magic by searching backwards from end
    let mut found = false;
    let mut index_offset = 0u64;
    
    // Search in 1KB chunks from the end
    for offset in (0..file_size).rev().step_by(1024) {
        file.seek(SeekFrom::Start(offset))?;
        let mut buffer = vec![0u8; 1024.min((file_size - offset) as usize)];
        file.read_exact(&mut buffer)?;
        
        if let Some(pos) = buffer.windows(8).position(|w| w == b"PSPF2025") {
            index_offset = offset + pos as u64;
            found = true;
            break;
        }
    }
    
    if !found {
        return Err(anyhow!("Not a valid PSPF 2025 bundle"));
    }
    
    // Read full index block
    file.seek(SeekFrom::Start(index_offset))?;
    let mut index_bytes = vec![0u8; INDEX_SIZE];
    file.read_exact(&mut index_bytes)?;
    
    // Parse index fields
    let version = u32::from_le_bytes([index_bytes[8], index_bytes[9], index_bytes[10], index_bytes[11]]);
    let stored_checksum = u32::from_le_bytes([index_bytes[12], index_bytes[13], index_bytes[14], index_bytes[15]]);
    let package_size = u64::from_le_bytes(index_bytes[16..24].try_into().unwrap());
    let launcher_size = u64::from_le_bytes(index_bytes[24..32].try_into().unwrap());
    let metadata_offset = u64::from_le_bytes(index_bytes[32..40].try_into().unwrap());
    let metadata_size = u64::from_le_bytes(index_bytes[40..48].try_into().unwrap());
    let slot_table_offset = u64::from_le_bytes(index_bytes[48..56].try_into().unwrap());
    let slot_table_size = u64::from_le_bytes(index_bytes[56..64].try_into().unwrap());
    let slot_count = u32::from_le_bytes([index_bytes[64], index_bytes[65], index_bytes[66], index_bytes[67]]);
    
    // Get ephemeral public key
    let ephemeral_key = &index_bytes[72..104];
    let metadata_checksum = &index_bytes[104..136];
    
    // Verify index checksum (with checksum field zeroed)
    let mut checksum_bytes = index_bytes.clone();
    checksum_bytes[12..16].copy_from_slice(&[0u8; 4]);
    
    let mut adler = Adler32::new();
    adler.write_slice(&checksum_bytes);
    let calculated_checksum = adler.checksum();
    
    let index_checksum_valid = calculated_checksum == stored_checksum;
    
    // Verify metadata checksum if metadata exists
    let mut metadata_checksum_valid = false;
    let mut integrity_seal_valid = false;
    
    if metadata_size > 0 && metadata_offset > 0 {
        file.seek(SeekFrom::Start(metadata_offset))?;
        let mut metadata_bytes = vec![0u8; metadata_size as usize];
        file.read_exact(&mut metadata_bytes)?;
        
        // Verify metadata checksum
        let mut hasher = Sha256::new();
        hasher.update(&metadata_bytes);
        let calculated_hash = hasher.finalize();
        
        metadata_checksum_valid = calculated_hash.as_slice() == metadata_checksum;
        
        // Extract integrity seal from metadata archive
        if metadata_checksum_valid {
            let gz = GzDecoder::new(&metadata_bytes[..]);
            let mut archive = Archive::new(gz);
            
            let mut seal_sig: Option<Vec<u8>> = None;
            let mut seal_pem: Option<Vec<u8>> = None;
            let mut psp_json: Option<Vec<u8>> = None;
            
            for entry in archive.entries()? {
                let mut entry = entry?;
                let path = entry.path()?;
                
                if path.ends_with("integrity/seal.sig") {
                    let mut contents = Vec::new();
                    entry.read_to_end(&mut contents)?;
                    seal_sig = Some(contents);
                } else if path.ends_with("integrity/seal.pem") {
                    let mut contents = Vec::new();
                    entry.read_to_end(&mut contents)?;
                    seal_pem = Some(contents);
                } else if path.ends_with("psp.json") {
                    let mut contents = Vec::new();
                    entry.read_to_end(&mut contents)?;
                    psp_json = Some(contents);
                }
            }
            
            // Verify ephemeral signature if we have all components
            if let (Some(sig_bytes), Some(pem_bytes), Some(json_bytes)) = (seal_sig, seal_pem, psp_json) {
                // Parse ephemeral public key from PEM
                let pem_str = std::str::from_utf8(&pem_bytes)?;
                let pem = pem::parse(pem_str)?;
                
                // Extract raw public key bytes (last 32 bytes of SubjectPublicKeyInfo)
                let spki_bytes = &pem.contents;
                let key_bytes = &spki_bytes[spki_bytes.len() - 32..];
                
                // Verify the ephemeral key matches the one in index
                if key_bytes == &ephemeral_key[..32] {
                    // Parse signature
                    let signature = Signature::from_bytes(&sig_bytes)?;
                    let public_key = PublicKey::from_bytes(key_bytes)?;
                    
                    // Verify signature over psp.json
                    integrity_seal_valid = public_key.verify(&json_bytes, &signature).is_ok();
                }
            }
        }
    }
    
    // Check package size matches
    let size_valid = package_size == file_size;
    
    // Create verification result
    let result = json!({
        "format": "PSPF/2025",
        "version": format!("0x{:08x}", version),
        "file_size": file_size,
        "package_size": package_size,
        "launcher_size": launcher_size,
        "index_offset": index_offset,
        "slot_count": slot_count,
        "checksums": {
            "index_checksum_valid": index_checksum_valid,
            "index_stored": format!("0x{:08x}", stored_checksum),
            "index_calculated": format!("0x{:08x}", calculated_checksum),
            "metadata_checksum_valid": metadata_checksum_valid,
            "package_size_valid": size_valid,
        },
        "metadata": {
            "offset": metadata_offset,
            "size": metadata_size,
        },
        "slots": {
            "table_offset": slot_table_offset,
            "table_size": slot_table_size,
            "count": slot_count,
        },
        "integrity_seal_valid": integrity_seal_valid,
        "signature_valid": metadata_checksum_valid && index_checksum_valid && integrity_seal_valid,
    });
    
    // Output JSON result
    println!("{}", serde_json::to_string_pretty(&result)?);
    
    // Exit with error if verification failed
    if !index_checksum_valid || !metadata_checksum_valid || !size_valid {
        std::process::exit(1);
    }
    
    Ok(())
}