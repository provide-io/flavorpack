// SPDX-FileCopyrightText: Copyright (c) 2026 provide.io llc. All rights reserved.
// SPDX-License-Identifier: Apache-2.0

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

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::json;

    #[test]
    fn manifest_slot_deserializes_default_fields() {
        let slot: ManifestSlot = serde_json::from_value(json!({
            "id": "launcher",
            "source": "$SELF",
            "target": "/app/bin/launcher"
        }))
        .expect("deserialize manifest slot");

        assert_eq!(slot.slot, None);
        assert_eq!(slot.operations, "");
        assert_eq!(slot.purpose, "data");
        assert_eq!(slot.lifecycle, "runtime");
        assert_eq!(slot.permissions, None);
        assert_eq!(slot.resolution, None);
    }

    #[test]
    fn build_manifest_deserializes_optional_sections() {
        let manifest: BuildManifest = serde_json::from_value(json!({
            "package": {
                "name": "demo",
                "version": "1.2.3"
            },
            "execution": {
                "command": "run",
                "env": {
                    "MODE": "test"
                }
            },
            "slots": [
                {
                    "slot": 0,
                    "id": "launcher",
                    "source": "$SELF",
                    "target": "/app/bin/launcher",
                    "purpose": "code",
                    "lifecycle": "startup"
                }
            ],
            "setup_commands": [
                {"kind": "prepare"}
            ],
            "cache_validation": {
                "check_file": "marker.txt",
                "expected_content": "ok"
            },
            "runtime": {
                "env": {
                    "set": {
                        "MODE": "test"
                    }
                }
            },
            "workenv": {
                "directories": [
                    {"path": "/tmp/demo"}
                ]
            }
        }))
        .expect("deserialize build manifest");

        assert_eq!(manifest.package.description, "");
        assert_eq!(
            manifest.execution.env.get("MODE").map(String::as_str),
            Some("test")
        );
        assert_eq!(manifest.slots.len(), 1);
        assert_eq!(manifest.slots[0].purpose, "code");
        assert_eq!(manifest.slots[0].lifecycle, "startup");
        assert!(manifest.cache_validation.is_some());
        assert!(manifest.runtime.is_some());
        assert!(manifest.workenv.is_some());
        assert_eq!(manifest.setup_commands.len(), 1);
    }
}
