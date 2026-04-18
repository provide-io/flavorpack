// SPDX-FileCopyrightText: Copyright (c) 2026 provide.io llc. All rights reserved.
// SPDX-License-Identifier: Apache-2.0

//! PSPF/2025 metadata structures and types

use serde::{Deserialize, Serialize};
use serde_json::Value;
use std::collections::HashMap;

/// Main metadata structure for a PSPF package
#[derive(Debug, Clone, Deserialize, Serialize)]
pub struct Metadata {
    pub format: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub format_version: Option<String>,
    pub package: PackageInfo,
    pub slots: Vec<SlotMetadata>,
    pub execution: ExecutionInfo,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub verification: Option<VerificationInfo>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub build: Option<BuildInfo>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub launcher: Option<LauncherInfo>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub compatibility: Option<CompatibilityInfo>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub cache_validation: Option<CacheValidationInfo>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub runtime: Option<RuntimeInfo>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub workenv: Option<WorkenvInfo>,
    #[serde(default)]
    pub setup_commands: Vec<Value>,
    /// Package-declared execution policy (FEP-0004 §8).
    #[serde(skip_serializing_if = "Option::is_none")]
    pub policy: Option<Value>,
}

/// Package information
#[derive(Debug, Clone, Deserialize, Serialize)]
pub struct PackageInfo {
    pub name: String,
    pub version: String,
}

/// Slot metadata for each data slot in the package
#[derive(Debug, Clone, Deserialize, Serialize)]
pub struct SlotMetadata {
    #[serde(rename = "slot")]
    pub index: usize, // Position validator
    pub id: String,     // Arbitrary identifier
    pub source: String, // Source path
    pub target: String, // Destination in workenv
    pub size: i64,      // Size as stored in package
    pub checksum: String,
    pub operations: String, // Operation chain (e.g., "gzip", "tar|gzip")
    pub purpose: String,
    pub lifecycle: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub permissions: Option<String>, // Unix permissions as octal string (e.g., "0755")
    #[serde(skip_serializing_if = "Option::is_none")]
    pub resolution: Option<String>, // When to resolve: build|runtime|lazy
    #[serde(skip_serializing_if = "Option::is_none")]
    pub self_ref: Option<bool>, // Self-referential slot (references launcher itself)
}

/// Execution configuration
#[derive(Debug, Clone, Deserialize, Serialize)]
pub struct ExecutionInfo {
    pub primary_slot: usize,
    pub command: String,
    #[serde(default)]
    pub env: HashMap<String, String>,
}

/// Verification information
#[derive(Debug, Clone, Deserialize, Serialize)]
pub struct VerificationInfo {
    pub integrity_seal: IntegritySealInfo,
    #[serde(default)]
    pub signed: bool,
    #[serde(default = "default_true")]
    pub require_verification: bool,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub trust_signatures: Option<TrustSignaturesInfo>,
}

fn default_true() -> bool {
    true
}

/// Integrity seal configuration
#[derive(Debug, Clone, Deserialize, Serialize)]
pub struct IntegritySealInfo {
    pub required: bool,
    pub algorithm: String,
}

/// Trust signatures configuration
#[derive(Debug, Clone, Deserialize, Serialize)]
pub struct TrustSignaturesInfo {
    pub required: bool,
    #[serde(default)]
    pub signers: Vec<SignerInfo>,
}

/// Signer information
#[derive(Debug, Clone, Deserialize, Serialize)]
pub struct SignerInfo {
    pub name: String,
    pub key_id: String,
    pub algorithm: String,
}

/// Build information (optional)
#[derive(Debug, Clone, Deserialize, Serialize)]
pub struct BuildInfo {
    pub tool: String,
    pub tool_version: String,
    pub timestamp: String,
    #[serde(default)]
    pub deterministic: bool,
    pub platform: PlatformInfo,
}

/// Platform information
#[derive(Debug, Clone, Deserialize, Serialize)]
pub struct PlatformInfo {
    pub os: String,
    pub arch: String,
    /// Optional: only present when FLAVOR_INCLUDE_BUILD_HOST=1 was set at build time.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub host: Option<String>,
}

/// Launcher information
#[derive(Debug, Clone, Deserialize, Serialize)]
pub struct LauncherInfo {
    pub tool: String,
    pub tool_version: String,
    pub size: i64,
    pub checksum: String,
    pub capabilities: Vec<String>,
}

/// Compatibility information
#[derive(Debug, Clone, Deserialize, Serialize)]
pub struct CompatibilityInfo {
    pub min_format_version: String,
    pub features: Vec<String>,
}

/// Cache validation configuration
#[derive(Debug, Clone, Deserialize, Serialize)]
pub struct CacheValidationInfo {
    pub check_file: String,
    pub expected_content: String,
}

/// Runtime configuration
#[derive(Debug, Clone, Deserialize, Serialize)]
pub struct RuntimeInfo {
    #[serde(skip_serializing_if = "Option::is_none")]
    pub env: Option<RuntimeEnv>,
}

/// Runtime environment configuration
#[derive(Debug, Clone, Deserialize, Serialize)]
pub struct RuntimeEnv {
    #[serde(skip_serializing_if = "Option::is_none")]
    pub unset: Option<Vec<String>>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub map: Option<HashMap<String, String>>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub set: Option<HashMap<String, String>>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub pass: Option<Vec<String>>,
}

/// Work environment configuration
#[derive(Debug, Clone, Deserialize, Serialize)]
pub struct WorkenvInfo {
    #[serde(skip_serializing_if = "Option::is_none")]
    pub directories: Option<Vec<DirectorySpec>>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub env: Option<HashMap<String, String>>,
}

/// Directory specification for workenv
#[derive(Debug, Clone, Deserialize, Serialize)]
pub struct DirectorySpec {
    pub path: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub mode: Option<String>, // Unix permission mode like "0700"
}

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::json;

    fn sample_slot() -> SlotMetadata {
        SlotMetadata {
            index: 0,
            id: "launcher".to_string(),
            source: "$SELF".to_string(),
            target: "/app/bin/launcher".to_string(),
            size: 0,
            checksum: "sha256:deadbeef".to_string(),
            operations: String::new(),
            purpose: "code".to_string(),
            lifecycle: "startup".to_string(),
            permissions: Some("0755".to_string()),
            resolution: Some("build".to_string()),
            self_ref: Some(true),
        }
    }

    #[test]
    fn verification_defaults_require_verification_to_true() {
        let verification: VerificationInfo = serde_json::from_value(json!({
            "integrity_seal": {
                "required": true,
                "algorithm": "ed25519"
            },
            "signed": false
        }))
        .expect("deserialize verification info");

        assert!(verification.require_verification);
        assert_eq!(verification.integrity_seal.algorithm, "ed25519");
        assert!(!verification.signed);
    }

    #[test]
    fn metadata_round_trips_full_structure() {
        let metadata = Metadata {
            format: "PSPF/2025".to_string(),
            format_version: Some("1.0.0".to_string()),
            package: PackageInfo {
                name: "demo".to_string(),
                version: "1.2.3".to_string(),
            },
            slots: vec![sample_slot()],
            execution: ExecutionInfo {
                primary_slot: 0,
                command: "run".to_string(),
                env: HashMap::from([(String::from("MODE"), String::from("test"))]),
            },
            verification: Some(VerificationInfo {
                integrity_seal: IntegritySealInfo {
                    required: true,
                    algorithm: "ed25519".to_string(),
                },
                signed: true,
                require_verification: true,
                trust_signatures: Some(TrustSignaturesInfo {
                    required: false,
                    signers: vec![SignerInfo {
                        name: "primary".to_string(),
                        key_id: "key-1".to_string(),
                        algorithm: "ed25519".to_string(),
                    }],
                }),
            }),
            build: Some(BuildInfo {
                tool: "flavor-rs".to_string(),
                tool_version: "0.3.21".to_string(),
                timestamp: "2026-03-31T00:00:00Z".to_string(),
                deterministic: true,
                platform: PlatformInfo {
                    os: "linux".to_string(),
                    arch: "x86_64".to_string(),
                    host: Some("linux/x86_64 test-host".to_string()),
                },
            }),
            launcher: Some(LauncherInfo {
                tool: "launcher".to_string(),
                tool_version: "1.0.0".to_string(),
                size: 42,
                checksum: "sha256:abcd".to_string(),
                capabilities: vec!["mmap".to_string(), "signed".to_string()],
            }),
            compatibility: Some(CompatibilityInfo {
                min_format_version: "1.0.0".to_string(),
                features: vec!["strict".to_string()],
            }),
            cache_validation: Some(CacheValidationInfo {
                check_file: "marker.txt".to_string(),
                expected_content: "ok".to_string(),
            }),
            runtime: Some(RuntimeInfo {
                env: Some(RuntimeEnv {
                    unset: Some(vec!["OLD".to_string()]),
                    map: Some(HashMap::from([(String::from("A"), String::from("B"))])),
                    set: Some(HashMap::from([(String::from("C"), String::from("D"))])),
                    pass: Some(vec!["PATH".to_string()]),
                }),
            }),
            workenv: Some(WorkenvInfo {
                directories: Some(vec![DirectorySpec {
                    path: "/tmp/demo".to_string(),
                    mode: Some("0700".to_string()),
                }]),
                env: Some(HashMap::from([(
                    String::from("WORKENV"),
                    String::from("1"),
                )])),
            }),
            setup_commands: vec![json!({"kind": "prepare"})],
            policy: Some(json!({"require_trusted_key": true})),
        };

        let encoded = serde_json::to_value(&metadata).expect("serialize metadata");
        let decoded: Metadata = serde_json::from_value(encoded).expect("deserialize metadata");

        assert_eq!(decoded.format, "PSPF/2025");
        assert_eq!(decoded.package.name, "demo");
        assert_eq!(decoded.package.version, "1.2.3");
        assert_eq!(decoded.slots.len(), 1);
        assert_eq!(decoded.slots[0].self_ref, Some(true));
        assert_eq!(
            decoded.execution.env.get("MODE").map(String::as_str),
            Some("test")
        );
        assert!(
            decoded
                .verification
                .expect("verification")
                .require_verification
        );
        assert!(decoded.build.expect("build").deterministic);
        assert_eq!(decoded.launcher.expect("launcher").tool, "launcher");
        assert_eq!(
            decoded
                .compatibility
                .expect("compatibility")
                .features
                .as_slice(),
            ["strict"]
        );
        assert_eq!(
            decoded
                .cache_validation
                .expect("cache validation")
                .check_file,
            "marker.txt"
        );
        assert!(decoded.runtime.is_some());
        assert!(decoded.workenv.is_some());
        assert_eq!(decoded.setup_commands.len(), 1);
        assert!(decoded.policy.is_some());
    }
}
