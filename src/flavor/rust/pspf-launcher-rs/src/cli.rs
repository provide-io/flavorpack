//! CLI command implementations for PSPF launcher
//! 
//! This module provides the command-line interface commands
//! available when running a PSPF bundle with FLAVOR_LAUNCHER_CLI=true

use anyhow::{anyhow, Context, Result};
use std::fs;
use std::path::Path;
use std::process::{Command, Stdio};
use tempfile::tempdir;

use crate::metadata::Metadata;
use crate::reader::Reader;

/// Show information about a PSPF bundle
pub fn show_bundle_info(exe_path: &Path) -> Result<()> {
    let mut reader = Reader::new(exe_path)?;
    let index = reader.read_index()?;
    let metadata = reader.read_metadata()?;
    
    // Detect launcher type
    let launcher_type = detect_launcher_type(exe_path);
    let builder_type = detect_builder_type(&metadata);
    
    // Calculate encoding info
    let mut encoding_types = std::collections::HashSet::new();
    
    for slot in &metadata.slots {
        if !slot.encoding.is_empty() && slot.encoding != "none" {
            encoding_types.insert(slot.encoding.clone());
        }
    }
    
    let encoding_info = if encoding_types.is_empty() {
        "none".to_string()
    } else {
        let types: Vec<_> = encoding_types.into_iter().collect();
        types.join(", ")
    };
    
    // Verify status
    let verify_status = if reader.verify_magic().is_ok() { "✓" } else { "✗" };
    
    println!("{} v{} [PSPF/{}]", 
        metadata.package.name, 
        metadata.package.version,
        metadata.format.trim_start_matches("PSPF/"));
    
    println!("Built with: {} | Launcher: {} | Size: {:.1}MB",
        builder_type,
        launcher_type,
        index.package_size as f64 / (1024.0 * 1024.0));
    
    let slot_count = metadata.slots.len();
    println!("Slots: {} ({}) | Verified: {}",
        slot_count,
        encoding_info,
        verify_status);
    
    if let Some(exec) = metadata.execution.command.split_whitespace().next() {
        println!("\nRun with: {}", exec);
    }
    println!("CLI Mode: Use 'run' to execute, 'extract' to unpack");
    
    Ok(())
}

/// Run the bundle with the provided arguments
pub fn run_bundle(exe_path: &Path, args: &[String]) -> Result<()> {
    // Unset CLI environment variable and re-execute
    unsafe {
        std::env::remove_var("FLAVOR_LAUNCHER_CLI");
    }
    
    let status = Command::new(exe_path)
        .args(args)
        .stdin(Stdio::inherit())
        .stdout(Stdio::inherit())
        .stderr(Stdio::inherit())
        .status()?;
    
    std::process::exit(status.code().unwrap_or(1));
}

/// Extract a specific slot from the bundle
pub fn extract_slot(exe_path: &Path, slot_str: &str, output_dir: &str) -> Result<()> {
    let slot_index = slot_str.parse::<usize>()
        .context("Invalid slot index")?;
    
    let mut reader = Reader::new(exe_path)?;
    let metadata = reader.read_metadata()?;
    
    if slot_index >= metadata.slots.len() {
        return Err(anyhow!("Slot index out of range"));
    }
    
    let slot_name = metadata.slots[slot_index].name.clone();
    let output_path = reader.extract_slot(slot_index, Path::new(output_dir))?;
    
    println!("Extracted slot {} ({}) to {}", 
        slot_index, slot_name, output_path.display());
    
    Ok(())
}

/// Show the metadata JSON for a bundle
pub fn show_metadata(exe_path: &Path) -> Result<()> {
    let mut reader = Reader::new(exe_path)?;
    let metadata = reader.read_metadata()?;
    
    let json = serde_json::to_string_pretty(&metadata)?;
    println!("{}", json);
    
    Ok(())
}

/// Verify the integrity of a bundle
pub fn verify_bundle(exe_path: &Path) -> Result<()> {
    println!("Verifying bundle integrity...");
    
    let mut errors = Vec::new();
    let mut reader = Reader::new(exe_path)?;
    
    // Check magic
    match reader.verify_magic() {
        Ok(_) => println!("✓ Magic sequence valid"),
        Err(e) => errors.push(format!("Magic verification failed: {}", e)),
    }
    
    // Check index
    match reader.read_index() {
        Ok(_) => println!("✓ Index checksum valid"),
        Err(e) => errors.push(format!("Index verification failed: {}", e)),
    }
    
    // Check metadata
    match reader.read_metadata() {
        Ok(metadata) => {
            println!("✓ Metadata checksum valid");
            
            // Check each slot
            for (i, slot) in metadata.slots.iter().enumerate() {
                // Verify slot by trying to extract it to temp dir
                match tempdir() {
                    Ok(temp_dir) => {
                        match reader.extract_slot(i, temp_dir.path()) {
                            Ok(_) => println!("✓ Slot {} ({}) checksum valid", i, slot.name),
                            Err(e) => errors.push(format!("Slot {} ({}) verification failed: {}", i, slot.name, e)),
                        }
                    }
                    Err(e) => errors.push(format!("Failed to create temp dir for slot {} verification: {}", i, e)),
                }
            }
        }
        Err(e) => errors.push(format!("Metadata verification failed: {}", e)),
    }
    
    if errors.is_empty() {
        println!("\n✓ Bundle verification passed");
    } else {
        println!("\n✗ Bundle verification failed:");
        for err in errors {
            println!("  - {}", err);
        }
        std::process::exit(1);
    }
    
    Ok(())
}

// Helper functions

/// Detect the launcher type by examining the binary
fn detect_launcher_type(exe_path: &Path) -> String {
    // Check filename patterns
    if let Some(filename) = exe_path.file_name().and_then(|f| f.to_str()) {
        if filename.contains("rust") {
            return "rust".to_string();
        }
        if filename.contains("go") {
            return "go".to_string();
        }
    }
    
    // Fall back to binary inspection
    if let Ok(data) = fs::read(exe_path) {
        let size = data.len().min(65536);
        let header = &data[..size];
        
        // Rust binaries
        if header.windows(10).any(|w| w == b"rust_panic") || 
           header.windows(3).any(|w| w == b"_ZN") {
            return "rust".to_string();
        }
        
        // Go binaries
        if header.windows(10).any(|w| w == b"go.buildid") ||
           header.windows(7).any(|w| w == b"runtime") {
            return "go".to_string();
        }
    }
    
    "unknown".to_string()
}

/// Detect the builder type from metadata
fn detect_builder_type(metadata: &Metadata) -> String {
    if let Some(build_info) = &metadata.build {
        return build_info.builder.clone();
    }
    "unknown/pspf-builder".to_string()
}