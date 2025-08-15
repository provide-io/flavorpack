//! PSPF metadata structures and types
//! 
//! This module defines all the metadata structures used in PSPF packages,
//! matching the PSPF 2025 specification.

use serde::{Deserialize, Serialize};
use serde_json::Value;
use std::collections::HashMap;

/// Main metadata structure for a PSPF package
#[derive(Debug, Deserialize, Serialize)]
pub struct Metadata {
    pub format: String,
    pub package: PackageInfo,
    pub slots: Vec<SlotMetadata>,
    pub execution: ExecutionInfo,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub build: Option<BuildInfo>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub cache_validation: Option<CacheValidationInfo>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub runtime: Option<RuntimeInfo>,
    #[serde(default)]
    pub setup_commands: Vec<Value>,
}

/// Package information
#[derive(Debug, Deserialize, Serialize)]
pub struct PackageInfo {
    pub name: String,
    pub version: String,
}

/// Slot metadata for each data slot in the package
/// 
/// Key fields:
/// - `size`: Size as stored in the package (after any compression)
/// - `encoding`: Indicates compression type ("none", "gzip")
/// - `extract_to`: Optional subdirectory for extraction
#[derive(Debug, Deserialize, Serialize)]
pub struct SlotMetadata {
    pub index: usize,
    pub name: String,
    pub size: i64,  // Size as stored in package
    pub checksum: String,
    pub encoding: String,  // Indicates compression type
    pub purpose: String,
    pub lifecycle: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub extract_to: Option<String>,  // Runtime extraction subdirectory
}

/// Execution configuration
#[derive(Debug, Deserialize, Serialize)]
pub struct ExecutionInfo {
    pub primary_slot: usize,
    pub command: String,
    #[serde(default)]
    pub environment: HashMap<String, String>,
}

/// Build information (optional)
#[derive(Debug, Deserialize, Serialize)]
pub struct BuildInfo {
    pub builder: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub version: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub timestamp: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub host: Option<String>,
}

/// Cache validation configuration
#[derive(Debug, Deserialize, Serialize)]
pub struct CacheValidationInfo {
    pub check_file: String,
    pub expected_content: String,
}

/// Runtime configuration
#[derive(Debug, Deserialize, Serialize)]
pub struct RuntimeInfo {
    #[serde(skip_serializing_if = "Option::is_none")]
    pub env: Option<RuntimeEnv>,
}

/// Runtime environment configuration
/// 
/// Operations are processed in this order:
/// 1. Analyze pass patterns (what to preserve)
/// 2. unset - Remove specified variables (except preserved)
/// 3. map - Rename variables
/// 4. set - Set specific values
/// 5. pass verification - Check required variables exist
#[derive(Debug, Deserialize, Serialize)]
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