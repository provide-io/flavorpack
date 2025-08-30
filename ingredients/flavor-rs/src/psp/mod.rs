//! Package format implementations

pub mod format_2025;

use crate::exceptions::{FlavorError, Result};
use std::path::Path;

/// Maximum size to search for PSPF magic in a file (5MB)
/// This accommodates Go launchers (~3.3MB) and Rust launchers (~1MB) with margin
const MAX_LAUNCHER_SEARCH_SIZE: u64 = 5 * 1024 * 1024;

/// Size of chunks to read when searching for PSPF magic (8KB)
const MAGIC_SEARCH_CHUNK_SIZE: usize = 8192;

/// Step size when searching for PSPF magic (4KB)
/// Smaller than chunk size to provide overlap and avoid missing magic at boundaries
const MAGIC_SEARCH_STEP_SIZE: usize = 4096;

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
            log::trace!("Found emoji magic at end of file, assuming valid PSPF package");
            // If we have the emoji magic, we can assume it's a valid PSPF package
            // The emoji magic is the definitive marker - no need to search for PSPF header
            // as that would be expensive for large files and the emoji magic is sufficient
            return Ok(PackageFormat::PSPF2025);
        } else {
            log::trace!("No emoji magic at end of file");
        }
    }

    Err(FlavorError::UnsupportedFormat(
        "Not a PSPF package".to_string(),
    ))
}
