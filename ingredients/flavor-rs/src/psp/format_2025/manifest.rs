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

#[derive(Debug, Serialize, Deserialize)]
pub struct ManifestSlot {
    #[serde(skip_serializing_if = "Option::is_none")]
    pub slot: Option<i32>, // Slot number for well-formedness check
    pub path: String,
    pub name: String,
    #[serde(default)]
    pub encoding: String,
    #[serde(default = "default_purpose")]
    pub purpose: String,
    #[serde(default = "default_lifecycle")]
    pub lifecycle: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub extract_to: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub permissions: Option<String>, // Unix permissions as octal string (e.g., "0755")
}

fn default_purpose() -> String {
    "data".to_string()
}

fn default_lifecycle() -> String {
    "runtime".to_string()
}