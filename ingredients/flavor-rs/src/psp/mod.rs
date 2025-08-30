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
        
        // Check for MagicTrailer (📦 + index + 🪄)
        // The MagicTrailer is 8200 bytes total at the end of the file
        if file_size >= format_2025::constants::MAGIC_TRAILER_SIZE as u64 {
            file.seek(SeekFrom::End(-(format_2025::constants::MAGIC_TRAILER_SIZE as i64)))?;
            let mut trailer = vec![0u8; format_2025::constants::MAGIC_TRAILER_SIZE];
            file.read_exact(&mut trailer)?;
            
            // Check for 📦 at start and 🪄 at end
            if trailer[0..4] == *format_2025::constants::PACKAGE_EMOJI_BYTES
                && trailer[format_2025::constants::MAGIC_TRAILER_SIZE - 4..] == *format_2025::constants::MAGIC_WAND_EMOJI_BYTES {
                log::debug!("Found valid MagicTrailer at end of file");
                return Ok(PackageFormat::PSPF2025);
            }
        }
        log::trace!("No valid MagicTrailer found");
    }

    Err(FlavorError::UnsupportedFormat(
        "Not a PSPF package".to_string(),
    ))
}
