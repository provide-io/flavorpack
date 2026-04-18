// SPDX-FileCopyrightText: Copyright (c) 2026 provide.io llc. All rights reserved.
// SPDX-License-Identifier: Apache-2.0

//! Slot extraction utilities

use super::super::metadata::Metadata;
use super::super::reader::Reader;
use crate::exceptions::Result;
use log::{debug, error, info};
use std::collections::HashMap;
use std::path::{Path, PathBuf};

fn normalize_slot_target(target: &str) -> PathBuf {
    PathBuf::from(target.replace("{workenv}/", "").replace("{workenv}", ""))
}

/// Extract slots from the package
pub(super) fn extract_slots(
    reader: &mut Reader,
    workenv_path: &Path,
) -> Result<(HashMap<usize, PathBuf>, Vec<PathBuf>)> {
    // Re-read metadata inside this function to avoid borrow issues
    debug!("📖 Reading metadata for slot extraction");
    let metadata = match reader.read_metadata() {
        Ok(m) => m.clone(),
        Err(e) => {
            error!("🚨 Failed to read metadata: {}", e);
            return Err(e);
        }
    };
    let mut slot_paths = HashMap::new();
    let mut init_paths = Vec::new();

    info!("📤 Extracting {} slots...", metadata.slots.len());

    // Print extraction progress to stderr
    use std::io::Write;
    let stderr = std::io::stderr();
    let mut stderr_handle = stderr.lock();

    // Extract slots by index
    for i in 0..metadata.slots.len() {
        let slot = &metadata.slots[i];
        debug!(
            "📦 Extracting slot {}: {} ({} bytes)",
            slot.index, slot.id, slot.size
        );
        debug!("  Source: {}", slot.source);
        debug!("  Target: {}", slot.target);
        debug!("  Lifecycle: {}", slot.lifecycle);
        debug!("  Permissions: {:?}", slot.permissions);

        // Write progress to stderr
        let _ = writeln!(
            stderr_handle,
            "[{}/{}] Extracting {}...",
            i + 1,
            metadata.slots.len(),
            slot.id
        );

        // Determine extraction path
        // Target field specifies where to extract (relative to workenv)
        // But extract_slot expects a directory, so we need to pass workenv_path
        // The extract_slot function will use the metadata to determine the target path

        // Extract the slot to workenv (it will use metadata.target internally)
        reader.extract_slot(i, workenv_path)?;

        let extracted_path = workenv_path.join(normalize_slot_target(&slot.target));
        debug!("✅ Extracted to: {extracted_path:?}");

        // Track init slots for later cleanup (removed after initialization)
        if slot.lifecycle == "init" {
            debug!("📌 Marking slot {} as init for cleanup", slot.index);
            init_paths.push(extracted_path.clone());
        }

        slot_paths.insert(i, extracted_path);
    }

    Ok((slot_paths, init_paths))
}

/// Build slot paths without extraction (when cache is valid)
pub(super) fn build_slot_paths(
    metadata: &Metadata,
    workenv_path: &Path,
) -> HashMap<usize, PathBuf> {
    let mut slot_paths = HashMap::new();

    for slot in &metadata.slots {
        // Target field specifies where to extract (relative to workenv)
        let slot_path = workenv_path.join(normalize_slot_target(&slot.target));
        slot_paths.insert(slot.index, slot_path);
    }

    slot_paths
}

#[cfg(test)]
mod tests {
    use super::super::super::metadata::{ExecutionInfo, Metadata, PackageInfo, SlotMetadata};
    use super::*;
    use crate::api::BuildOptions;
    use crate::psp::format_2025::build;
    use serde_json::json;
    use std::collections::HashMap;
    use std::fs;
    use tempfile::tempdir;

    fn build_real_bundle(temp: &tempfile::TempDir) -> PathBuf {
        let payload = temp.path().join("payload.txt");
        fs::write(&payload, b"payload contents").expect("write payload");
        let launcher = temp.path().join(if cfg!(windows) {
            "launcher.bat"
        } else {
            "launcher.sh"
        });
        let launcher_bytes = if cfg!(windows) {
            b"@echo off\r\nexit /b 0\r\n".as_slice()
        } else {
            b"#!/bin/sh\nexit 0\n".as_slice()
        };
        fs::write(&launcher, launcher_bytes).expect("write launcher");

        let manifest_path = temp.path().join("manifest.json");
        let output_path = temp.path().join("bundle.pspf");
        let manifest = json!({
            "package": {
                "name": "launcher-extraction-demo",
                "version": "1.0.0"
            },
            "execution": {
                "command": if cfg!(windows) { "cmd /C exit 0" } else { "true" },
                "env": {}
            },
            "slots": [
                {
                    "slot": 0,
                    "id": "payload",
                    "source": payload.display().to_string(),
                    "target": "bin/payload.txt",
                    "operations": "",
                    "purpose": "payload",
                    "lifecycle": "runtime",
                    "permissions": "0644"
                }
            ]
        });
        fs::write(
            &manifest_path,
            serde_json::to_vec_pretty(&manifest).expect("serialize manifest"),
        )
        .expect("write manifest");

        let options = BuildOptions {
            launcher_bin: Some(launcher),
            skip_verification: false,
            private_key_path: None,
            public_key_path: None,
            key_seed: Some("launcher-extraction-test-seed".to_string()),
            workenv_base: None,
        };

        build(&manifest_path, &output_path, options).expect("build real bundle");
        output_path
    }

    fn sample_metadata(slot_target: &str) -> Metadata {
        Metadata {
            format: "PSPF/2025".to_string(),
            format_version: None,
            package: PackageInfo {
                name: "demo".to_string(),
                version: "1.0.0".to_string(),
            },
            slots: vec![SlotMetadata {
                index: 0,
                id: "slot-0".to_string(),
                source: "source".to_string(),
                target: slot_target.to_string(),
                size: 0,
                checksum: String::new(),
                operations: String::new(),
                purpose: String::new(),
                lifecycle: String::new(),
                permissions: None,
                resolution: None,
                self_ref: None,
            }],
            execution: ExecutionInfo {
                primary_slot: 0,
                command: "run".to_string(),
                env: HashMap::new(),
            },
            verification: None,
            build: None,
            launcher: None,
            compatibility: None,
            cache_validation: None,
            runtime: None,
            workenv: None,
            setup_commands: Vec::new(),
            policy: None,
        }
    }

    #[test]
    fn build_slot_paths_strips_workenv_placeholder() {
        let metadata = sample_metadata("{workenv}/bin/tool");
        let workenv = Path::new("/tmp/workenv");

        let slot_paths = build_slot_paths(&metadata, workenv);

        assert_eq!(slot_paths.get(&0), Some(&workenv.join("bin/tool")));
    }

    #[test]
    fn build_slot_paths_handles_plain_relative_targets() {
        let metadata = sample_metadata("lib/example.bin");
        let workenv = Path::new("/tmp/workenv");

        let slot_paths = build_slot_paths(&metadata, workenv);

        assert_eq!(slot_paths.get(&0), Some(&workenv.join("lib/example.bin")));
    }

    #[test]
    fn extract_slots_extracts_real_bundle_payload_and_tracks_init_slots() {
        let temp = tempdir().expect("tempdir");
        let bundle = build_real_bundle(&temp);
        let mut reader = Reader::new(&bundle).expect("reader");
        let workenv = temp.path().join("workenv");

        let (slot_paths, init_paths) = extract_slots(&mut reader, &workenv).expect("extract slots");

        let payload = workenv.join("bin/payload.txt");
        assert_eq!(slot_paths.get(&0), Some(&payload));
        assert!(init_paths.is_empty());
        assert_eq!(
            fs::read_to_string(payload).expect("read extracted payload"),
            "payload contents"
        );
    }
}
