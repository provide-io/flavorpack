//! CLI command handlers for PSPF/2025 packages

use crate::psp::format_2025::reader::Reader;
use std::path::Path;

/// Show package information
pub fn show_info(exe_path: &Path) -> i32 {
    log::trace!("show_info starting for: {:?}", exe_path);
    log::debug!("Creating reader for package");
    let mut reader = match Reader::new(exe_path) {
        Ok(r) => r,
        Err(e) => {
            eprintln!("Error: Failed to create reader: {}", e);
            return 1;
        }
    };

    // Clone the index and metadata to release the mutable borrow on the reader.
    let index = match reader.read_index() {
        Ok(idx) => idx.clone(),
        Err(e) => {
            eprintln!("Error: Failed to read index: {}", e);
            return 1;
        }
    };

    let metadata = match reader.read_metadata() {
        Ok(m) => m.clone(),
        Err(e) => {
            eprintln!("Error: Failed to read metadata: {}", e);
            return 1;
        }
    };

    // Detect launcher type from binary
    let launcher_type = detect_launcher_type(exe_path);

    // Get builder type from metadata
    let builder_type = if let Some(build) = &metadata.build {
        build.tool.clone()
    } else {
        "unknown/flavor-builder".to_string()
    };

    // Calculate total size and codec info
    let mut total_size = 0i64;
    let mut codec_types = std::collections::HashMap::new();

    for slot in &metadata.slots {
        total_size += slot.size;
        if !slot.operations.is_empty() && slot.operations != "none" {
            *codec_types.entry(slot.operations.clone()).or_insert(0) += 1;
        }
    }

    let codec_info = if codec_types.is_empty() {
        "none".to_string()
    } else {
        codec_types.keys().cloned().collect::<Vec<_>>().join(", ")
    };

    // Verification is now handled internally by read_index/read_metadata
    use crate::psp::format_2025::defaults::{ValidationLevel, get_validation_level};

    let verified = match get_validation_level() {
        ValidationLevel::None => "✓ (skipped)".to_string(),
        _ => "✓".to_string(),
    };

    // Copy packed fields to local variables to avoid unaligned access.
    let format_version = index.format_version;

    // Display info
    println!("📦 Package Information:");
    println!("  Name: {}", metadata.package.name);
    println!("  Version: {}", metadata.package.version);
    println!();
    println!("🔧 Build Information:");
    println!("  Format: PSPF/{:04x}", format_version);
    println!("  Builder: {}", builder_type);
    println!("  Launcher: {}", launcher_type);
    if let Some(build) = &metadata.build {
        println!("  Built: {}", build.timestamp);
    }
    println!();
    println!("📊 Package Details:");
    println!("  Slots: {} ({})", metadata.slots.len(), codec_info);
    println!("  Total Size: {:.2} MB", total_size as f64 / 1_048_576.0);
    println!("  Verified: {}", verified);
    println!();
    println!("🚀 Execution:");
    println!("  Command: {}", metadata.execution.command);

    0
}

/// Show raw metadata as JSON
pub fn show_metadata(exe_path: &Path) -> i32 {
    let mut reader = match Reader::new(exe_path) {
        Ok(r) => r,
        Err(e) => {
            eprintln!("Error: Failed to create reader: {}", e);
            return 1;
        }
    };

    let metadata = match reader.read_metadata() {
        Ok(m) => m.clone(),
        Err(e) => {
            eprintln!("Error: Failed to read metadata: {}", e);
            return 1;
        }
    };

    // Output raw JSON metadata
    match serde_json::to_string_pretty(&metadata) {
        Ok(json) => {
            println!("{}", json);
            0
        }
        Err(e) => {
            eprintln!("Error: Failed to encode metadata: {}", e);
            1
        }
    }
}

/// Verify bundle integrity
pub fn verify_bundle(exe_path: &Path) -> i32 {
    println!("🔍 Verifying PSPF package: {:?}", exe_path);

    let mut reader = match Reader::new(exe_path) {
        Ok(r) => r,
        Err(e) => {
            eprintln!("Error: Failed to create reader: {}", e);
            return 1;
        }
    };

    let mut errors = Vec::new();

    // Reading index and metadata performs the necessary checksum checks.
    let _index = match reader.read_index() {
        Ok(idx) => {
            let format_version = idx.format_version; // Copy to avoid unaligned access
            println!("  ✓ Valid PSPF magic");
            println!("  ✓ Format version: {:04x}", format_version);
            println!("  ✓ Index checksum valid");
            idx.clone()
        }
        Err(e) => {
            println!("  ✗ Index verification failed");
            errors.push(format!("Index error: {}", e));
            return 1;
        }
    };

    let metadata = match reader.read_metadata() {
        Ok(m) => {
            println!("  ✓ Metadata checksum valid");
            m.clone()
        }
        Err(e) => {
            println!("  ✗ Metadata verification failed");
            errors.push(format!("Metadata error: {}", e));
            return 1;
        }
    };

    // Check slots
    match reader.read_slot_descriptors() {
        Ok(descriptors) => {
            if descriptors.len() == metadata.slots.len() {
                println!("  ✓ All {} slot descriptors valid", metadata.slots.len());
            } else {
                errors.push(format!(
                    "Slot descriptor count mismatch: expected {}, got {}",
                    metadata.slots.len(),
                    descriptors.len()
                ));
            }
        }
        Err(e) => {
            errors.push(format!("Failed to read slot descriptors: {}", e));
        }
    }

    if errors.is_empty() {
        println!("\n✓ Bundle verification passed");
        0
    } else {
        println!("\n✗ Bundle verification failed:");
        for err in &errors {
            println!("  - {}", err);
        }
        1
    }
}

/// Extract a specific slot
pub fn extract_slot(exe_path: &Path, slot_str: &str, output_dir: &str) -> i32 {
    let slot_index = if let Ok(idx) = slot_str.parse::<usize>() {
        idx
    } else {
        eprintln!("Error: Invalid slot index: {}", slot_str);
        return 1;
    };

    let mut reader = match Reader::new(exe_path) {
        Ok(r) => r,
        Err(e) => {
            eprintln!("Error: Failed to create reader: {}", e);
            return 1;
        }
    };

    let metadata = match reader.read_metadata() {
        Ok(m) => m,
        Err(e) => {
            eprintln!("Error: Failed to read metadata: {}", e);
            return 1;
        }
    };

    if slot_index >= metadata.slots.len() {
        eprintln!(
            "Error: Slot index {} out of range (0-{})",
            slot_index,
            metadata.slots.len() - 1
        );
        return 1;
    }

    let slot = &metadata.slots[slot_index];
    println!("📦 Extracting slot {}: {}", slot_index, slot.id);
    println!("  Size: {} bytes", slot.size);
    println!("  Target: {}", slot.target);

    // Create output directory
    let output_path = Path::new(output_dir);
    if let Err(e) = std::fs::create_dir_all(output_path) {
        eprintln!("Error: Failed to create output directory: {}", e);
        return 1;
    }

    // Extract the slot
    match reader.extract_slot(slot_index, output_path) {
        Ok(_) => {
            println!("✓ Extracted to: {}", output_path.display());
            0
        }
        Err(e) => {
            eprintln!("Error: Failed to extract slot: {}", e);
            1
        }
    }
}

/// Detect launcher type from binary
fn detect_launcher_type(exe_path: &Path) -> String {
    use std::fs::File;
    use std::io::Read;

    let mut file = match File::open(exe_path) {
        Ok(f) => f,
        Err(_) => return "unknown".to_string(),
    };

    let mut buffer = vec![0u8; 4096];
    if file.read(&mut buffer).is_err() {
        return "unknown".to_string();
    }

    let header_str = String::from_utf8_lossy(&buffer);

    if header_str.contains("go.buildid") || header_str.contains("runtime.main") {
        "go".to_string()
    } else if header_str.contains("rust_panic") || header_str.contains("_ZN") {
        "rust".to_string()
    } else if header_str.starts_with("#!/usr/bin/env python")
        || header_str.starts_with("#!/usr/bin/python")
    {
        "python".to_string()
    } else if header_str.starts_with("#!/usr/bin/env node")
        || header_str.starts_with("#!/usr/bin/node")
    {
        "node".to_string()
    } else {
        "unknown".to_string()
    }
}
