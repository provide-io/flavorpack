//! High-level API for flavor operations

use crate::exceptions::{FlavorError, Result};
use crate::psp::{self, PackageFormat};
use std::path::Path;

/// Options for building a package
#[derive(Debug, Default)]
pub struct BuildOptions {
    /// Path to launcher binary
    pub launcher_bin: Option<std::path::PathBuf>,
    /// Skip verification after building
    pub skip_verification: bool,
    /// Path to private key file (PEM format)
    pub private_key_path: Option<std::path::PathBuf>,
    /// Path to public key file (PEM format)
    pub public_key_path: Option<std::path::PathBuf>,
    /// Seed for deterministic key generation
    pub key_seed: Option<String>,
    /// Base directory for workenv resolution
    pub workenv_base: Option<std::path::PathBuf>,
}

/// Options for launching a package
#[derive(Debug, Default)]
pub struct LaunchOptions {
    /// Working directory for extraction
    pub workdir: Option<String>,
}

/// Result of package verification
#[derive(Debug)]
pub struct VerifyResult {
    pub format: String,
    pub version: String,
    pub signature_valid: bool,
    pub slot_count: usize,
    pub package_name: String,
    pub package_version: String,
}

/// Build a PSPF package from a manifest
pub fn build_package(
    manifest_path: &Path,
    output_path: &Path,
    options: BuildOptions,
) -> Result<()> {
    // Read manifest to determine format
    let manifest_data = std::fs::read_to_string(manifest_path)?;
    let manifest: serde_json::Value = serde_json::from_str(&manifest_data)?;

    // Determine format (default to PSPF/2025)
    let format = manifest
        .get("format")
        .and_then(|f| f.as_str())
        .unwrap_or("PSPF/2025");

    match format {
        "PSPF/2025" => psp::format_2025::build(manifest_path, output_path, options),
        _ => Err(FlavorError::UnsupportedFormat(format.to_string())),
    }
}

/// Launch a PSPF package
pub fn launch_package(package_path: &Path, args: &[String], options: LaunchOptions) -> Result<i32> {
    // Detect format from package
    let format = detect_package_format(package_path)?;

    match format {
        PackageFormat::PSPF2025 => psp::format_2025::launch(package_path, args, options),
    }
}

/// Verify a PSPF package
pub fn verify_package(package_path: &Path) -> Result<VerifyResult> {
    // Detect format from package
    let format = detect_package_format(package_path)?;

    match format {
        PackageFormat::PSPF2025 => psp::format_2025::verify(package_path),
    }
}

/// Detect the format of a package by reading its magic bytes
fn detect_package_format(package_path: &Path) -> Result<PackageFormat> {
    use std::fs::File;
    use std::io::{Read, Seek, SeekFrom};

    let mut file = File::open(package_path)?;

    // Search for PSPF magic
    let file_size = file.metadata()?.len();

    // Search in chunks from the beginning (up to 10MB to handle large launchers)
    // Check for MagicTrailer at end of file using minimal reads
    if file_size >= psp::format_2025::constants::MAGIC_TRAILER_SIZE as u64 {
        // First check for 🪄 at the very end (last 4 bytes)
        file.seek(SeekFrom::End(-4))?;
        let mut magic_wand = [0u8; 4];
        file.read_exact(&mut magic_wand)?;

        if magic_wand == *psp::format_2025::constants::MAGIC_WAND_EMOJI_BYTES {
            // Now check for 📦 at the start of the trailer
            file.seek(SeekFrom::End(
                -(psp::format_2025::constants::MAGIC_TRAILER_SIZE as i64),
            ))?;
            let mut package_emoji = [0u8; 4];
            file.read_exact(&mut package_emoji)?;

            if package_emoji == *psp::format_2025::constants::PACKAGE_EMOJI_BYTES {
                return Ok(PackageFormat::PSPF2025);
            }
        }
    }

    Err(FlavorError::UnsupportedFormat(
        "Unknown package format".to_string(),
    ))
}
