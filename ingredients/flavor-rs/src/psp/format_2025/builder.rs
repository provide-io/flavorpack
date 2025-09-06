//! PSPF/2025 package builder

use super::checksums::{calculate_checksum, ChecksumAlgorithm};
use super::{
    constants::{CAPABILITY_MMAP, CAPABILITY_SIGNED, HEADER_SIZE, ENCODING_GZIP, ENCODING_TGZ, ENCODING_TAR, ENCODING_RAW, DEFAULT_FILE_PERMS, SLOT_ALIGNMENT, SLOT_DESCRIPTOR_SIZE, MAGIC_TRAILER_SIZE, PACKAGE_EMOJI_BYTES, MAGIC_WAND_EMOJI_BYTES, DEFAULT_DIR_PERMS},
    index::Index,
    keys::load_or_generate_keys,
    manifest::{BuildManifest, ManifestSlot},
    metadata::{Metadata, PackageInfo, ExecutionInfo, VerificationInfo, IntegritySealInfo, BuildInfo, PlatformInfo, LauncherInfo, CompatibilityInfo, CacheValidationInfo, RuntimeInfo, WorkenvInfo, SlotMetadata},
    slots::{align_offset, SlotDescriptor},
};
use crate::api::BuildOptions;
use crate::exceptions::{FlavorError, Result};
use ed25519_dalek::{Signature, Signer};
use log::{debug, error, info, trace};
use std::fs::{self, File};
use std::io::{self, BufReader, Read, Seek, SeekFrom, Write};
use std::path::{Path, PathBuf};
use std::time::Instant;

/// Build a PSPF/2025 package
pub fn build(manifest_path: &Path, output_path: &Path, options: BuildOptions) -> Result<()> {
    let _start_time = Instant::now();
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
    let descriptor_table_offset = reserve_descriptor_space(
        &mut out, 
        &slot_processor.slot_descriptors, 
        &mut index
    )?;
    
    // Phase 6: Write slot data and update descriptors
    let mut slot_descriptors = slot_processor.slot_descriptors;
    stream_slot_data(&mut out, &mut slot_descriptors, &slot_processor.slot_paths)?;
    
    // Phase 7: Write descriptor table at reserved location
    let end_pos = write_descriptor_table(&mut out, &slot_descriptors, descriptor_table_offset)?;
    
    // Phase 8: Finalize package with MagicTrailer
    finalize_package(&mut out, &mut index, end_pos, output_path, &manifest, &options)?;
    
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
    let launcher_size = launcher_data.len() as u64;
    debug!(
        "🚀 Loaded launcher: {} bytes in {:?}",
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
    index.capabilities = CAPABILITY_MMAP | CAPABILITY_SIGNED;
    
    index
}

/// Get build timestamp and host information
fn get_build_info() -> (String, String) {
    if let Ok(epoch) = std::env::var("SOURCE_DATE_EPOCH") {
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
    }
}

/// Create the package metadata structure
fn create_metadata(
    manifest: &BuildManifest,
    launcher_size: u64,
    launcher_data: &[u8],
    options: &BuildOptions,
) -> Result<Metadata> {
    let (build_timestamp, build_host) = get_build_info();
    
    // Calculate launcher checksum
    let launcher_checksum = calculate_checksum(launcher_data, ChecksumAlgorithm::Sha256)
        .map_err(|e| FlavorError::Generic(format!("Failed to calculate launcher checksum: {}", e)))?;

    Ok(Metadata {
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
            timestamp: build_timestamp,
            deterministic: options.key_seed.is_some(),
            platform: PlatformInfo {
                os: std::env::consts::OS.to_string(),
                arch: std::env::consts::ARCH.to_string(),
                host: build_host,
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
            tool_version: env!("CARGO_PKG_VERSION").to_string(),
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
        setup_commands: manifest.setup_commands.clone(),
    })
}

/// Process and validate slot data
struct SlotProcessor {
    manifest_slots: Vec<ManifestSlot>,
    slot_descriptors: Vec<SlotDescriptor>,
    metadata_slots: Vec<SlotMetadata>,
    slot_paths: Vec<PathBuf>,
}

impl SlotProcessor {
    fn new(manifest_slots: Vec<ManifestSlot>) -> Self {
        Self {
            manifest_slots,
            slot_descriptors: Vec::new(),
            metadata_slots: Vec::new(),
            slot_paths: Vec::new(),
        }
    }

    fn process_slots(&mut self) -> Result<()> {
        debug!("🎰 Processing {} slots", self.manifest_slots.len());
        let slots_timer = Instant::now();
        
        // Process slots one by one
        let num_slots = self.manifest_slots.len();
        for i in 0..num_slots {
            // Work with index to avoid borrow checker issues
            let slot = &self.manifest_slots[i];
            
            trace!("📖 Processing slot {}: {}", i, slot.source);
            
            // Validate slot number if provided
            if let Some(declared_slot) = slot.slot {
                if declared_slot as usize != i {
                    error!(
                        "❌ Critical: Slot number mismatch - expected {}, declared {} for slot '{}'",
                        i, declared_slot, slot.id
                    );
                    std::process::exit(1);
                }
            }
            
            // Resolve slot path
            let slot_path = self.resolve_slot_path(&slot.source)?;
            
            // Calculate checksums and size
            let (file_size, sha256_checksum, adler32_checksum) = self.calculate_slot_checksums(&slot_path, i)?;
            
            // Create metadata entry
            let slot_meta = SlotMetadata {
                index: i,
                id: slot.id.clone(),
                source: slot.source.clone(),
                target: slot.target.clone(),
                size: file_size as i64,
                checksum: sha256_checksum,
                encoding: slot.encoding.clone(),
                purpose: slot.purpose.clone(),
                lifecycle: slot.lifecycle.clone(),
                permissions: slot.permissions.clone().or_else(|| Some(format!("{:04o}", DEFAULT_FILE_PERMS))),
                resolution: slot.resolution.clone().or_else(|| Some("build".to_string())),
            };
            self.metadata_slots.push(slot_meta);
            
            // Create descriptor
            let descriptor = self.create_slot_descriptor(i, slot, file_size, adler32_checksum)?;
            self.slot_descriptors.push(descriptor);
            
            // Store path for later streaming
            self.slot_paths.push(slot_path);
        }
        
        debug!(
            "✅ Processed {} slots in {:?}",
            self.manifest_slots.len(),
            slots_timer.elapsed()
        );
        Ok(())
    }

    fn resolve_slot_path(&self, source: &str) -> Result<PathBuf> {
        let slot_path = if source.contains("{workenv}") {
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
            let resolved = source.replace("{workenv}", base_dir.to_str().unwrap_or("."));
            info!(
                "📍 Resolved slot path: {} -> {} (base: {})",
                source,
                resolved,
                base_dir.display()
            );
            PathBuf::from(resolved)
        } else {
            info!("📍 Slot path has no {{workenv}}: {}", source);
            PathBuf::from(source)
        };
        
        info!("Attempting to open slot file at: {:?}", slot_path);
        Ok(slot_path)
    }

    fn calculate_slot_checksums(&self, slot_path: &Path, index: usize) -> Result<(u64, String, u32)> {
        let slot_file = File::open(slot_path).map_err(|e| {
            FlavorError::Generic(format!("Failed to open slot {}: {}", slot_path.display(), e))
        })?;
        
        let file_metadata = slot_file.metadata()?;
        let file_size = file_metadata.len();
        trace!("📊 Slot {} size: {} bytes", index, file_size);
        
        // Calculate SHA-256 checksum
        let checksum_timer = Instant::now();
        let mut reader = BufReader::with_capacity(8 * 1024 * 1024, slot_file);
        let sha256_checksum = calculate_checksum(&mut reader, ChecksumAlgorithm::Sha256).map_err(|e| {
            FlavorError::Generic(format!("Failed to calculate SHA256 for slot {}: {}", index, e))
        })?;
        
        // Calculate Adler-32 checksum
        let slot_file2 = File::open(slot_path)?;
        let mut reader2 = BufReader::with_capacity(8 * 1024 * 1024, slot_file2);
        let mut adler = adler::Adler32::new();
        let mut buffer = vec![0u8; 8 * 1024 * 1024];
        loop {
            let bytes_read = reader2.read(&mut buffer).map_err(|e| {
                FlavorError::Generic(format!("Failed to read slot {} for Adler32: {}", index, e))
            })?;
            if bytes_read == 0 {
                break;
            }
            adler.write_slice(&buffer[..bytes_read]);
        }
        let adler32_checksum = adler.checksum();
        
        trace!("☑️ Checksums calculated in {:?}", checksum_timer.elapsed());
        info!("Slot {}: SHA256 checksum: {}", index, sha256_checksum);
        info!("Slot {}: Adler32 checksum: {:08x}", index, adler32_checksum);
        
        Ok((file_size, sha256_checksum, adler32_checksum))
    }

    fn create_slot_descriptor(&self, index: usize, slot: &ManifestSlot, file_size: u64, adler_checksum: u32) -> Result<SlotDescriptor> {
        // Map encoding string to byte value
        let encoding_value = match slot.encoding.as_str() {
            "gzip" => ENCODING_GZIP,
            "tgz" => ENCODING_TGZ,
            "tar" => ENCODING_TAR,
            "raw" | "none" | "" => ENCODING_RAW,
            _ => ENCODING_RAW,
        };

        // Map purpose string to byte value
        let purpose_value = match slot.purpose.as_str() {
            "payload" => 0,
            "runtime" => 1,
            "tool" => 2,
            _ => 0,
        };

        // Map lifecycle string to byte value
        let lifecycle_value = match slot.lifecycle.as_str() {
            "init" => 0,
            "startup" => 1,
            "runtime" => 2,
            "shutdown" => 3,
            "cache" => 4,
            "temp" => 5,
            "lazy" => 6,
            "eager" => 7,
            "dev" => 8,
            "config" => 9,
            "platform" => 10,
            _ => 2,
        };

        // Create descriptor
        let mut descriptor = SlotDescriptor::new(index as u64);
        descriptor = descriptor.with_name(&slot.id);
        descriptor.size = file_size;
        descriptor.original_size = file_size;
        descriptor.checksum = adler_checksum;
        descriptor.encoding = encoding_value;
        descriptor.purpose = purpose_value;
        descriptor.lifecycle = lifecycle_value;
        
        // Parse permissions
        descriptor.permissions = if let Some(ref perm_str) = slot.permissions {
            u16::from_str_radix(perm_str.trim_start_matches('0'), 8).unwrap_or(DEFAULT_FILE_PERMS)
        } else {
            DEFAULT_FILE_PERMS
        };
        
        descriptor.alignment = SLOT_ALIGNMENT as u16;
        
        trace!(
            "📍 Slot {}: {} size {} bytes, checksum {:08x}",
            index,
            slot.id,
            file_size,
            adler_checksum
        );
        
        Ok(descriptor)
    }
}

/// Compress and sign metadata
fn compress_and_sign_metadata(
    metadata: &Metadata,
    signing_key: &ed25519_dalek::SigningKey,
    index: &mut Index,
) -> Result<Vec<u8>> {
    trace!("📝 Creating and signing metadata");
    
    // Create JSON
    let metadata_json = serde_json::to_vec_pretty(metadata)?;
    
    // Sign the metadata
    let signature: Signature = signing_key.sign(&metadata_json);
    index.integrity_signature[..64].copy_from_slice(signature.to_bytes().as_ref());
    
    // Compress with gzip
    let mut compressed = Vec::new();
    {
        use flate2::write::GzEncoder;
        use flate2::Compression;
        
        let mut encoder = GzEncoder::new(&mut compressed, Compression::default());
        encoder.write_all(&metadata_json)?;
        encoder.finish()?;
    }
    
    // Calculate checksum
    let metadata_checksum = adler::adler32_slice(&compressed);
    let mut checksum_bytes = [0u8; 32];
    checksum_bytes[0..4].copy_from_slice(&metadata_checksum.to_le_bytes());
    index.metadata_checksum = checksum_bytes;
    
    Ok(compressed)
}

/// Write metadata to output file
fn write_metadata_bytes(out: &mut File, compressed: &[u8], index: &mut Index) -> Result<()> {
    let metadata_pos = out.stream_position()?;
    debug!("📝 Writing metadata at position {:#x}", metadata_pos);
    
    out.write_all(compressed)?;
    let metadata_end = out.stream_position()?;
    
    index.metadata_offset = metadata_pos;
    index.metadata_size = compressed.len() as u64;
    
    debug!(
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
    
    Ok(())
}

/// Reserve space for descriptor table
fn reserve_descriptor_space(
    out: &mut File,
    descriptors: &[SlotDescriptor],
    index: &mut Index,
) -> Result<u64> {
    let current_pos = out.stream_position()?;
    debug!("📍 Current position after metadata: {:#x}", current_pos);
    
    let descriptor_table_offset = align_offset(current_pos, SLOT_ALIGNMENT);
    debug!(
        "📍 Aligned descriptor table offset: {:#x} (aligned from {:#x})",
        descriptor_table_offset, current_pos
    );
    
    index.slot_table_offset = descriptor_table_offset;
    index.slot_table_size = (descriptors.len() * SLOT_DESCRIPTOR_SIZE) as u64;
    index.slot_count = descriptors.len() as u32;
    
    info!(
        "🔍 Setting descriptor_offset to {:#x} for {} descriptors",
        descriptor_table_offset,
        descriptors.len()
    );
    
    // Reserve space
    let descriptor_table_size = (descriptors.len() * SLOT_DESCRIPTOR_SIZE) as u64;
    out.seek(SeekFrom::Start(
        descriptor_table_offset + descriptor_table_size,
    ))?;
    
    debug!(
        "📊 Reserved {} bytes for {} descriptors at offset {:#x}",
        descriptor_table_size,
        descriptors.len(),
        descriptor_table_offset
    );
    
    Ok(descriptor_table_offset)
}

/// Stream slot data from files to output
fn stream_slot_data(
    out: &mut File,
    descriptors: &mut [SlotDescriptor],
    slot_paths: &[PathBuf],
) -> Result<()> {
    trace!("📦 Streaming slot data to output");
    
    for (i, (descriptor, slot_path)) in descriptors.iter_mut().zip(slot_paths).enumerate() {
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
        let bytes_copied = io::copy(&mut slot_file, out)?;
        
        debug!(
            "📍 Wrote slot {}: offset={:#x}, size={} bytes",
            i,
            slot_offset,
            bytes_copied
        );
    }
    
    Ok(())
}

/// Write descriptor table at reserved location
fn write_descriptor_table(
    out: &mut File,
    descriptors: &[SlotDescriptor],
    descriptor_table_offset: u64,
) -> Result<u64> {
    let end_pos = out.stream_position()?;
    out.seek(SeekFrom::Start(descriptor_table_offset))?;
    
    for (i, descriptor) in descriptors.iter().enumerate() {
        let descriptor_bytes = descriptor.pack();
        out.write_all(&descriptor_bytes)?;
        trace!("✍️ Wrote 64-byte descriptor for slot {}", i);
    }
    
    debug!(
        "📋 Wrote {} descriptors at offset {:#x}",
        descriptors.len(),
        descriptor_table_offset
    );
    
    // Return to end of data
    out.seek(SeekFrom::Start(end_pos))?;
    Ok(end_pos)
}

/// Finalize package with MagicTrailer and make executable
fn finalize_package(
    out: &mut File,
    index: &mut Index,
    end_pos: u64,
    output_path: &Path,
    manifest: &BuildManifest,
    options: &BuildOptions,
) -> Result<()> {
    trace!("🎬 Finalizing package with MagicTrailer");
    
    // Update package size before writing MagicTrailer
    index.package_size = end_pos + MAGIC_TRAILER_SIZE as u64;
    
    // Write MagicTrailer (8200 bytes: 📦 + index + 🪄)
    out.write_all(PACKAGE_EMOJI_BYTES)?;
    write_index(out, index)?;
    out.write_all(MAGIC_WAND_EMOJI_BYTES)?;
    
    // Make the output file executable
    #[cfg(unix)]
    {
        use std::os::unix::fs::PermissionsExt;
        let mut perms = fs::metadata(output_path)?.permissions();
        perms.set_mode(DEFAULT_DIR_PERMS as u32);
        fs::set_permissions(output_path, perms)?;
    }
    
    // Log success message
    log::info!("✅ Successfully built PSPF bundle: {output_path:?}");
    log::info!("  Package: {} v{}", manifest.package.name, manifest.package.version);
    let launcher_display = options.launcher_bin.as_ref()
        .map(|p| p.display().to_string())
        .or_else(|| std::env::var("FLAVOR_LAUNCHER_BIN").ok())
        .unwrap_or_else(|| "unknown".to_string());
    log::info!("  Launcher: {}", launcher_display);
    log::info!("  Slots: {}", manifest.slots.len());
    let package_size = index.package_size;
    log::info!("  Size: {} bytes", package_size);
    
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

fn write_index(out: &mut File, index: &mut Index) -> Result<()> {
    // Calculate checksum with placeholder set to 0
    let mut bytes = index.pack();
    bytes[4..8].copy_from_slice(&[0, 0, 0, 0]);
    let checksum = adler::adler32_slice(&bytes);
    
    // Update the index structure with the calculated checksum
    index.index_checksum = checksum;
    
    // Get the bytes again with the updated checksum
    let final_bytes = index.pack();
    
    out.write_all(&final_bytes)?;
    Ok(())
}