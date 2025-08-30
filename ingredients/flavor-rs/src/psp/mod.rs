//! Package format implementations

pub mod format_2025;

use crate::exceptions::{FlavorError, Result};
use std::path::Path;

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
            let search_limit = file_size.min(10 * 1024 * 1024);
            log::trace!("Searching for PSPF magic in first {} bytes", search_limit);
            
            for offset in (0..search_limit).step_by(1024) {
                file.seek(SeekFrom::Start(offset))?;
                let mut buffer = vec![0u8; 1024.min((file_size - offset) as usize)];
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
