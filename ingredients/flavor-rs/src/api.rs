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
}

/// Options for launching a package
#[derive(Debug, Default)]
pub struct LaunchOptions {
    /// Skip integrity verification
    pub insecure: bool,
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
    for offset in (0..file_size.min(10 * 1024 * 1024)).step_by(1024) {
        file.seek(SeekFrom::Start(offset))?;
        let mut buffer = vec![0u8; 1024.min((file_size - offset) as usize)];
        file.read_exact(&mut buffer)?;

        // Check for PSPF magic bytes (using constants to avoid string in binary)
        let magic = &psp::format_2025::constants::PSPF_MAGIC;
        if buffer.starts_with(magic) || buffer.windows(8).any(|w| w == magic) {
            return Ok(PackageFormat::PSPF2025);
        }
    }

    Err(FlavorError::UnsupportedFormat(
        "Unknown package format".to_string(),
    ))
}
