//! Build manifest structures for PSPF/2025

use serde::{Deserialize, Serialize};
use std::collections::HashMap;

/// Build manifest structure - matches PSPF/2025 spec
#[derive(Debug, Serialize, Deserialize)]
pub struct BuildManifest {
    pub package: PackageInfo,
    pub execution: ExecutionInfo,
    pub slots: Vec<ManifestSlot>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub cache_validation: Option<serde_json::Value>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub runtime: Option<serde_json::Value>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub workenv: Option<serde_json::Value>,
    #[serde(default)]
    pub setup_commands: Vec<serde_json::Value>,
}

/// Package information
#[derive(Debug, Serialize, Deserialize)]
pub struct PackageInfo {
    pub name: String,
    pub version: String,
    #[serde(default)]
    pub description: String,
}

/// Execution information
#[derive(Debug, Serialize, Deserialize)]
pub struct ExecutionInfo {
    pub command: String,
    #[serde(default)]
    pub env: HashMap<String, String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ManifestSlot {
    #[serde(skip_serializing_if = "Option::is_none")]
    pub slot: Option<i32>, // Optional: position validator
    pub id: String,     // Arbitrary identifier for the slot
    pub source: String, // Source path within the package
    pub target: String, // Destination path in workenv
    #[serde(default)]
    pub operations: String, // Operations chain (e.g., "gzip", "tar.gz")
    #[serde(default = "default_purpose")]
    pub purpose: String, // Role of the slot
    #[serde(default = "default_lifecycle")]
    pub lifecycle: String, // Cache management
    #[serde(skip_serializing_if = "Option::is_none")]
    pub permissions: Option<String>, // Unix permissions as octal string (e.g., "0755")
    #[serde(skip_serializing_if = "Option::is_none")]
    pub resolution: Option<String>, // When to resolve: build|runtime|lazy
}

fn default_purpose() -> String {
    "data".to_string()
}

fn default_lifecycle() -> String {
    "runtime".to_string()
}
