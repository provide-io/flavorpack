use clap::Parser;
use serde::{Deserialize, Serialize};
use std::fs::{self, File};
use std::io::{Seek, SeekFrom, Write};
use std::path::PathBuf;
use anyhow::{Context, Result};
use sha2::{Sha256, Digest};
use tar::Builder as TarBuilder;
use flate2::write::GzEncoder;
use flate2::Compression;
use rand::Rng;
use rand::rngs::OsRng;
use ed25519_dalek::{SigningKey, Signature, Signer};
use pem::{Pem, encode};

mod logging;

use flavor_common::{PSPFIndex, INDEX_SIZE, SLOT_ALIGNMENT, EMOJI_MAGIC_SIZE};

/// Build PSPF 2025 bundles
#[derive(Parser, Debug)]
#[command(author, version, about, long_about = None)]
struct Args {
    /// Path to manifest.json
    #[arg(short, long)]
    manifest: PathBuf,

    /// Output path for PSPF bundle
    #[arg(short, long)]
    output: PathBuf,

    /// Launcher type (go, rust)
    #[arg(short, long, default_value = "rust")]
    launcher: String,

    /// Enable reproducible builds (deterministic output)
    #[arg(long)]
    reproducible: bool,
}

#[derive(Debug, Serialize, Deserialize)]
struct BuildConfig {
    name: String,
    version: String,
    #[serde(default)]
    description: String,
    #[serde(default)]
    launcher: String,
    command: String,
    slots: Vec<Slot>,
    #[serde(default)]
    environment: std::collections::HashMap<String, String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    cache_validation: Option<serde_json::Value>,
    #[serde(skip_serializing_if = "Option::is_none")]
    runtime: Option<serde_json::Value>,
    #[serde(default)]
    setup_commands: Vec<serde_json::Value>,
}

#[derive(Debug, Serialize, Deserialize)]
struct Slot {
    path: String,
    name: String,
    #[serde(default)]
    encoding: String,
    purpose: String,
    lifecycle: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    extract_to: Option<String>,
}

#[derive(Debug, Serialize)]
struct Metadata {
    format: String,
    package: PackageInfo,
    slots: Vec<SlotMetadata>,
    execution: ExecutionInfo,
    verification: VerificationInfo,
    #[serde(skip_serializing_if = "Option::is_none")]
    build: Option<BuildInfo>,
    #[serde(skip_serializing_if = "Option::is_none")]
    cache_validation: Option<serde_json::Value>,
    #[serde(skip_serializing_if = "Option::is_none")]
    runtime: Option<serde_json::Value>,
    #[serde(default)]
    setup_commands: Vec<serde_json::Value>,
}

#[derive(Debug, Serialize)]
struct PackageInfo {
    name: String,
    version: String,
    description: String,
}

#[derive(Debug, Serialize)]
struct SlotMetadata {
    index: usize,
    name: String,
    size: i64,  // Size as stored in package
    checksum: String,
    encoding: String,  // Indicates compression type
    purpose: String,
    lifecycle: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    extract_to: Option<String>,  // Runtime extraction subdirectory
}

#[derive(Debug, Serialize)]
struct ExecutionInfo {
    primary_slot: usize,
    command: String,
    environment: std::collections::HashMap<String, String>,
}

#[derive(Debug, Serialize)]
struct VerificationInfo {
    integrity_seal: IntegritySealInfo,
}

#[derive(Debug, Serialize)]
struct IntegritySealInfo {
    required: bool,
    algorithm: String,
}

#[derive(Debug, Serialize)]
struct BuildInfo {
    builder: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    version: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    timestamp: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    host: Option<String>,
}


fn main() -> Result<()> {
    // Initialize logging with JSON support
    if let Err(e) = logging::init_logger() {
        eprintln!("Failed to initialize logger: {}", e);
        // Fall back to basic stderr logging
    }
    
    let args = Args::parse();

    // Read manifest
    let manifest_data = fs::read_to_string(&args.manifest)
        .with_context(|| format!("❌ Failed to read manifest: {:?}", args.manifest))?;
    
    let mut config: BuildConfig = serde_json::from_str(&manifest_data)
        .context("❌ Failed to parse manifest")?;

    // Override launcher if specified
    if config.launcher.is_empty() {
        config.launcher = args.launcher;
    }

    // Get launcher binary
    let launcher_path = get_launcher_path(&config.launcher);
    let launcher_data = fs::read(&launcher_path)
        .with_context(|| format!("❌ Failed to read launcher: {}", launcher_path))?;

    // Create output file
    let mut out = File::create(&args.output)
        .with_context(|| format!("❌ Failed to create output file: {:?}", args.output))?;

    // Write launcher
    out.write_all(&launcher_data)?;
    let launcher_size = launcher_data.len() as u64;

    // Create index
    let mut index = PSPFIndex {
        format_magic: [b'P', b'S', b'P', b'F', b'2', b'0', b'2', b'5'],
        format_version: 0x20250001,
        index_checksum: 0,
        package_size: 0,
        launcher_size,
        metadata_offset: 0,
        metadata_size: 0,
        slot_table_offset: 0,
        slot_table_size: 0,
        slot_count: 0,
        flags: 0,
        ephemeral_public_key: [0; 32],
        metadata_checksum: [0; 32],
        reserved: [0; 120],
    };

    // Generate ephemeral Ed25519 keys
    let signing_key = if args.reproducible {
        // Use deterministic seed for reproducible builds
        let seed = Sha256::digest(b"reproducible-build-seed");
        let seed_bytes: [u8; 32] = seed.into();
        SigningKey::from_bytes(&seed_bytes)
    } else {
        SigningKey::generate(&mut OsRng)
    };
    let public_key = signing_key.verifying_key();
    index.ephemeral_public_key[..32].copy_from_slice(public_key.as_bytes());

    // Skip index block space
    let index_offset = launcher_size;
    out.seek(SeekFrom::Start(index_offset + INDEX_SIZE))?;

    // Build metadata
    let (build_timestamp, build_host) = if args.reproducible {
        // Use fixed values for reproducible builds
        (
            "2025-01-01T00:00:00Z".to_string(),
            format!("{}/{} reproducible", std::env::consts::OS, std::env::consts::ARCH)
        )
    } else {
        let hostname = gethostname::gethostname()
            .to_string_lossy()
            .to_string();
        (
            chrono::Utc::now().to_rfc3339(),
            format!("{}/{} {}", std::env::consts::OS, std::env::consts::ARCH, hostname)
        )
    };
    
    let metadata = Metadata {
        format: "PSPF/2025".to_string(),
        package: PackageInfo {
            name: config.name.clone(),
            version: config.version.clone(),
            description: config.description.clone(),
        },
        slots: vec![],
        execution: ExecutionInfo {
            primary_slot: 0,
            command: config.command.clone(),
            environment: config.environment.clone(),
        },
        verification: VerificationInfo {
            integrity_seal: IntegritySealInfo {
                required: true,
                algorithm: "ecdsa-p256".to_string(),
            },
        },
        build: Some(BuildInfo {
            builder: "rust/pspf-builder".to_string(),
            version: Some("1.0.0".to_string()),
            timestamp: Some(build_timestamp),
            host: Some(build_host),
        }),
        cache_validation: config.cache_validation.clone(),
        runtime: config.runtime.clone(),
        setup_commands: config.setup_commands.clone(),
    };

    // Process slots
    let mut slot_offsets = Vec::new();
    let mut metadata_slots = Vec::new();

    for (i, slot) in config.slots.iter().enumerate() {
        // Read slot data
        let slot_data = fs::read(&slot.path)
            .with_context(|| format!("❌ Failed to read slot: {}", slot.path))?;

        // Calculate checksum
        let mut hasher = Sha256::new();
        hasher.update(&slot_data);
        let checksum = format!("{:x}", hasher.finalize());

        // The encoding field describes what format the data is already in
        // We don't need to compress it again - just use it as-is
        let compressed = slot_data.clone();

        let slot_meta = SlotMetadata {
            index: i,
            name: slot.name.clone(),
            size: compressed.len() as i64,  // Size as stored in the package
            checksum,
            encoding: slot.encoding.clone(),
            purpose: slot.purpose.clone(),
            lifecycle: slot.lifecycle.clone(),
            extract_to: slot.extract_to.clone(),
        };
        metadata_slots.push(slot_meta);

        // Align position
        let current_pos = out.stream_position()?;
        let aligned_pos = align_offset(current_pos, SLOT_ALIGNMENT);
        if aligned_pos > current_pos {
            let padding = vec![0u8; (aligned_pos - current_pos) as usize];
            out.write_all(&padding)?;
        }

        // Write slot
        let slot_offset = out.stream_position()?;
        out.write_all(&compressed)?;

        // Calculate adler32 checksum
        let adler_checksum = adler::adler32_slice(&compressed);

        // Map purpose string to uint8
        let purpose_value = match slot.purpose.as_str() {
            "payload" => 0,
            "runtime" => 1,
            "tool" => 2,
            _ => 0, // default to payload
        };

        // Map lifecycle string to uint8
        let lifecycle_value = match slot.lifecycle.as_str() {
            "persistent" => 0,
            "volatile" => 1,
            _ => 0, // default to persistent
        };

        // Map encoding string to uint8
        let encoding_value = match slot.encoding.as_str() {
            "gzip" => 1,
            "zstd" => 2,
            "none" | "" => 0,
            _ => 0, // default to none
        };

        slot_offsets.push(SlotEntry {
            offset: slot_offset,
            size: compressed.len() as u64,
            checksum: adler_checksum,
            encoding: encoding_value,
            purpose: purpose_value,
            lifecycle: lifecycle_value,
            reserved: 0,
        });
    }

    // Update metadata with slots
    let mut metadata = metadata;
    metadata.slots = metadata_slots;

    // Write slot table
    let current_pos = out.stream_position()?;
    let slot_table_offset = align_offset(current_pos, SLOT_ALIGNMENT);
    out.seek(SeekFrom::Start(slot_table_offset))?;

    index.slot_table_offset = slot_table_offset;
    index.slot_count = slot_offsets.len() as u32;

    for entry in &slot_offsets {
        out.write_all(&entry.offset.to_le_bytes())?;
        out.write_all(&entry.size.to_le_bytes())?;
        out.write_all(&entry.checksum.to_le_bytes())?;
        out.write_all(&entry.encoding.to_le_bytes())?;
        out.write_all(&entry.purpose.to_le_bytes())?;
        out.write_all(&entry.lifecycle.to_le_bytes())?;
        out.write_all(&entry.reserved.to_le_bytes())?;
    }
    // Each slot entry is 8+8+4+1+1+1+1 = 24 bytes
    index.slot_table_size = (slot_offsets.len() * 24) as u64;

    // Create metadata archive in memory first to calculate checksum
    let metadata_archive = create_metadata_archive(&metadata, &signing_key)?;
    
    // Calculate metadata checksum
    let mut hasher = Sha256::new();
    hasher.update(&metadata_archive);
    let metadata_checksum = hasher.finalize();
    index.metadata_checksum.copy_from_slice(&metadata_checksum);
    
    // Write metadata archive
    let metadata_pos = out.stream_position()?;
    out.write_all(&metadata_archive)?;
    
    index.metadata_offset = metadata_pos;
    index.metadata_size = metadata_archive.len() as u64;

    // Write emoji magic
    let emoji_magic = generate_emoji_magic(&config.launcher);
    out.write_all(&emoji_magic)?;

    // Update package size
    let final_pos = out.stream_position()?;
    index.package_size = final_pos;

    // Write index
    out.seek(SeekFrom::Start(index_offset))?;
    write_index(&mut out, &index)?;

    // Standard output for success messages (builder convention)
    println!("✅ Successfully built PSPF bundle: {:?}", args.output);
    println!("  Package: {} v{}", config.name, config.version);
    println!("  Launcher: {}", config.launcher);
    println!("  Slots: {}", config.slots.len());
    println!("  Size: {} bytes", final_pos);

    Ok(())
}

struct SlotEntry {
    offset: u64,      // 8 bytes: where slot data starts
    size: u64,        // 8 bytes: size of data as stored
    checksum: u32,    // 4 bytes: adler32 of stored data
    encoding: u8,  // 1 byte: 0=none, 1=gzip, 2=zstd, etc
    purpose: u8,      // 1 byte: 0=payload, 1=runtime, 2=tool
    lifecycle: u8,    // 1 byte: 0=persistent, 1=volatile
    reserved: u8,     // 1 byte: padding for alignment
}

fn get_launcher_path(launcher_type: &str) -> String {
    match launcher_type {
        "go" => "flavor-go-launcher".to_string(),
        "rust" => "flavor-rs-launcher".to_string(),
        _ => "flavor-rs-launcher".to_string(),  // Default to Rust launcher
    }
}

fn align_offset(offset: u64, alignment: u64) -> u64 {
    (offset + alignment - 1) & !(alignment - 1)
}

fn create_metadata_archive(metadata: &Metadata, signing_key: &SigningKey) -> Result<Vec<u8>> {
    let mut buffer = Vec::new();
    
    {
        let encoder = GzEncoder::new(&mut buffer, Compression::default());
        let mut tar = TarBuilder::new(encoder);

        // Write psp.json
        let metadata_json = serde_json::to_vec_pretty(metadata)?;
        let mut header = tar::Header::new_gnu();
        header.set_path("psp.json")?;
        header.set_size(metadata_json.len() as u64);
        header.set_mode(0o644);
        header.set_cksum();
        tar.append(&header, &metadata_json[..])?;

        // Sign the metadata with Ed25519
        let signature: Signature = signing_key.sign(&metadata_json);
        let mut seal_header = tar::Header::new_gnu();
        seal_header.set_path("integrity/seal.sig")?;
        seal_header.set_size(signature.to_bytes().len() as u64);
        seal_header.set_mode(0o644);
        seal_header.set_cksum();
        tar.append(&seal_header, signature.to_bytes().as_ref())?;

        // Write public key in PEM format
        let public_key_bytes = signing_key.verifying_key().to_bytes();
        let pem = Pem::new("PUBLIC KEY", public_key_bytes);
        let pem_string = encode(&pem);
        let mut key_header = tar::Header::new_gnu();
        key_header.set_path("integrity/seal.pem")?;
        key_header.set_size(pem_string.len() as u64);
        key_header.set_mode(0o644);
        key_header.set_cksum();
        tar.append(&key_header, pem_string.as_bytes())?;

        tar.finish()?;
    }

    Ok(buffer)
}

fn generate_emoji_magic(launcher_type: &str) -> Vec<u8> {
    // Just the magic wand emoji (4 bytes)
    let magic_wand = "🪄";
    magic_wand.as_bytes().to_vec()
}

fn write_index(out: &mut File, index: &PSPFIndex) -> Result<()> {
    // Create buffer
    let mut buf = vec![0u8; INDEX_SIZE as usize];
    
    // Pack fields in the same order as Go
    buf[0..8].copy_from_slice(&index.format_magic);
    buf[8..12].copy_from_slice(&index.format_version.to_le_bytes());
    buf[12..16].copy_from_slice(&[0, 0, 0, 0]); // Checksum placeholder
    buf[16..24].copy_from_slice(&index.package_size.to_le_bytes());
    buf[24..32].copy_from_slice(&index.launcher_size.to_le_bytes());
    buf[32..40].copy_from_slice(&index.metadata_offset.to_le_bytes());
    buf[40..48].copy_from_slice(&index.metadata_size.to_le_bytes());
    buf[48..56].copy_from_slice(&index.slot_table_offset.to_le_bytes());
    buf[56..64].copy_from_slice(&index.slot_table_size.to_le_bytes());
    buf[64..68].copy_from_slice(&index.slot_count.to_le_bytes());
    buf[68..72].copy_from_slice(&index.flags.to_le_bytes());
    buf[72..104].copy_from_slice(&index.ephemeral_public_key);
    buf[104..136].copy_from_slice(&index.metadata_checksum);
    buf[136..256].copy_from_slice(&index.reserved);
    
    // Calculate checksum with placeholder set to 0
    let checksum = adler::adler32_slice(&buf);
    buf[12..16].copy_from_slice(&checksum.to_le_bytes());
    
    out.write_all(&buf)?;
    Ok(())
}

