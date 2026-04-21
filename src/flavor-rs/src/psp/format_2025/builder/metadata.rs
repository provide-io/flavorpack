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
    get_build_info_with(std::env::var("SOURCE_DATE_EPOCH").ok(), None)
}

fn get_build_info_with(epoch: Option<String>, hostname: Option<String>) -> (String, String) {
    if let Some(epoch) = epoch {
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
        let hostname =
            hostname.unwrap_or_else(|| gethostname::gethostname().to_string_lossy().to_string());
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
                host: Some(build_host),
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
                    std::env::var(crate::env_vars::LAUNCHER_BIN)
                        .ok()
                        .and_then(|s| {
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
        // Policy is not carried through the Rust builder manifest; launchers read it
        // from the signed metadata JSON produced by the Python orchestrator.
        policy: None,
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

#[cfg(test)]
mod tests {
    use super::*;
    use crate::psp::format_2025::Index;
    use crate::psp::format_2025::manifest::{
        BuildManifest, ExecutionInfo as ManifestExecutionInfo, ManifestSlot,
        PackageInfo as ManifestPackageInfo,
    };
    use flate2::read::GzDecoder;
    use serde_json::json;
    use sha2::{Digest, Sha256};
    use std::collections::HashMap;
    use std::io::Read;
    use std::path::PathBuf;

    fn sample_manifest() -> BuildManifest {
        BuildManifest {
            package: ManifestPackageInfo {
                name: "demo".to_string(),
                version: "1.2.3".to_string(),
                description: "test package".to_string(),
            },
            execution: ManifestExecutionInfo {
                command: "run".to_string(),
                env: HashMap::from([(String::from("MODE"), String::from("test"))]),
            },
            slots: vec![ManifestSlot {
                slot: Some(0),
                id: "launcher".to_string(),
                source: "$SELF".to_string(),
                target: "/app/bin/launcher".to_string(),
                operations: String::new(),
                purpose: "code".to_string(),
                lifecycle: "startup".to_string(),
                permissions: Some("0755".to_string()),
                resolution: Some("build".to_string()),
            }],
            cache_validation: Some(json!({
                "check_file": "marker.txt",
                "expected_content": "ok"
            })),
            runtime: Some(json!({
                "env": {
                    "set": {
                        "MODE": "test"
                    }
                }
            })),
            workenv: Some(json!({
                "directories": [
                    {"path": "/tmp/demo", "mode": "0700"}
                ],
                "env": {
                    "WORKENV": "1"
                }
            })),
            setup_commands: vec![json!({"kind": "prepare"})],
        }
    }

    #[test]
    fn get_build_info_uses_source_date_epoch_when_present() {
        let (timestamp, host) =
            get_build_info_with(Some("1".to_string()), Some("ignored-host".to_string()));

        assert!(timestamp.starts_with("1970-01-01T00:00:01"));
        assert_eq!(
            host,
            format!("{}/{}", std::env::consts::OS, std::env::consts::ARCH)
        );
    }

    #[test]
    fn get_build_info_includes_hostname_without_source_date_epoch() {
        let (timestamp, host) = get_build_info_with(None, Some("test-host".to_string()));

        assert!(!timestamp.is_empty());
        assert!(host.ends_with(" test-host"));
    }

    #[test]
    fn create_metadata_populates_expected_fields() {
        let manifest = sample_manifest();
        let options = BuildOptions {
            launcher_bin: Some(PathBuf::from("/tmp/fake-launcher")),
            skip_verification: false,
            private_key_path: None,
            public_key_path: None,
            key_seed: Some("deterministic-seed".to_string()),
            workenv_base: None,
        };

        let metadata =
            create_metadata(&manifest, 123, b"launcher-data", &options).expect("create metadata");

        assert_eq!(metadata.format, "PSPF/2025");
        assert_eq!(metadata.package.name, "demo");
        assert_eq!(metadata.package.version, "1.2.3");
        assert_eq!(metadata.execution.primary_slot, 0);
        assert_eq!(metadata.execution.command, "run");
        assert_eq!(
            metadata.execution.env.get("MODE").map(String::as_str),
            Some("test")
        );
        assert!(
            metadata
                .verification
                .expect("verification")
                .require_verification
        );
        let build = metadata.build.expect("build");
        assert_eq!(build.tool, "flavor-rs");
        assert!(build.deterministic);
        assert_eq!(
            metadata.launcher.as_ref().expect("launcher").tool,
            "fake-launcher"
        );
        assert_eq!(metadata.launcher.as_ref().expect("launcher").size, 123);
        assert_eq!(
            metadata.launcher.as_ref().expect("launcher").capabilities,
            vec!["mmap", "signed"]
        );
        assert!(metadata.cache_validation.is_some());
        assert_eq!(
            metadata
                .runtime
                .as_ref()
                .expect("runtime")
                .env
                .as_ref()
                .and_then(|env| env.set.as_ref())
                .and_then(|set| set.get("MODE"))
                .map(String::as_str),
            Some("test")
        );
        assert_eq!(
            metadata
                .workenv
                .as_ref()
                .expect("workenv")
                .directories
                .as_ref()
                .expect("directories")[0]
                .path,
            "/tmp/demo"
        );
        assert_eq!(metadata.setup_commands.len(), 1);
        assert!(metadata.policy.is_none());
    }

    #[test]
    fn compress_and_sign_metadata_updates_index_and_round_trips() {
        let manifest = sample_manifest();
        let options = BuildOptions {
            launcher_bin: Some(PathBuf::from("/tmp/fake-launcher")),
            skip_verification: false,
            private_key_path: None,
            public_key_path: None,
            key_seed: Some("deterministic-seed".to_string()),
            workenv_base: None,
        };
        let metadata =
            create_metadata(&manifest, 123, b"launcher-data", &options).expect("create metadata");
        let secret = [7u8; 32];
        let signing_key = ed25519_dalek::SigningKey::from_bytes(&secret);
        let mut index = Index::new();

        let compressed = compress_and_sign_metadata(&metadata, &signing_key, &mut index)
            .expect("compress and sign");

        assert!(!compressed.is_empty());

        let checksum_bytes = index.metadata_checksum;
        assert!(checksum_bytes.iter().any(|byte| *byte != 0));
        assert!(
            index
                .integrity_signature
                .iter()
                .take(64)
                .any(|byte| *byte != 0)
        );

        let mut decompressed = String::new();
        GzDecoder::new(compressed.as_slice())
            .read_to_string(&mut decompressed)
            .expect("decompress metadata");
        let expected = serde_json::to_string_pretty(&metadata).expect("serialize metadata");
        assert_eq!(decompressed, expected);

        let mut hasher = Sha256::new();
        hasher.update(&compressed);
        let expected_checksum: [u8; 32] = hasher.finalize().into();
        assert_eq!(checksum_bytes, expected_checksum);
    }
}
