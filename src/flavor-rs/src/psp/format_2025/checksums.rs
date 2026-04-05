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
            let mut adler = adler2::Adler32::new();
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
            let checksum = adler2::adler32_slice(data);
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

#[cfg(test)]
mod tests {
    use super::{
        ChecksumAlgorithm, calculate_checksum, calculate_checksum_bytes, parse_checksum,
        verify_checksum,
    };

    #[test]
    fn test_parse_checksum_prefixed_and_legacy_formats() {
        let (algo, value) = parse_checksum("sha256:abcd").expect("prefixed checksum should parse");
        assert_eq!(algo, ChecksumAlgorithm::Sha256);
        assert_eq!(value, "abcd");

        let (algo, value) = parse_checksum("12345678").expect("legacy adler32 should parse");
        assert_eq!(algo, ChecksumAlgorithm::Adler32);
        assert_eq!(value, "12345678");
    }

    #[test]
    fn test_calculate_checksum_bytes_and_verify() {
        let data = b"checksum-target";
        let sha256 = calculate_checksum_bytes(data, ChecksumAlgorithm::Sha256)
            .expect("sha256 checksum should succeed");
        assert!(sha256.starts_with("sha256:"));
        assert!(verify_checksum(data, &sha256).expect("verification should succeed"));
        assert!(
            !verify_checksum(b"other", &sha256).expect("mismatched verification should succeed")
        );

        let adler32 = calculate_checksum_bytes(data, ChecksumAlgorithm::Adler32)
            .expect("adler32 checksum should succeed");
        assert!(adler32.starts_with("adler32:"));
    }

    #[test]
    fn test_calculate_checksum_streaming_and_blake2b_error() {
        let checksum = calculate_checksum(&b"streamed"[..], ChecksumAlgorithm::Sha512)
            .expect("sha512 checksum should succeed");
        assert!(checksum.starts_with("sha512:"));

        let err = calculate_checksum_bytes(b"data", ChecksumAlgorithm::Blake2b)
            .expect_err("blake2b should be unsupported");
        assert_eq!(err.kind(), std::io::ErrorKind::Unsupported);
    }

    #[test]
    fn test_calculate_checksum_streaming_sha256() {
        let checksum =
            calculate_checksum(&b"hello"[..], ChecksumAlgorithm::Sha256).expect("sha256 streaming");
        assert!(checksum.starts_with("sha256:"));
        // SHA-256 hex is 64 chars
        assert_eq!(checksum.split(':').nth(1).unwrap().len(), 64);
    }

    #[test]
    fn test_calculate_checksum_streaming_adler32() {
        let checksum = calculate_checksum(&b"hello"[..], ChecksumAlgorithm::Adler32)
            .expect("adler32 streaming");
        assert!(checksum.starts_with("adler32:"));
    }

    #[test]
    fn test_calculate_checksum_streaming_blake2b_error() {
        let err = calculate_checksum(&b"data"[..], ChecksumAlgorithm::Blake2b)
            .expect_err("blake2b streaming should fail");
        assert_eq!(err.kind(), std::io::ErrorKind::Unsupported);
    }

    #[test]
    fn test_calculate_checksum_bytes_sha512() {
        let checksum =
            calculate_checksum_bytes(b"data", ChecksumAlgorithm::Sha512).expect("sha512 bytes");
        assert!(checksum.starts_with("sha512:"));
        // SHA-512 hex is 128 chars
        assert_eq!(checksum.split(':').nth(1).unwrap().len(), 128);
    }

    #[test]
    fn test_parse_checksum_all_prefixed_algorithms() {
        let (algo, val) = parse_checksum("sha512:abcd").unwrap();
        assert_eq!(algo, ChecksumAlgorithm::Sha512);
        assert_eq!(val, "abcd");

        let (algo, val) = parse_checksum("adler32:12345678").unwrap();
        assert_eq!(algo, ChecksumAlgorithm::Adler32);
        assert_eq!(val, "12345678");

        let (algo, val) = parse_checksum("blake2b:ff").unwrap();
        assert_eq!(algo, ChecksumAlgorithm::Blake2b);
        assert_eq!(val, "ff");
    }

    #[test]
    fn test_parse_checksum_unknown_algorithm() {
        let err = parse_checksum("md5:abc123").unwrap_err();
        assert!(err.contains("Unknown checksum algorithm"));
    }

    #[test]
    fn test_parse_checksum_legacy_sha512_length() {
        let hex_128 = "a".repeat(128);
        let (algo, _) = parse_checksum(&hex_128).unwrap();
        assert_eq!(algo, ChecksumAlgorithm::Sha512);
    }

    #[test]
    fn test_parse_checksum_legacy_default_length() {
        // 10 chars doesn't match any known length, defaults to SHA256
        let (algo, _) = parse_checksum("abcdef1234").unwrap();
        assert_eq!(algo, ChecksumAlgorithm::Sha256);
    }

    #[test]
    fn test_checksum_algorithm_display() {
        assert_eq!(format!("{}", ChecksumAlgorithm::Sha256), "sha256");
        assert_eq!(format!("{}", ChecksumAlgorithm::Sha512), "sha512");
        assert_eq!(format!("{}", ChecksumAlgorithm::Adler32), "adler32");
        assert_eq!(format!("{}", ChecksumAlgorithm::Blake2b), "blake2b");
    }

    #[test]
    fn test_verify_checksum_rejects_wrong_data() {
        let checksum = calculate_checksum_bytes(b"correct", ChecksumAlgorithm::Sha256).unwrap();
        assert!(!verify_checksum(b"wrong", &checksum).unwrap());
    }
}
