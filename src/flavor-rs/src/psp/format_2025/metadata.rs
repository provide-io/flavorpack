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
    pub host: String,
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
