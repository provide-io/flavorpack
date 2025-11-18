//! Metadata creation and compression

use super::super::checksums::{ChecksumAlgorithm, calculate_checksum};
use super::super::index::Index;
use super::super::manifest::BuildManifest;
use super::super::metadata::{
    BuildInfo, CacheValidationInfo, CompatibilityInfo, ExecutionInfo, IntegritySealInfo,
    LauncherInfo, Metadata, PackageInfo, PlatformInfo, RuntimeInfo, VerificationInfo, WorkenvInfo,
};
use crate::api::BuildOptions;
use crate::exceptions::{FlavorError, Result};
use ed25519_dalek::{Signature, Signer};
use log::trace;
use std::io::Write;
use std::path::PathBuf;

/// Get build timestamp and host information
pub(super) fn get_build_info() -> (String, String) {
    if let Ok(epoch) = std::env::var("SOURCE_DATE_EPOCH") {
        // Use SOURCE_DATE_EPOCH for reproducible timestamps
        let timestamp = if let Ok(secs) = epoch.parse::<i64>() {
            chrono::DateTime::from_timestamp(secs, 0)
                .map(|dt| dt.to_rfc3339())
                .unwrap_or_else(|| chrono::Utc::now().to_rfc3339())
        } else {
            chrono::Utc::now().to_rfc3339()
        };
        (
            timestamp,
            format!("{}/{}", std::env::consts::OS, std::env::consts::ARCH),
        )
    } else {
        let hostname = gethostname::gethostname().to_string_lossy().to_string();
        (
            chrono::Utc::now().to_rfc3339(),
            format!(
                "{}/{} {}",
                std::env::consts::OS,
                std::env::consts::ARCH,
                hostname
            ),
        )
    }
}

/// Create the package metadata structure
pub(super) fn create_metadata(
    manifest: &BuildManifest,
    launcher_size: u64,
    launcher_data: &[u8],
    options: &BuildOptions,
) -> Result<Metadata> {
    let (build_timestamp, build_host) = get_build_info();

    // Calculate launcher checksum
    let launcher_checksum =
        calculate_checksum(launcher_data, ChecksumAlgorithm::Sha256).map_err(|e| {
            FlavorError::Generic(format!("Failed to calculate launcher checksum: {}", e))
        })?;

    Ok(Metadata {
        format: "PSPF/2025".to_string(),
        format_version: Some("1.0.0".to_string()),
        package: PackageInfo {
            name: manifest.package.name.clone(),
            version: manifest.package.version.clone(),
        },
        slots: vec![],
        execution: ExecutionInfo {
            primary_slot: 0,
            command: manifest.execution.command.clone(),
            env: manifest.execution.env.clone(),
        },
        verification: Some(VerificationInfo {
            integrity_seal: IntegritySealInfo {
                required: true,
                algorithm: "ed25519".to_string(),
            },
            signed: true,
            require_verification: true,
            trust_signatures: None,
        }),
        build: Some(BuildInfo {
            tool: "flavor-rs".to_string(),
            tool_version: env!("FLAVOR_VERSION").to_string(),
            timestamp: build_timestamp,
            deterministic: options.key_seed.is_some(),
            platform: PlatformInfo {
                os: std::env::consts::OS.to_string(),
                arch: std::env::consts::ARCH.to_string(),
                host: build_host,
            },
        }),
        launcher: Some(LauncherInfo {
            tool: options
                .launcher_bin
                .as_ref()
                .and_then(|p| p.file_name())
                .and_then(|n| n.to_str())
                .map(|s| s.to_string())
                .or_else(|| {
                    std::env::var("FLAVOR_LAUNCHER_BIN").ok().and_then(|s| {
                        PathBuf::from(s)
                            .file_name()
                            .and_then(|n| n.to_str())
                            .map(|s| s.to_string())
                    })
                })
                .unwrap_or_else(|| "unknown".to_string()),
            tool_version: env!("CARGO_PKG_VERSION").to_string(),
            size: launcher_size as i64,
            checksum: launcher_checksum,
            capabilities: vec!["mmap".to_string(), "signed".to_string()],
        }),
        compatibility: Some(CompatibilityInfo {
            min_format_version: "1.0.0".to_string(),
            features: vec![],
        }),
        cache_validation: manifest
            .cache_validation
            .as_ref()
            .and_then(|v| serde_json::from_value::<CacheValidationInfo>(v.clone()).ok()),
        runtime: manifest
            .runtime
            .as_ref()
            .and_then(|v| serde_json::from_value::<RuntimeInfo>(v.clone()).ok()),
        workenv: manifest
            .workenv
            .as_ref()
            .and_then(|v| serde_json::from_value::<WorkenvInfo>(v.clone()).ok()),
        setup_commands: manifest.setup_commands.clone(),
    })
}

/// Compress and sign metadata
pub(super) fn compress_and_sign_metadata(
    metadata: &Metadata,
    signing_key: &ed25519_dalek::SigningKey,
    index: &mut Index,
) -> Result<Vec<u8>> {
    trace!("📝 Creating and signing metadata");

    // Create JSON
    let metadata_json = serde_json::to_vec_pretty(metadata)?;

    // Sign the metadata
    let signature: Signature = signing_key.sign(&metadata_json);
    index.integrity_signature[..64].copy_from_slice(signature.to_bytes().as_ref());

    // Compress with gzip
    let mut compressed = Vec::new();
    {
        use flate2::Compression;
        use flate2::write::GzEncoder;

        let mut encoder = GzEncoder::new(&mut compressed, Compression::default());
        encoder.write_all(&metadata_json)?;
        encoder.finish()?;
    }

    // Calculate checksum (SHA-256 - full 32 bytes)
    use sha2::{Digest, Sha256};
    let mut hasher = Sha256::new();
    hasher.update(&compressed);
    let checksum_bytes: [u8; 32] = hasher.finalize().into();
    index.metadata_checksum = checksum_bytes;

    Ok(compressed)
}
