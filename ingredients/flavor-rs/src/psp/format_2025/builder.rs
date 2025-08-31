//! PSPF/2025 package builder

use super::checksums::{calculate_checksum, ChecksumAlgorithm};
use super::{
    constants::*,
    index::Index,
    keys::load_or_generate_keys,
    manifest::BuildManifest,
    metadata::*,
    slots::{align_offset, SlotDescriptor},
};
use crate::api::BuildOptions;
use crate::exceptions::{FlavorError, Result};
use ed25519_dalek::{Signature, Signer};
use log::{debug, error, info, trace, warn};
use std::fs::{self, File};
use std::io::{self, BufReader, Read, Seek, SeekFrom, Write};
use std::path::{Path, PathBuf};
use std::time::Instant;

// BuildManifest and ManifestSlot now imported from manifest module
// Key loading functions now in keys module

/// Get the builder's compilation timestamp
#[allow(dead_code)]
fn get_builder_timestamp() -> Option<String> {
    // Try to get the builder's own modification time
    if let Ok(current_exe) = std::env::current_exe() {
        if let Ok(metadata) = std::fs::metadata(&current_exe) {
            if let Ok(modified) = metadata.modified() {
                // Convert SystemTime to chrono DateTime
                let datetime: chrono::DateTime<chrono::Utc> = modified.into();
                return Some(datetime.to_rfc3339());
            }
        }
    }

    // Fallback: use compile-time env var if available
    option_env!("SOURCE_DATE_EPOCH")
        .map(|epoch_str| {
            epoch_str.parse::<i64>().ok().and_then(|epoch| {
                chrono::DateTime::from_timestamp(epoch, 0).map(|dt| dt.to_rfc3339())
            })
        })
        .flatten()
}

/// Build a PSPF/2025 package
pub fn build(manifest_path: &Path, output_path: &Path, options: BuildOptions) -> Result<()> {
    let _start_time = Instant::now();
    info!("🔨 Building PSPF/2025 package from: {manifest_path:?}");
    trace!("🔍 Build options: {:?}", options);

    // Read and parse manifest
    let manifest_timer = Instant::now();
    let manifest_data = fs::read_to_string(manifest_path)?;
    let manifest: BuildManifest = serde_json::from_str(&manifest_data)
        .map_err(|e| FlavorError::Generic(format!("Failed to parse manifest: {e}")))?;
    trace!("✅ Manifest parsed in {:?}", manifest_timer.elapsed());

    // Get launcher binary - required via CLI or env var
    let launcher_timer = Instant::now();
    let launcher_data = get_launcher(&options)?;
    let launcher_size = launcher_data.len() as u64;
    debug!(
        "🚀 Loaded launcher: {} bytes in {:?}",
        launcher_size,
        launcher_timer.elapsed()
    );

    // Create output file
    let mut out = File::create(output_path)?;
    trace!("📄 Created output file: {:?}", output_path);

    // Write launcher
    let write_timer = Instant::now();
    out.write_all(&launcher_data)?;
    trace!("✍️ Wrote launcher in {:?}", write_timer.elapsed());

    // Get or generate keys using the keys module
    let (signing_key, public_key) = load_or_generate_keys(&options)?;

    // Create index with new 4096-byte structure
    trace!("📦 Creating PSPF/2025 index structure");
    let mut index = Index::new();
    index.launcher_size = launcher_size;
    index.public_key.copy_from_slice(public_key.as_bytes());
    index.capabilities = CAPABILITY_MMAP | CAPABILITY_SIGNED;

    // Skip index block space
    let index_offset = launcher_size;
    let data_start = index_offset + HEADER_SIZE as u64;
    out.seek(SeekFrom::Start(data_start))?;
    debug!(
        "📍 Data section starts at {:#x} (after launcher {:#x} + index 512)",
        data_start, launcher_size
    );

    // Build metadata
    let (build_timestamp, build_host) = if let Ok(epoch) = std::env::var("SOURCE_DATE_EPOCH") {
        // Use SOURCE_DATE_EPOCH for reproducible timestamps
        let timestamp = if let Ok(secs) = epoch.parse::<i64>() {
            chrono::DateTime::from_timestamp(secs, 0)
                .map(|dt| dt.to_rfc3339())
                .unwrap_or_else(|| chrono::Utc::now().to_rfc3339())
        } else {
            chrono::Utc::now().to_rfc3339()
        };
        (
            timestamp,
            format!("{}/{}", std::env::consts::OS, std::env::consts::ARCH),
        )
    } else {
        let hostname = gethostname::gethostname().to_string_lossy().to_string();
        (
            chrono::Utc::now().to_rfc3339(),
            format!(
                "{}/{} {}",
                std::env::consts::OS,
                std::env::consts::ARCH,
                hostname
            ),
        )
    };

    // Calculate launcher checksum
    let launcher_checksum = calculate_checksum(launcher_data.as_slice(), ChecksumAlgorithm::Sha256)
        .map_err(|e| FlavorError::Generic(format!("Failed to calculate launcher checksum: {}", e)))?;

    let mut metadata = Metadata {
        format: "PSPF/2025".to_string(),
        format_version: Some("1.0.0".to_string()),
        package: PackageInfo {
            name: manifest.package.name.clone(),
            version: manifest.package.version.clone(),
        },
        slots: vec![],
        execution: ExecutionInfo {
            primary_slot: 0,
            command: manifest.execution.command.clone(),
            env: manifest.execution.env.clone(),
        },
        verification: Some(VerificationInfo {
            integrity_seal: IntegritySealInfo {
                required: true,
                algorithm: "ed25519".to_string(),
            },
            signed: true,
            require_verification: true,
            trust_signatures: None,
        }),
        build: Some(BuildInfo {
            tool: "flavor-rs".to_string(),
            tool_version: env!("FLAVOR_VERSION").to_string(),
            timestamp: build_timestamp.clone(),
            deterministic: options.key_seed.is_some(),
            platform: PlatformInfo {
                os: std::env::consts::OS.to_string(),
                arch: std::env::consts::ARCH.to_string(),
                host: build_host.clone(),
            },
        }),
        launcher: Some(LauncherInfo {
            tool: options.launcher_bin.as_ref()
                .and_then(|p| p.file_name())
                .and_then(|n| n.to_str())
                .map(|s| s.to_string())
                .or_else(|| std::env::var("FLAVOR_LAUNCHER_BIN").ok()
                    .and_then(|s| PathBuf::from(s).file_name()
                        .and_then(|n| n.to_str())
                        .map(|s| s.to_string())))
                .unwrap_or_else(|| "unknown".to_string()),
            tool_version: "1.0.0".to_string(), // TODO: Get actual version
            size: launcher_size as i64,
            checksum: launcher_checksum,
            capabilities: vec!["mmap".to_string(), "signed".to_string()],
        }),
        compatibility: Some(CompatibilityInfo {
            min_format_version: "1.0.0".to_string(),
            features: vec![],
        }),
        cache_validation: manifest
            .cache_validation
            .as_ref()
            .and_then(|v| serde_json::from_value::<CacheValidationInfo>(v.clone()).ok()),
        runtime: manifest
            .runtime
            .as_ref()
            .and_then(|v| serde_json::from_value::<RuntimeInfo>(v.clone()).ok()),
        workenv: manifest
            .workenv
            .as_ref()
            .and_then(|v| serde_json::from_value::<WorkenvInfo>(v.clone()).ok()),
        setup_commands: manifest.setup_commands.clone()
    };

    // Process slots (read only, don't write yet)
    let slots_timer = Instant::now();
    let mut slot_descriptors = Vec::new();
    let mut metadata_slots = Vec::new();
    let mut slot_paths = Vec::new(); // Store paths for streaming later

    debug!("🎰 Processing {} slots", manifest.slots.len());
    for (i, slot) in manifest.slots.iter().enumerate() {
        let _slot_timer = Instant::now();
        // Validate slot number if provided - critical error on mismatch
        if let Some(declared_slot) = slot.slot {
            if declared_slot as usize != i {
                error!(
                    "❌ Critical: Slot number mismatch - expected {}, declared {} for slot '{}'",
                    i, declared_slot, slot.id
                );
                std::process::exit(1);
            }
        }
        // Process slot metadata without loading data into memory
        trace!("📖 Processing slot {}: {}", i, slot.source);

        // Resolve {workenv} to base directory (FLAVOR_WORKENV_BASE or CWD)
        let slot_path = if slot.source.contains("{workenv}") {
            // Priority: 1. FLAVOR_WORKENV_BASE env var, 2. Current working directory
            let base_dir = if let Ok(env_base) = std::env::var("FLAVOR_WORKENV_BASE") {
                info!("🔍 Using FLAVOR_WORKENV_BASE: {}", env_base);
                PathBuf::from(env_base)
            } else {
                let cwd = std::env::current_dir().map_err(|e| {
                    FlavorError::Generic(format!("Failed to get current directory: {}", e))
                })?;
                info!("🔍 No FLAVOR_WORKENV_BASE, using CWD: {}", cwd.display());
                cwd
            };
            let resolved = slot
                .source
                .replace("{workenv}", base_dir.to_str().unwrap_or("."));
            info!(
                "📍 Resolved slot path: {} -> {} (base: {})",
                slot.source,
                resolved,
                base_dir.display()
            );
            PathBuf::from(resolved)
        } else {
            info!("📍 Slot path has no {{workenv}}: {}", slot.source);
            PathBuf::from(&slot.source)
        };

        // Open file and calculate size + checksums in streaming fashion
        info!("Attempting to open slot file at: {:?}", slot_path);
        let slot_file = File::open(&slot_path).map_err(|e| {
            FlavorError::Generic(format!("Failed to open slot {} (resolved to {:?}): {}", slot.source, slot_path, e))
        })?;
        
        let file_metadata = slot_file.metadata()?;
        let file_size = file_metadata.len();
        trace!("📊 Slot {} size: {} bytes", i, file_size);
        
        // Calculate checksums using streaming
        let checksum_timer = Instant::now();
        let mut reader = BufReader::with_capacity(8 * 1024 * 1024, slot_file);
        let checksum = calculate_checksum(&mut reader, ChecksumAlgorithm::Sha256).map_err(|e| {
            FlavorError::Generic(format!("Failed to calculate checksum for slot {}: {}", i, e))
        })?;
        
        // Calculate Adler-32 by re-reading (we need both checksums)
        let slot_file2 = File::open(&slot_path)?;
        let mut reader2 = BufReader::with_capacity(8 * 1024 * 1024, slot_file2);
        let mut adler = adler::Adler32::new();
        let mut buffer = vec![0u8; 8 * 1024 * 1024];
        loop {
            let bytes_read = reader2.read(&mut buffer).map_err(|e| {
                FlavorError::Generic(format!("Failed to read slot {} for Adler32: {}", i, e))
            })?;
            if bytes_read == 0 {
                break;
            }
            adler.write_slice(&buffer[..bytes_read]);
        }
        let adler_checksum = adler.checksum();
        
        trace!("☑️ Checksums calculated in {:?}", checksum_timer.elapsed());
        info!("Slot {}: SHA256 checksum: {}", i, checksum);
        info!("Slot {}: Adler32 checksum: {:08x}", i, adler_checksum);

        // Create metadata entry
        let slot_meta = SlotMetadata {
            index: i,
            id: slot.id.clone(),
            source: slot.source.clone(),
            target: slot.target.clone(),
            size: file_size as i64,
            checksum,
            encoding: slot.encoding.clone(),
            purpose: slot.purpose.clone(),
            lifecycle: slot.lifecycle.clone(),
            permissions: slot.permissions.clone().or_else(|| Some(format!("{:04o}", super::constants::DEFAULT_FILE_PERMS))),
            resolution: slot.resolution.clone().or_else(|| Some("build".to_string())),
        };
        metadata_slots.push(slot_meta);

        // Store path for later streaming (instead of data)
        slot_paths.push(slot_path);

        // Map string values to bytes per PSPF spec constants
        let encoding_value = match slot.encoding.as_str() {
            "gzip" => ENCODING_GZIP,     // 2 = single gzipped file
            "tgz" => ENCODING_TGZ,       // 3 = tar.gz
            "tar" => ENCODING_TAR,       // 1 = uncompressed tar
            "none" | "" => ENCODING_RAW, // 0 = raw uncompressed
            _ => ENCODING_RAW,
        };

        let purpose_value = match slot.purpose.as_str() {
            "payload" => 0,
            "runtime" => 1,
            "tool" => 2,
            _ => 0,
        };

        let lifecycle_value = match slot.lifecycle.as_str() {
            // Timing-based
            "init" => 0,
            "startup" => 1,
            "runtime" => 2,
            "shutdown" => 3,
            // Retention-based
            "cache" => 4,
            "temp" => 5,
            // Access-based
            "lazy" => 6,
            "eager" => 7,
            // Environment-based
            "dev" => 8,
            "config" => 9,
            "platform" => 10,
            _ => 2, // default to runtime
        };

        // Create proper 64-byte SlotDescriptor (offset will be set later)
        let mut descriptor = SlotDescriptor::new(i as u64);
        descriptor = descriptor.with_name(&slot.id);
        descriptor.size = file_size;
        descriptor.original_size = file_size; // TODO: Track original size if compressed
        descriptor.checksum = adler_checksum;
        descriptor.encoding = encoding_value;
        descriptor.purpose = purpose_value;
        descriptor.lifecycle = lifecycle_value;

        // Parse permissions from metadata or use default
        descriptor.permissions = if let Some(ref perm_str) = slot.permissions {
            // Parse octal string (e.g., "0755" -> 0o755)
            u16::from_str_radix(perm_str.trim_start_matches('0'), 8).unwrap_or(DEFAULT_FILE_PERMS)
        } else {
            DEFAULT_FILE_PERMS // Default: read/write for owner only
        };

        descriptor.alignment = SLOT_ALIGNMENT as u16;

        slot_descriptors.push(descriptor);

        trace!(
            "📍 Slot {}: {} size {} bytes, checksum {:08x}",
            i,
            slot.id,
            file_size,
            adler_checksum
        );
    }

    debug!(
        "✅ Processed {} slots in {:?}",
        manifest.slots.len(),
        slots_timer.elapsed()
    );

    // Update metadata with slots
    metadata.slots = metadata_slots;

    // Step 1: Write metadata FIRST (before slots and descriptors)

    // Create compressed JSON metadata
    let metadata_json = serde_json::to_vec_pretty(&metadata)?;

    // Sign the metadata
    let signature: Signature = signing_key.sign(&metadata_json);
    // Ed25519 signatures are 64 bytes, copy to the beginning of the 512-byte field
    index.integrity_signature[..64].copy_from_slice(signature.to_bytes().as_ref());

    // Compress the JSON with gzip
    let mut compressed = Vec::new();
    {
        use flate2::write::GzEncoder;
        use flate2::Compression;
        use std::io::Write;

        let mut encoder = GzEncoder::new(&mut compressed, Compression::default());
        encoder.write_all(&metadata_json)?;
        encoder.finish()?;
    }

    // Calculate metadata checksum (Adler-32)
    let metadata_checksum = adler::adler32_slice(&compressed);
    // Convert u32 checksum to 32-byte array (padded with zeros)
    let mut checksum_bytes = [0u8; 32];
    checksum_bytes[0..4].copy_from_slice(&metadata_checksum.to_le_bytes());
    index.metadata_checksum = checksum_bytes;

    // Write compressed metadata at current position
    let metadata_pos = out.stream_position()?;
    eprintln!("📝 Writing metadata at position {:#x}", metadata_pos);
    out.write_all(&compressed)?;
    let metadata_end = out.stream_position()?;
    index.metadata_offset = metadata_pos;
    index.metadata_size = compressed.len() as u64;
    eprintln!(
        "📝 Wrote metadata: start={:#x}, size={}, end={:#x}",
        metadata_pos,
        compressed.len(),
        metadata_end
    );

    // Verify position math
    assert_eq!(
        metadata_end,
        metadata_pos + compressed.len() as u64,
        "Metadata end position mismatch!"
    );

    // Step 2: Calculate and reserve space for descriptor table
    let current_pos = out.stream_position()?;
    eprintln!("📍 Current position after metadata: {:#x}", current_pos);
    let descriptor_table_offset = align_offset(current_pos, SLOT_ALIGNMENT);
    eprintln!(
        "📍 Aligned descriptor table offset: {:#x} (aligned from {:#x})",
        descriptor_table_offset, current_pos
    );
    index.slot_table_offset = descriptor_table_offset;
    index.slot_table_size = (slot_descriptors.len() * SLOT_DESCRIPTOR_SIZE) as u64;
    index.slot_count = slot_descriptors.len() as u32;
    info!(
        "🔍 Setting descriptor_offset to {:#x} for {} descriptors",
        descriptor_table_offset,
        slot_descriptors.len()
    );

    // Reserve space for descriptors
    let descriptor_table_size = (slot_descriptors.len() * SLOT_DESCRIPTOR_SIZE) as u64;
    out.seek(SeekFrom::Start(
        descriptor_table_offset + descriptor_table_size,
    ))?;
    debug!(
        "📊 Reserved {} bytes for {} descriptors at offset {:#x}",
        descriptor_table_size,
        slot_descriptors.len(),
        descriptor_table_offset
    );

    // Step 3: Stream slot data directly from files and update descriptor offsets
    for (i, (descriptor, slot_path)) in slot_descriptors.iter_mut().zip(&slot_paths).enumerate()
    {
        // Align position
        let current = out.stream_position()?;
        let aligned = align_offset(current, SLOT_ALIGNMENT);
        if aligned > current {
            out.write_all(&vec![0u8; (aligned - current) as usize])?;
        }

        // Write slot and update descriptor with actual offset
        let slot_offset = out.stream_position()?;
        descriptor.offset = slot_offset;
        
        // Stream file directly to output
        let mut slot_file = File::open(slot_path)?;
        let bytes_copied = io::copy(&mut slot_file, &mut out)?;

        debug!(
            "📍 Wrote slot {}: offset={:#x}, size={} bytes",
            i,
            slot_offset,
            bytes_copied
        );
    }

    // Step 4: Go back and write descriptor table at reserved location
    let end_pos = out.stream_position()?;
    out.seek(SeekFrom::Start(descriptor_table_offset))?;

    for (i, descriptor) in slot_descriptors.iter().enumerate() {
        let descriptor_bytes = descriptor.to_bytes();
        out.write_all(&descriptor_bytes)?;
        trace!("✍️ Wrote 64-byte descriptor for slot {}", i);
    }
    debug!(
        "📋 Wrote {} descriptors at offset {:#x}",
        slot_descriptors.len(),
        descriptor_table_offset
    );

    // Step 5: Return to end of data and write trailing magic
    out.seek(SeekFrom::Start(end_pos))?;

    // Write trailing magic (emoji bytes, XOR decoded)
    out.write_all(&*TRAILING_MAGIC)?;

    // Update package size
    let final_pos = out.stream_position()?;
    index.package_size = final_pos;

    // Write index with checksum
    out.seek(SeekFrom::Start(index_offset))?;
    write_index(&mut out, &mut index)?;

    // Make the output file executable
    #[cfg(unix)]
    {
        use std::os::unix::fs::PermissionsExt;
        let mut perms = fs::metadata(output_path)?.permissions();
        perms.set_mode(super::constants::DEFAULT_DIR_PERMS as u32);
        fs::set_permissions(output_path, perms)?;
    }

    log::info!("✅ Successfully built PSPF bundle: {output_path:?}");
    log::info!("  Package: {} v{}", manifest.package.name, manifest.package.version);
    let launcher_display = options.launcher_bin.as_ref()
        .map(|p| p.display().to_string())
        .or_else(|| std::env::var("FLAVOR_LAUNCHER_BIN").ok())
        .unwrap_or_else(|| "unknown".to_string());
    log::info!("  Launcher: {}", launcher_display);
    log::info!("  Slots: {}", manifest.slots.len());
    log::info!("  Size: {final_pos} bytes");

    Ok(())
}

fn get_launcher(options: &BuildOptions) -> Result<Vec<u8>> {
    // Priority order:
    // 1. Explicit launcher_bin from options
    // 2. FLAVOR_LAUNCHER_BIN environment variable
    // No fallback - launcher must be explicitly specified

    let launcher_path = if let Some(ref explicit_path) = options.launcher_bin {
        explicit_path.clone()
    } else if let Ok(explicit_path) = std::env::var("FLAVOR_LAUNCHER_BIN") {
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
            warn!("⚠️ Failed to get launcher version: {}", e);
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

fn write_index(out: &mut File, index: &mut Index) -> Result<()> {
    // Calculate checksum with placeholder set to 0
    let mut bytes = index.to_bytes();
    bytes[12..16].copy_from_slice(&[0, 0, 0, 0]);
    let checksum = adler::adler32_slice(&bytes);
    
    // Update the index structure with the calculated checksum
    index.index_checksum = checksum;
    
    // Get the bytes again with the updated checksum
    let final_bytes = index.to_bytes();
    
    out.write_all(&final_bytes)?;
    Ok(())
}
