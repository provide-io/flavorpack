//! Package format implementations

pub mod format_2025;

use crate::exceptions::{FlavorError, Result};
use std::path::Path;

/// Maximum size to search for PSPF magic in a file (5MB)
/// This accommodates Go launchers (~3.3MB) and Rust launchers (~1MB) with margin
const MAX_LAUNCHER_SEARCH_SIZE: u64 = 5 * 1024 * 1024;

/// Supported package formats
#[derive(Debug, Clone, Copy)]
pub enum PackageFormat {
    PSPF2025,
}

/// Detect the format of a package by reading its magic bytes
pub fn detect_format(package_path: &Path) -> Result<PackageFormat> {
    use std::fs::File;
    use std::io::{Read, Seek, SeekFrom};

    log::trace!("Detecting format for: {:?}", package_path);
    let mut file = File::open(package_path)?;
    let file_size = file.metadata()?.len();
    log::trace!("File size: {} bytes", file_size);

    // A valid PSPF package MUST have the trailing emoji magic at the end
    // Check the last 8 bytes for the emoji magic (📦🪄)
    if file_size >= 8 {
        file.seek(SeekFrom::End(-8))?;
        let mut trailing = [0u8; 8];
        file.read_exact(&mut trailing)?;
        
        // Check for the emoji magic bytes
        let expected = [
            format_2025::constants::PACKAGE_EMOJI_BYTES,
            format_2025::constants::MAGIC_WAND_EMOJI_BYTES,
        ].concat();
        
        if trailing == expected.as_slice() {
            log::trace!("Found emoji magic at end of file");
            // Now verify there's a valid PSPF header somewhere
            // Search for PSPF magic in the file
            // Limit search to first 5MB to accommodate larger launchers (Go launcher is ~3.3MB)
            let search_limit = file_size.min(5 * 1024 * 1024);
            log::trace!("Searching for PSPF magic in first {} bytes", search_limit);
            
            // Search more efficiently - use larger chunks and skip by larger amounts
            // Most launchers have PSPF magic aligned at 4K or 8K boundaries
            let chunk_size = 8192;  // 8KB chunks
            let step_size = 4096;   // Step by 4KB for some overlap
            
            for offset in (0..search_limit).step_by(step_size) {
                file.seek(SeekFrom::Start(offset))?;
                let read_size = chunk_size.min((file_size - offset) as usize);
                let mut buffer = vec![0u8; read_size];
                file.read_exact(&mut buffer)?;

                let magic = &format_2025::constants::PSPF_MAGIC;
                if buffer.starts_with(magic) || buffer.windows(8).any(|w| w == magic) {
                    log::debug!("Found PSPF magic at offset {}", offset);
                    return Ok(PackageFormat::PSPF2025);
                }
            }
            log::trace!("PSPF magic not found in search range");
        } else {
            log::trace!("No emoji magic at end of file");
        }
    }

    Err(FlavorError::UnsupportedFormat(
        "Not a PSPF package".to_string(),
    ))
}
