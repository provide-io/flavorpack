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

        // Check for MagicTrailer (📦 + index + 🪄) using minimal reads
        // The MagicTrailer is 8200 bytes total at the end of the file
        if file_size >= format_2025::constants::MAGIC_TRAILER_SIZE as u64 {
            // First check for 🪄 at the very end (last 4 bytes)
            file.seek(SeekFrom::End(-4))?;
            let mut magic_wand = [0u8; 4];
            file.read_exact(&mut magic_wand)?;

            if magic_wand == *format_2025::constants::MAGIC_WAND_EMOJI_BYTES {
                // Now check for 📦 at the start of the trailer
                file.seek(SeekFrom::End(
                    -(format_2025::constants::MAGIC_TRAILER_SIZE as i64),
                ))?;
                let mut package_emoji = [0u8; 4];
                file.read_exact(&mut package_emoji)?;

                if package_emoji == *format_2025::constants::PACKAGE_EMOJI_BYTES {
                    log::debug!("Found valid MagicTrailer at end of file");
                    return Ok(PackageFormat::PSPF2025);
                }
            }
        }
        log::trace!("No valid MagicTrailer found");
    }

    Err(FlavorError::UnsupportedFormat(
        "Not a PSPF package".to_string(),
    ))
}
