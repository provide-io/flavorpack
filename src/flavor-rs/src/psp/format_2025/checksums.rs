//! Checksum utilities supporting multiple algorithms with prefixed format.
//!
//! Format: "algorithm:hexvalue" (e.g., "sha256:cafe8008...", "adler32:f00dcafe")

use sha2::{Digest, Sha256, Sha512};
use std::fmt;
use std::io::Read;

/// Supported checksum algorithms
#[derive(Debug, Clone, PartialEq)]
pub enum ChecksumAlgorithm {
    Sha256,
    Sha512,
    Adler32,
    Blake2b,
}

impl fmt::Display for ChecksumAlgorithm {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            ChecksumAlgorithm::Sha256 => write!(f, "sha256"),
            ChecksumAlgorithm::Sha512 => write!(f, "sha512"),
            ChecksumAlgorithm::Adler32 => write!(f, "adler32"),
            ChecksumAlgorithm::Blake2b => write!(f, "blake2b"),
        }
    }
}

/// Parse a checksum string that may or may not have a prefix
pub fn parse_checksum(checksum_str: &str) -> Result<(ChecksumAlgorithm, String), String> {
    if checksum_str.contains(':') {
        // Prefixed format
        let parts: Vec<&str> = checksum_str.splitn(2, ':').collect();
        if parts.len() != 2 {
            return Err(format!("Invalid checksum format: {}", checksum_str));
        }

        let algo = match parts[0] {
            "sha256" => ChecksumAlgorithm::Sha256,
            "sha512" => ChecksumAlgorithm::Sha512,
            "adler32" => ChecksumAlgorithm::Adler32,
            "blake2b" => ChecksumAlgorithm::Blake2b,
            _ => return Err(format!("Unknown checksum algorithm: {}", parts[0])),
        };

        Ok((algo, parts[1].to_string()))
    } else {
        // Legacy format - guess based on length
        let len = checksum_str.len();
        let algo = match len {
            64 => ChecksumAlgorithm::Sha256,
            128 => ChecksumAlgorithm::Sha512,
            8 => ChecksumAlgorithm::Adler32,
            _ => ChecksumAlgorithm::Sha256, // Default
        };

        Ok((algo, checksum_str.to_string()))
    }
}

/// Calculate checksum with prefix using streaming I/O
/// This replaces the old memory-based version for efficiency
pub fn calculate_checksum<R: Read>(
    mut reader: R,
    algorithm: ChecksumAlgorithm,
) -> std::io::Result<String> {
    const BUFFER_SIZE: usize = 8 * 1024 * 1024; // 8MB buffer
    let mut buffer = vec![0u8; BUFFER_SIZE];

    match algorithm {
        ChecksumAlgorithm::Sha256 => {
            let mut hasher = Sha256::new();
            loop {
                let bytes_read = reader.read(&mut buffer)?;
                if bytes_read == 0 {
                    break;
                }
                hasher.update(&buffer[..bytes_read]);
            }
            Ok(format!("sha256:{:x}", hasher.finalize()))
        }
        ChecksumAlgorithm::Sha512 => {
            let mut hasher = Sha512::new();
            loop {
                let bytes_read = reader.read(&mut buffer)?;
                if bytes_read == 0 {
                    break;
                }
                hasher.update(&buffer[..bytes_read]);
            }
            Ok(format!("sha512:{:x}", hasher.finalize()))
        }
        ChecksumAlgorithm::Adler32 => {
            let mut adler = adler::Adler32::new();
            loop {
                let bytes_read = reader.read(&mut buffer)?;
                if bytes_read == 0 {
                    break;
                }
                adler.write_slice(&buffer[..bytes_read]);
            }
            Ok(format!("adler32:{:08x}", adler.checksum()))
        }
        ChecksumAlgorithm::Blake2b => {
            // Blake2b not implemented in this version
            Err(std::io::Error::new(
                std::io::ErrorKind::Unsupported,
                "Blake2b checksum not implemented",
            ))
        }
    }
}

/// Calculate checksum from byte slice - convenience function for small data like metadata
pub fn calculate_checksum_bytes(
    data: &[u8],
    algorithm: ChecksumAlgorithm,
) -> Result<String, std::io::Error> {
    match algorithm {
        ChecksumAlgorithm::Sha256 => {
            let mut hasher = Sha256::new();
            hasher.update(data);
            Ok(format!("sha256:{:x}", hasher.finalize()))
        }
        ChecksumAlgorithm::Sha512 => {
            let mut hasher = Sha512::new();
            hasher.update(data);
            Ok(format!("sha512:{:x}", hasher.finalize()))
        }
        ChecksumAlgorithm::Adler32 => {
            let checksum = adler::adler32_slice(data);
            Ok(format!("adler32:{:08x}", checksum))
        }
        ChecksumAlgorithm::Blake2b => {
            // Blake2b not implemented in this version
            Err(std::io::Error::new(
                std::io::ErrorKind::Unsupported,
                "Blake2b checksum not implemented",
            ))
        }
    }
}

/// Verify data against a checksum string
pub fn verify_checksum(data: &[u8], checksum_str: &str) -> Result<bool, String> {
    let (algo, expected) = parse_checksum(checksum_str)?;
    let actual = calculate_checksum_bytes(data, algo)
        .map_err(|e| format!("Checksum calculation failed: {}", e))?;

    // Compare just the hex part
    let actual_hex = actual.split(':').next_back().unwrap_or(&actual);
    Ok(actual_hex == expected)
}
