//! PSPF/2025 package builder

mod finalization;
mod metadata;
mod slot_processor;

use finalization::{
    finalize_package, reserve_descriptor_space, stream_slot_data, write_descriptor_table,
    write_metadata_bytes,
};
use metadata::{compress_and_sign_metadata, create_metadata};
use slot_processor::SlotProcessor;

use super::constants::HEADER_SIZE;
use super::defaults::{CAPABILITY_MMAP, CAPABILITY_SIGNED};
use super::index::Index;
use super::keys::load_or_generate_keys;
use super::manifest::BuildManifest;
use super::trust::compute_key_fingerprint;
use crate::api::BuildOptions;
use crate::exceptions::{FlavorError, Result};
use log::{debug, info, trace};
use std::fs::{self, File};
use std::io::{Seek, SeekFrom, Write};
use std::path::{Path, PathBuf};
use std::time::Instant;

/// Build a PSPF/2025 package
pub fn build(manifest_path: &Path, output_path: &Path, options: BuildOptions) -> Result<()> {
    let _start_time = Instant::now();
    info!("🦀🦀🦀 Hello from Flavor's Rust Builder 🦀🦀🦀");
    info!("PSPF Rust Builder starting...");
    info!("🔨 Building PSPF/2025 package from: {manifest_path:?}");
    trace!("🔍 Build options: {:?}", options);

    // Phase 1: Initialize package components
    let manifest = read_manifest(manifest_path)?;
    let mut out = File::create(output_path)?;
    trace!("📄 Created output file: {:?}", output_path);

    // Phase 2: Write launcher and setup index
    let (launcher_size, launcher_data) = write_launcher(&mut out, &options)?;
    let (signing_key, public_key) = load_or_generate_keys(&options)?;
    let mut index = initialize_index(launcher_size, &public_key);

    // Skip index block space
    let data_start = launcher_size + HEADER_SIZE as u64;
    out.seek(SeekFrom::Start(data_start))?;
    debug!(
        "📍 Data section starts at {:#x} (after launcher {:#x} + index 512)",
        data_start, launcher_size
    );

    // Phase 3: Process slots and create metadata
    let mut metadata = create_metadata(&manifest, launcher_size, &launcher_data, &options)?;

    // Use the new SlotProcessor for all slot processing
    let mut slot_processor = SlotProcessor::new(manifest.slots.clone());
    slot_processor.process_slots()?;
    metadata.slots = slot_processor.metadata_slots;

    // Phase 4: Write metadata and setup index
    let compressed_metadata = compress_and_sign_metadata(&metadata, &signing_key, &mut index)?;
    write_metadata_bytes(&mut out, &compressed_metadata, &mut index)?;

    // Phase 5: Reserve space for descriptor table
    let descriptor_table_offset =
        reserve_descriptor_space(&mut out, &slot_processor.slot_descriptors, &mut index)?;

    // Phase 6: Write slot data and update descriptors
    let mut slot_descriptors = slot_processor.slot_descriptors;
    stream_slot_data(&mut out, &mut slot_descriptors, &slot_processor.slot_paths)?;

    // Phase 7: Write descriptor table at reserved location
    let end_pos = write_descriptor_table(&mut out, &slot_descriptors, descriptor_table_offset)?;

    // Phase 8: Finalize package with MagicTrailer
    finalize_package(
        &mut out,
        &mut index,
        end_pos,
        output_path,
        &manifest,
        &options,
    )?;

    // Phase 9: Convert to PE resource embedding if needed (Windows + Go launcher)
    drop(out); // Close the file before resource embedding
    if should_use_resource_embedding(&launcher_data)? {
        info!("🪟 Converting to PE resource embedding (Windows Go launcher)");
        convert_to_resource_embedding(output_path, launcher_size)?;
        info!("✅ Successfully embedded PSPF as PE resource");
    }

    Ok(())
}

/// Read and parse the build manifest
fn read_manifest(manifest_path: &Path) -> Result<BuildManifest> {
    let manifest_timer = Instant::now();
    let manifest_data = fs::read_to_string(manifest_path)?;
    let manifest: BuildManifest = serde_json::from_str(&manifest_data)
        .map_err(|e| FlavorError::Generic(format!("Failed to parse manifest: {e}")))?;
    trace!("✅ Manifest parsed in {:?}", manifest_timer.elapsed());
    Ok(manifest)
}

/// Write launcher binary to output file
fn write_launcher(out: &mut File, options: &BuildOptions) -> Result<(u64, Vec<u8>)> {
    let launcher_timer = Instant::now();
    let launcher_data = get_launcher(options)?;

    // Process launcher for Windows PE compatibility if needed
    let launcher_data = super::pe_utils::process_launcher_for_pspf(launcher_data)?;

    let launcher_size = launcher_data.len() as u64;
    debug!(
        "🚀 Loaded and processed launcher: {} bytes in {:?}",
        launcher_size,
        launcher_timer.elapsed()
    );

    let write_timer = Instant::now();
    out.write_all(&launcher_data)?;
    trace!("✍️ Wrote launcher in {:?}", write_timer.elapsed());

    Ok((launcher_size, launcher_data))
}

/// Initialize the index structure
fn initialize_index(launcher_size: u64, public_key: &ed25519_dalek::VerifyingKey) -> Index {
    trace!("📦 Creating PSPF/2025 index structure");
    let mut index = Index::new();
    index.launcher_size = launcher_size;
    index.public_key.copy_from_slice(public_key.as_bytes());
    if let Ok(fp) = compute_key_fingerprint(public_key.as_bytes()) {
        index.attestation_key_fp[..64].copy_from_slice(fp.as_bytes());
    }
    index.capabilities = CAPABILITY_MMAP | CAPABILITY_SIGNED;

    index
}

/// Get launcher binary data
fn get_launcher(options: &BuildOptions) -> Result<Vec<u8>> {
    // Priority order:
    // 1. Explicit launcher_bin from options
    // 2. FLAVOR_LAUNCHER_BIN environment variable
    // No fallback - launcher must be explicitly specified

    let launcher_path = if let Some(ref explicit_path) = options.launcher_bin {
        explicit_path.clone()
    } else if let Ok(explicit_path) = std::env::var(crate::env_vars::LAUNCHER_BIN) {
        PathBuf::from(explicit_path)
    } else {
        return Err(FlavorError::Generic(
            "Launcher binary path must be specified via --launcher-bin or FLAVOR_LAUNCHER_BIN environment variable".to_string()
        ));
    };

    info!("🚀 Loading launcher: {}", launcher_path.display());

    // Check launcher version
    let version_output = std::process::Command::new(&launcher_path)
        .arg("--version")
        .output();

    match version_output {
        Ok(output) => {
            let version_str = String::from_utf8_lossy(&output.stdout);
            let version_str = version_str.trim();
            if !version_str.is_empty() {
                info!("🔍 Launcher version: {}", version_str);
            }
        }
        Err(e) => {
            debug!("⚠️ Failed to get launcher version: {}", e);
        }
    }

    // Just try to read the file - let the OS handle PATH resolution
    fs::read(&launcher_path).map_err(|e| {
        FlavorError::Generic(format!(
            "Failed to read launcher '{}': {}",
            launcher_path.display(),
            e
        ))
    })
}

/// Determines if PE resource embedding should be used.
///
/// TEMPORARILY DISABLED: The Windows UpdateResourceW API corrupts Go binaries
/// even though it reports success. The Go builder uses a PE reconstruction library
/// (winres) which works correctly, but there's no Rust equivalent for runtime PE
/// modification. Until we implement proper PE reconstruction in Rust, we fall back
/// to overlay mode (appended data) for all launchers.
///
/// See: Phase 31 analysis - UpdateResourceW corrupts Go launcher entry point
/// NOTE: PE reconstruction via a Rust winres equivalent is a known future enhancement.
fn should_use_resource_embedding(_launcher_data: &[u8]) -> Result<bool> {
    // Disabled until we have proper PE reconstruction
    Ok(false)
}

/// Converts a PSP file from append mode to PE resource embedding.
///
/// This function:
/// 1. Reads the entire PSP file
/// 2. Extracts the PSPF data (everything after the launcher)
/// 3. Truncates the file to just the launcher
/// 4. Embeds the PSPF data as a PE resource
///
/// This is necessary for Go launchers on Windows, as they reject appended data.
fn convert_to_resource_embedding(file_path: &Path, launcher_size: u64) -> Result<()> {
    use super::pe_resources::embed_pspf_as_resource;

    debug!("📖 Reading PSP file to extract PSPF data");
    debug!("   File: {}", file_path.display());
    debug!("   Launcher size: {} bytes", launcher_size);

    // Read the entire file
    let file_data = fs::read(file_path)?;
    let file_size = file_data.len() as u64;

    debug!("   Total file size: {} bytes", file_size);
    debug!("   PSPF data size: {} bytes", file_size - launcher_size);

    // Extract PSPF data (everything after launcher)
    // Copy to a new Vec to ensure it's not tied to the original file data
    let pspf_data: Vec<u8> = file_data[launcher_size as usize..].to_vec();

    if pspf_data.is_empty() {
        return Err(FlavorError::Generic(
            "No PSPF data found after launcher".to_string(),
        ));
    }
    debug!("   Copied PSPF data to separate buffer");

    debug!("✂️  Truncating file to launcher size");

    // Truncate file to launcher size (in-place modification)
    // This is safer than fs::write() as it preserves file attributes
    {
        use std::fs::OpenOptions;

        let file = OpenOptions::new().write(true).open(file_path)?;
        file.set_len(launcher_size)?;

        // Explicitly sync file metadata and data to disk
        // This ensures the truncation is committed before resource embedding
        file.sync_all()?;
        debug!("   Synced truncation to disk");
    }

    // Verify the truncation was successful
    let truncated_size = fs::metadata(file_path)?.len();
    if truncated_size != launcher_size {
        return Err(FlavorError::Generic(format!(
            "File truncation failed: expected {} bytes, got {} bytes",
            launcher_size, truncated_size
        )));
    }
    debug!("   Verified truncated size: {} bytes", truncated_size);

    debug!(
        "📦 Embedding {} bytes of PSPF data as PE resource",
        pspf_data.len()
    );

    // Embed PSPF data as resource
    embed_pspf_as_resource(file_path, &pspf_data)?;

    let final_size = fs::metadata(file_path)?.len();
    debug!("✅ Conversion complete: final size {} bytes", final_size);

    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::psp::PackageFormat;
    use crate::psp::format_2025::constants::{
        HEADER_SIZE, MAGIC_TRAILER_SIZE, MAGIC_WAND_EMOJI_BYTES, PACKAGE_EMOJI_BYTES,
    };
    use std::fs;
    use tempfile::tempdir;

    fn write_launcher_script(path: &Path) {
        #[cfg(unix)]
        {
            let script = b"#!/bin/sh\nif [ \"$1\" = \"--version\" ]; then\n  echo launcher 1.0\nfi\nexit 0\n";
            fs::write(path, script).expect("write launcher script");
            let mut perms = fs::metadata(path).expect("launcher metadata").permissions();
            std::os::unix::fs::PermissionsExt::set_mode(&mut perms, 0o755);
            fs::set_permissions(path, perms).expect("set launcher executable");
        }

        #[cfg(windows)]
        {
            let script =
                b"@echo off\r\nif \"%1\"==\"--version\" echo launcher 1.0\r\nexit /b 0\r\n";
            fs::write(path, script).expect("write launcher script");
        }
    }

    fn write_manifest(path: &Path) {
        let manifest = serde_json::json!({
            "package": {
                "name": "demo",
                "version": "1.2.3"
            },
            "execution": {
                "command": "run",
                "env": {}
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
            ]
        });
        fs::write(
            path,
            serde_json::to_vec_pretty(&manifest).expect("serialize manifest"),
        )
        .expect("write manifest");
    }

    #[test]
    fn build_smoke_test_creates_pspf_package() {
        let dir = tempdir().expect("tempdir");
        let manifest_path = dir.path().join("manifest.json");
        let output_path = dir.path().join("package.pspf");
        let launcher_path = dir.path().join(if cfg!(windows) {
            "launcher.cmd"
        } else {
            "launcher.sh"
        });

        write_launcher_script(&launcher_path);
        write_manifest(&manifest_path);

        let options = BuildOptions {
            launcher_bin: Some(launcher_path.clone()),
            skip_verification: false,
            private_key_path: None,
            public_key_path: None,
            key_seed: Some("builder-test-seed".to_string()),
            workenv_base: None,
        };

        build(&manifest_path, &output_path, options).expect("build package");
        assert!(output_path.exists());

        let format = crate::psp::detect_format(&output_path).expect("detect package format");
        assert_eq!(format, PackageFormat::PSPF2025);

        let bytes = fs::read(&output_path).expect("read package");
        assert!(bytes.len() >= MAGIC_TRAILER_SIZE);
        assert!(bytes.ends_with(MAGIC_WAND_EMOJI_BYTES));
        assert_eq!(
            &bytes[bytes.len() - MAGIC_TRAILER_SIZE..bytes.len() - MAGIC_TRAILER_SIZE + 4],
            PACKAGE_EMOJI_BYTES
        );

        let trailer_start = bytes.len() - MAGIC_TRAILER_SIZE;
        let trailer_index = &bytes[trailer_start + 4..trailer_start + 4 + HEADER_SIZE];
        let index =
            crate::psp::format_2025::Index::unpack(trailer_index).expect("unpack package index");
        let package_size = index.package_size;
        let slot_count = index.slot_count;
        assert_eq!(package_size, bytes.len() as u64);
        assert_eq!(slot_count, 1);
        assert_ne!(
            index.attestation_key_fp, [0u8; 64],
            "attestation_key_fp should be populated for signed bundles"
        );
    }

    // This test verifies that on non-Windows, the file is truncated before the
    // "only supported on Windows" error is returned from embed_pspf_as_resource.
    // On Windows, embed_pspf_as_resource succeeds, so this test is non-Windows only.
    #[cfg(not(target_os = "windows"))]
    #[test]
    fn convert_to_resource_embedding_truncates_before_windows_error() {
        let dir = tempdir().expect("tempdir");
        let file_path = dir.path().join("bundle.pspf");
        let original = b"launcher-data-pspf-payload";
        fs::write(&file_path, original).expect("write package bytes");

        let result = convert_to_resource_embedding(&file_path, 13);
        assert!(result.is_err());
        assert!(
            result
                .err()
                .expect("error")
                .to_string()
                .contains("only supported on Windows")
        );

        let truncated_size = fs::metadata(&file_path).expect("metadata").len();
        assert_eq!(truncated_size, 13);
    }
}
