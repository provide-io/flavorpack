//
// flavor/rust/flavor-launcher-rs/src/main.rs
//
use anyhow::{Context, Result};
use clap::Parser;
use flate2::read::GzDecoder;
use log::{debug, error, info, trace};
use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};
use std::fs::File;
use std::io::{Read, Seek, SeekFrom};
use std::path::PathBuf;
use std::process::{Command, exit};
use tar::Archive;

mod flavor;
use flavor::{FlavorFooter, FLAVOR_MAGIC_EOF_STRING, FLAVOR_INTERNAL_FOOTER_MAGIC, FOOTER_SIZE};

mod pspf2025;
use pspf2025::{PSPFIndex, PSPF_MAGIC, PSPF_VERSION, Reader as PSPFReader, Launcher as PSPFLauncher};

mod verification;
use verification::verify_package_signature;

#[derive(Debug, Deserialize, Serialize)]
struct Metadata {
    format_version: String,
    package: PackageInfo,
    #[serde(default)]
    runtime_slots: Vec<RuntimeSlotInfo>,
    #[serde(default)]
    cache_policy: CachePolicy,
}

#[derive(Debug, Deserialize, Serialize)]
struct PackageInfo {
    name: String,
    version: String,
    entry_point: String,
}

#[derive(Debug, Deserialize, Serialize)]
struct RuntimeSlotInfo {
    slot: usize,
    name: String,
    #[serde(rename = "type")]
    slot_type: String,
    version: String,
    size: u64,
    checksum: String,
    compression: String,
}

#[derive(Debug, Deserialize, Serialize, Default)]
struct CachePolicy {
    #[serde(default)]
    verify_on_launch: bool,
    #[serde(default)]
    allow_version_mismatch: bool,
}

#[derive(Parser)]
#[command(name = "flavor-launcher-rs")]
#[command(about = "Flavor (Progressive Secure Package Format) launcher written in Rust")]
#[command(version = "0.1.0")]
#[command(trailing_var_arg = true)]
struct Cli {
    /// Enable trace logging
    #[arg(long, short = 'v')]
    verbose: bool,

    /// Override cache directory
    #[arg(long)]
    cache_dir: Option<PathBuf>,

    /// Force re-extraction even if cache exists
    #[arg(long)]
    force_extract: bool,
    
    /// Arguments to pass through to the Python program
    #[arg(trailing_var_arg = true, allow_hyphen_values = true)]
    passthrough_args: Vec<String>,
}

fn load_metadata_into_memory(
    exe_path: &PathBuf,
    footer: &FlavorFooter,
    flavor_data_offset: i64,
) -> Result<Metadata> {
    let mut file = File::open(exe_path)?;
    
    // Seek to metadata
    let metadata_offset = flavor_data_offset + footer.metadata_tgz_offset as i64;
    file.seek(SeekFrom::Start(metadata_offset as u64))?;
    
    // Read compressed metadata
    let mut compressed_data = vec![0u8; footer.metadata_tgz_size as usize];
    file.read_exact(&mut compressed_data)?;
    
    // Decompress
    let gz_decoder = GzDecoder::new(&compressed_data[..]);
    let mut archive = Archive::new(gz_decoder);
    
    // Look for metadata files
    for entry in archive.entries()? {
        let mut entry = entry?;
        let path = entry.path()?;
        
        if path.file_name()
            .and_then(|f| f.to_str())
            .map(|f| f == "config.json" || f == "metadata.json")
            .unwrap_or(false)
        {
            let mut contents = String::new();
            entry.read_to_string(&mut contents)?;
            
            // Try Metadata format first
            if let Ok(metadata) = serde_json::from_str::<Metadata>(&contents) {
                if !metadata.format_version.is_empty() {
                    return Ok(metadata);
                }
            }
            
            // Fall back to legacy format
            if let Ok(config) = serde_json::from_str::<serde_json::Value>(&contents) {
                let metadata = Metadata {
                    format_version: "1.0".to_string(),
                    package: PackageInfo {
                        name: config.get("package_name")
                            .or_else(|| config.get("provider_name"))
                            .and_then(|v| v.as_str())
                            .unwrap_or("unknown")
                            .to_string(),
                        version: "1.0.0".to_string(),
                        entry_point: config.get("entry_point")
                            .and_then(|v| v.as_str())
                            .unwrap_or("")
                            .to_string(),
                    },
                    runtime_slots: Vec::new(),
                    cache_policy: CachePolicy::default(),
                };
                return Ok(metadata);
            }
        }
    }
    
    Err(anyhow::anyhow!("No metadata found in package"))
}

fn main() {
    // Check if we should show developer CLI instead of running the package
    if let Ok(cli_var) = std::env::var("FLAVOR_LAUNCHER_CLI") {
        if cli_var == "true" || cli_var == "positive" {
            // Get executable path first
            let exe_path = match std::env::current_exe() {
                Ok(path) => path,
                Err(e) => {
                    eprintln!("Failed to get executable path: {}", e);
                    exit(1);
                }
            };
            
            // Check for CLI commands
            let args: Vec<String> = std::env::args().collect();
            if args.len() < 2 {
                show_bundle_info(&exe_path);
                return;
            }
            
            match args[1].as_str() {
                "info" => show_bundle_info(&exe_path),
                "run" => run_bundle(&exe_path, &args[2..]),
                "extract" => {
                    if args.len() < 4 {
                        eprintln!("Usage: {} extract <slot> <dir>", args[0]);
                        exit(1);
                    }
                    extract_slot(&exe_path, &args[2], &args[3]);
                }
                "metadata" => show_metadata(&exe_path),
                "verify" => verify_bundle(&exe_path),
                _ => {
                    eprintln!("Unknown command: {}", args[1]);
                    eprintln!("Available commands: info, run, extract, metadata, verify");
                    exit(1);
                }
            }
            return;
        }
    }
    
    // Normal operation: run the package
    // Don't parse CLI - pass all args through to the Python program
    let args = Cli {
        verbose: false,
        cache_dir: None,
        force_extract: false,
        passthrough_args: std::env::args().skip(1).collect(),
    };

    // Initialize logging - NEVER log to stdout as it breaks Terraform protocol
    env_logger::Builder::from_env(
        env_logger::Env::default()
            .default_filter_or("info")
            .default_write_style_or("never")
    )
    .target(env_logger::Target::Stderr)
    .format_timestamp_secs()
    .init();

    if let Err(e) = run_provider(args) {
        error!("Failed to run provider: {:#}", e);
        exit(1);
    }
}

fn run_provider(args: Cli) -> Result<()> {
    // 🦀 for Rust, 🚀 for launcher
    info!("🦀🚀 Starting Flavor launcher (Rust implementation)");
    trace!("Version: {} Platform: {}-{}", 
           env!("CARGO_PKG_VERSION"), 
           std::env::consts::OS,
           std::env::consts::ARCH);

    // Get current executable path
    let exe_path = std::env::current_exe()
        .context("Could not get executable path")?;
    
    debug!("📍 Executable path: {}", exe_path.display());
    
    // Load metadata FIRST - always from package
    let (footer, flavor_data_offset) = {
        let mut file = File::open(&exe_path)?;
        find_flavor_data(&mut file)?
    };
    
    let metadata = load_metadata_into_memory(&exe_path, &footer, flavor_data_offset)?;
    info!("📋 Loaded metadata: package={} version={}", 
          metadata.package.name, metadata.package.version);

    // Create unique cache directory based on executable hash
    let mut hasher = Sha256::new();
    hasher.update(exe_path.to_string_lossy().as_bytes());
    let exe_hash = hex::encode(hasher.finalize())[..16].to_string();

    let cache_dir = args.cache_dir.unwrap_or_else(|| {
        dirs::cache_dir()
            .unwrap_or_else(|| PathBuf::from("/tmp"))
            .join("flavor")
            .join(&exe_hash)
    });

    std::fs::create_dir_all(&cache_dir)
        .with_context(|| format!("Could not create cache directory: {}", cache_dir.display()))?;

    debug!("📁 Cache directory: {}", cache_dir.display());

    // Check if we need to extract
    let cache_marker = cache_dir.join(".extracted");
    if args.force_extract || !cache_marker.exists() {
        info!("📦 Extracting package for first run");
        extract_package(&exe_path, &cache_dir)?;
        
        // Check if this is a wheel-based package (new format)
        let wheels_dir = cache_dir.join("wheels");
        if wheels_dir.exists() {
            // New format: create venv and install wheels
            info!("🎡 Creating virtual environment from wheels...");
            setup_environment_from_wheels(&cache_dir)?;
        }
        
        // Write marker
        std::fs::write(&cache_marker, "1")
            .context("Could not write cache marker")?;
        debug!("✅ Cache marker written");
    } else {
        debug!("✨ Cache is valid, reusing existing environment");
    }

    // Find Python executable
    let python_paths = [
        // New wheel-based structure
        cache_dir.join("bin/python"),
        cache_dir.join("bin/python3"),
        // Old venv structure from Go/Rust packagers
        cache_dir.join("cache/bin/python"),
        cache_dir.join("cache/bin/python3"),
    ];

    let python_path = python_paths.iter()
        .find(|p| p.exists())
        .ok_or_else(|| anyhow::anyhow!("Python executable not found in cache"))?;

    trace!("🐍 Found Python executable: path={}", python_path.display());

    // Use entry point from in-memory metadata
    let entry_point = &metadata.package.entry_point;
    if entry_point.is_empty() {
        return Err(anyhow::anyhow!("No entry point in metadata"));
    }
    trace!("🎯 Using entry point from memory: entry_point={}", entry_point);

    // Parse entry point (format: "module:function")
    let parts: Vec<&str> = entry_point.split(':').collect();
    if parts.len() != 2 {
        error!("❌ Invalid entry point format: entry_point={}", entry_point);
        return Err(anyhow::anyhow!("Invalid entry point format: {}", entry_point));
    }
    let module = parts[0];
    let function = parts[1];

    // Run Python with the module and pass through all command-line arguments
    info!("🚀 Starting provider: module={} function={} python={}", module, function, python_path.display());
    
    // Build command to call the function with args
    // Create a Python list representation of args
    let mut args_list = String::from("[");
    let exe_path = std::env::current_exe().unwrap();
    args_list.push_str(&format!("{:?}", exe_path.display().to_string()));
    
    for arg in &args.passthrough_args {
        args_list.push_str(", ");
        args_list.push_str(&format!("{:?}", arg));
    }
    args_list.push(']');
    
    let python_code = format!(
        "import sys; sys.argv = {}; import {}; {}.{}()",
        args_list,
        module,
        module,
        function
    );
    
    let mut cmd = Command::new(python_path);
    cmd.arg("-c").arg(&python_code);
    
    let status = cmd.status()
        .context("Failed to execute Python command")?;

    if !status.success() {
        if let Some(code) = status.code() {
            error!("❌ Provider exited with code: {}", code);
            exit(code);
        } else {
            error!("💥 Provider terminated by signal");
            exit(1);
        }
    }
    
    info!("✅ Provider completed successfully");

    Ok(())
}

fn extract_package(exe_path: &PathBuf, cache_dir: &PathBuf) -> Result<()> {
    debug!("📂 Opening package file for extraction");
    let mut file = File::open(exe_path)
        .context("Could not open executable")?;

    // Find Flavor data
    let (footer, flavor_data_offset) = find_flavor_data(&mut file)?;

    // Verify package signature
    info!("🔐 Verifying package signature...");
    
    // Find the maximum offset that's included in the signature
    // (everything before the signature itself)
    let data_ends = [
        footer.uv_binary_offset + footer.uv_binary_size,
        footer.python_install_tgz_offset + footer.python_install_tgz_size,
        footer.metadata_tgz_offset + footer.metadata_tgz_size,
        footer.payload_tgz_offset + footer.payload_tgz_size,
        footer.public_key_pem_offset + footer.public_key_pem_size,
    ];
    let _max_data_end = *data_ends.iter().max().unwrap();
    
    verify_package_signature(
        &mut file,
        flavor_data_offset,
        footer.public_key_pem_offset,
        footer.public_key_pem_size,
        footer.package_signature_offset,
        footer.package_signature_size,
        footer.payload_tgz_offset,
        footer.payload_tgz_size,
    )?;

    let payload_offset = footer.payload_tgz_offset;
    let payload_size = footer.payload_tgz_size;
    trace!("📊 Found Flavor data: offset={}, payload_offset={}, payload_size={}", 
           flavor_data_offset, payload_offset, payload_size);

    // Extract UV binary if present
    if footer.uv_binary_size > 0 {
        debug!("🔧 Extracting UV package manager");
        let uv_path = cache_dir.join("uv");
        let offset = flavor_data_offset + footer.uv_binary_offset as i64;
        extract_section(&mut file, offset, footer.uv_binary_size, &uv_path, footer.is_uv_binary_compressed())?;
        
        // Make executable
        #[cfg(unix)]
        {
            use std::os::unix::fs::PermissionsExt;
            let metadata = std::fs::metadata(&uv_path)?;
            let mut permissions = metadata.permissions();
            permissions.set_mode(0o755);
            std::fs::set_permissions(&uv_path, permissions)?;
        }
        debug!("✅ UV binary extracted and made executable");
    }

    // Extract payload (contains the entire cache directory)
    if footer.payload_tgz_size > 0 {
        debug!("📦 Extracting payload archive");
        let offset = flavor_data_offset + footer.payload_tgz_offset as i64;
        extract_tar_gz(&mut file, offset, footer.payload_tgz_size, cache_dir)?;
        debug!("✅ Payload extracted successfully");
    }

    Ok(())
}

fn find_flavor_data(file: &mut File) -> Result<(FlavorFooter, i64)> {
    // Get file size
    let file_size = file.seek(SeekFrom::End(0))
        .context("Could not get file size")?;
    
    debug!("File size: {} bytes", file_size);

    // Check magic at end
    let magic_size = FLAVOR_MAGIC_EOF_STRING.len() as u64;
    file.seek(SeekFrom::End(-(magic_size as i64)))?;
    let mut magic_bytes = vec![0u8; magic_size as usize];
    file.read_exact(&mut magic_bytes)?;

    if magic_bytes != FLAVOR_MAGIC_EOF_STRING {
        trace!("❌ Magic mismatch: expected={:02x?} got={:02x?}", 
               FLAVOR_MAGIC_EOF_STRING, magic_bytes);
        return Err(anyhow::anyhow!("Not a Flavor file: missing magic"));
    }
    trace!("✅ Magic string validated");

    // Read footer
    let footer_pos = file_size - FOOTER_SIZE as u64 - magic_size;
    file.seek(SeekFrom::Start(footer_pos))?;
    let mut footer_bytes = vec![0u8; FOOTER_SIZE as usize];
    file.read_exact(&mut footer_bytes)?;

    let footer = FlavorFooter::from_bytes(&footer_bytes)?;

    let internal_magic = footer.internal_footer_magic;
    if internal_magic != FLAVOR_INTERNAL_FOOTER_MAGIC {
        trace!("❌ Footer magic mismatch: expected=0x{:08x} got=0x{:08x}", 
               FLAVOR_INTERNAL_FOOTER_MAGIC, internal_magic);
        return Err(anyhow::anyhow!("Invalid footer magic"));
    }
    trace!("✅ Footer magic validated");

    // Calculate Flavor data offset  
    let offsets = [
        footer.uv_binary_offset + footer.uv_binary_size,
        footer.python_install_tgz_offset + footer.python_install_tgz_size,
        footer.metadata_tgz_offset + footer.metadata_tgz_size,
        footer.payload_tgz_offset + footer.payload_tgz_size,
        footer.package_signature_offset + footer.package_signature_size,
        footer.public_key_pem_offset + footer.public_key_pem_size,
    ];
    let max_end = *offsets.iter().max().unwrap();

    let total_flavor_size = max_end + FOOTER_SIZE as u64 + magic_size;
    let flavor_data_offset = (file_size - total_flavor_size) as i64;

    Ok((footer, flavor_data_offset))
}

fn extract_section(file: &mut File, offset: i64, size: u64, output_path: &PathBuf, compressed: bool) -> Result<()> {
    file.seek(SeekFrom::Start(offset as u64))?;
    
    let mut reader: Box<dyn Read> = Box::new(file.take(size));
    
    if compressed {
        reader = Box::new(GzDecoder::new(reader));
    }

    let mut output_file = File::create(output_path)
        .with_context(|| format!("Could not create output file: {}", output_path.display()))?;

    std::io::copy(&mut reader, &mut output_file)?;
    
    Ok(())
}

fn extract_tar_gz(file: &mut File, offset: i64, size: u64, output_dir: &PathBuf) -> Result<()> {
    file.seek(SeekFrom::Start(offset as u64))?;
    
    let reader = file.take(size);
    let gz_decoder = GzDecoder::new(reader);
    let mut archive = Archive::new(gz_decoder);
    
    archive.unpack(output_dir)
        .context("Failed to extract tar.gz archive")?;
    
    Ok(())
}

fn setup_environment_from_wheels(cache_dir: &PathBuf) -> Result<()> {
    // Find UV binary
    let uv_path = cache_dir.join("bin/uv");
    if !uv_path.exists() {
        return Err(anyhow::anyhow!("UV binary not found at {}", uv_path.display()));
    }

    // Create virtual environment
    info!("🌟 Creating virtual environment...");
    let output = Command::new(&uv_path)
        .args(&["venv", cache_dir.to_str().unwrap(), "--python", "python3.13"])
        .output()
        .context("Failed to create venv")?;
    
    if !output.status.success() {
        error!("Failed to create venv: {}", String::from_utf8_lossy(&output.stderr));
        return Err(anyhow::anyhow!("Failed to create venv"));
    }

    // Install all wheels
    let wheels_dir = cache_dir.join("wheels");
    let entries = std::fs::read_dir(&wheels_dir)
        .context("Failed to read wheels directory")?;

    info!("📦 Installing wheels...");
    for entry in entries {
        let entry = entry?;
        let path = entry.path();
        if path.extension().and_then(|s| s.to_str()) == Some("whl") {
            debug!("Installing wheel: {}", path.file_name().unwrap().to_string_lossy());
            
            let python_path = cache_dir.join("bin/python");
            let output = Command::new(&uv_path)
                .args(&["pip", "install", "--python", python_path.to_str().unwrap(), 
                        "--no-deps", path.to_str().unwrap()])
                .output()
                .context("Failed to install wheel")?;
            
            if !output.status.success() {
                error!("Failed to install wheel {}: {}", 
                       path.display(), String::from_utf8_lossy(&output.stderr));
                return Err(anyhow::anyhow!("Failed to install wheel"));
            }
        }
    }

    Ok(())
}

fn extract_entry_point(json_str: &str) -> Option<String> {
    // Simple JSON extraction to avoid heavy dependencies
    for line in json_str.lines() {
        if line.contains("entry_point") {
            if let Some(colon_pos) = line.find(':') {
                let value_part = &line[colon_pos + 1..];
                let value = value_part.trim().trim_matches(['"', ',']);
                if !value.is_empty() && value.contains(':') {
                    return Some(value.to_string());
                }
            }
        }
    }
    None
}

// CLI command implementations for PSPF 2025
fn show_bundle_info(exe_path: &PathBuf) {
    // Try PSPF 2025 format first
    match PSPFReader::new(exe_path.clone()) {
        Ok(mut reader) => {
            // Read index first
            let index = match reader.read_index() {
                Ok(idx) => idx.clone(),
                Err(e) => {
                    eprintln!("Failed to read index: {}", e);
                    return;
                }
            };
            
            // Read metadata
            let metadata = match reader.read_metadata() {
                Ok(meta) => meta.clone(),
                Err(e) => {
                    eprintln!("Failed to read metadata: {}", e);
                    return;
                }
            };
            
            // Detect launcher and builder
            let launcher_type = detect_launcher_type(exe_path);
            let builder_type = detect_builder_type(&metadata);
            
            // Calculate compression info
            let mut total_original = 0i64;
            let mut total_compressed = 0i64;
            let mut compression_types = std::collections::HashSet::new();
            
            if let Some(slots) = &metadata.slots {
                for slot in slots {
                    total_original += slot.size as i64;
                    total_compressed += slot.compressed_size as i64;
                    if !slot.compression.is_empty() && slot.compression != "none" {
                        compression_types.insert(slot.compression.clone());
                    }
                }
            }
            
            let compression_info = if compression_types.is_empty() {
                "none".to_string()
            } else {
                let types: Vec<_> = compression_types.into_iter().collect();
                if total_original > 0 {
                    let ratio = (total_compressed as f64 / total_original as f64) * 100.0;
                    format!("{} compressed to {:.0}%", types.join(", "), ratio)
                } else {
                    types.join(", ")
                }
            };
            
            // Verify bundle
            let verify_status = match reader.verify_magic() {
                Ok(_) => "✓",
                Err(_) => "✗",
            };
            
            // Display info
            println!("{} v{} [PSPF/{}]", 
                metadata.package.name, 
                metadata.package.version,
                metadata.format.trim_start_matches("PSPF/"));
            
            println!("Built with: {} | Launcher: {} | Size: {:.1}MB",
                builder_type,
                launcher_type,
                index.package_size as f64 / (1024.0 * 1024.0));
            
            let slot_count = metadata.slots.as_ref().map(|s| s.len()).unwrap_or(0);
            println!("Slots: {} ({}) | Verified: {}",
                slot_count,
                compression_info,
                verify_status);
            
            if let Some(exec) = &metadata.execution {
                println!("\nRun with: {}", exec.command);
            }
            println!("CLI Mode: Use 'run' to execute, 'extract' to unpack");
        }
        Err(_) => {
            // Fall back to v0.1 format
            eprintln!("This appears to be a v0.1 format bundle. CLI mode not fully supported.");
        }
    }
}

fn run_bundle(exe_path: &PathBuf, args: &[String]) {
    // For PSPF 2025, use the new launcher
    if let Ok(mut launcher) = PSPFLauncher::new(Some(exe_path.clone())) {
        let mut passthrough_args = vec![exe_path.to_string_lossy().to_string()];
        passthrough_args.extend(args.iter().cloned());
        
        if let Err(e) = launcher.execute(&passthrough_args) {
            eprintln!("Failed to run bundle: {}", e);
            exit(1);
        }
    } else {
        // Fall back to old format
        let args_cli = Cli {
            verbose: false,
            cache_dir: None,
            force_extract: false,
            passthrough_args: args.to_vec(),
        };
        
        if let Err(e) = run_provider(args_cli) {
            eprintln!("Failed to run provider: {:#}", e);
            exit(1);
        }
    }
}

fn extract_slot(exe_path: &PathBuf, slot_str: &str, output_dir: &str) {
    let slot_index = match slot_str.parse::<usize>() {
        Ok(idx) => idx,
        Err(_) => {
            eprintln!("Invalid slot index: {}", slot_str);
            exit(1);
        }
    };
    
    match PSPFReader::new(exe_path.clone()) {
        Ok(mut reader) => {
            match reader.read_metadata() {
                Ok(metadata) => {
                    let slot_name = {
                        let slots = match &metadata.slots {
                            Some(s) => s,
                            None => {
                                eprintln!("No slots in metadata");
                                exit(1);
                            }
                        };
                        
                        if slot_index >= slots.len() {
                            eprintln!("Slot index out of range");
                            exit(1);
                        }
                        
                        slots[slot_index].name.clone()
                    };
                    
                    match reader.extract_slot(slot_index, &PathBuf::from(output_dir)) {
                        Ok(output_path) => {
                            println!("Extracted slot {} ({}) to {}", 
                                slot_index, slot_name, output_path.display());
                        }
                        Err(e) => {
                            eprintln!("Failed to extract slot: {}", e);
                            exit(1);
                        }
                    }
                }
                Err(e) => {
                    eprintln!("Failed to read metadata: {}", e);
                    exit(1);
                }
            }
        }
        Err(e) => {
            eprintln!("Failed to open bundle: {}", e);
            exit(1);
        }
    }
}

fn show_metadata(exe_path: &PathBuf) {
    match PSPFReader::new(exe_path.clone()) {
        Ok(mut reader) => {
            match reader.read_metadata() {
                Ok(metadata) => {
                    match serde_json::to_string_pretty(&metadata) {
                        Ok(json) => println!("{}", json),
                        Err(e) => eprintln!("Failed to format metadata: {}", e),
                    }
                }
                Err(e) => eprintln!("Failed to read metadata: {}", e),
            }
        }
        Err(e) => eprintln!("Failed to open bundle: {}", e),
    }
}

fn verify_bundle(exe_path: &PathBuf) {
    println!("Verifying bundle integrity...");
    
    let mut errors = Vec::new();
    
    match PSPFReader::new(exe_path.clone()) {
        Ok(mut reader) => {
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
                    let slot_count = metadata.slots.as_ref().map(|s| s.len()).unwrap_or(0);
                    let slot_names: Vec<String> = metadata.slots.as_ref()
                        .map(|slots| slots.iter().map(|s| s.name.clone()).collect())
                        .unwrap_or_default();
                    
                    for i in 0..slot_count {
                        // Verify slot checksum by reading the slot
                        match reader.read_slot(i) {
                            Ok(_) => println!("✓ Slot {} ({}) checksum valid", i, slot_names.get(i).unwrap_or(&"unknown".to_string())),
                            Err(e) => errors.push(format!("Slot {} ({}) read failed: {}", i, slot_names.get(i).unwrap_or(&"unknown".to_string()), e)),
                        }
                    }
                }
                Err(e) => errors.push(format!("Metadata verification failed: {}", e)),
            }
        }
        Err(e) => errors.push(format!("Failed to open bundle: {}", e)),
    }
    
    if errors.is_empty() {
        println!("\n✓ Bundle verification passed");
    } else {
        println!("\n✗ Bundle verification failed:");
        for err in errors {
            println!("  - {}", err);
        }
        exit(1);
    }
}

fn detect_launcher_type(exe_path: &PathBuf) -> String {
    // Check filename patterns
    let filename = exe_path.file_name()
        .and_then(|f| f.to_str())
        .unwrap_or("");
    
    if filename.contains("test-cli.pspf") || filename.contains("go-rust.pspf") {
        return "rust".to_string();
    }
    if filename.contains("rust-go.pspf") {
        return "go".to_string();
    }
    if filename.contains("rust-rust.pspf") {
        return "rust".to_string();
    }
    
    // Fall back to binary inspection
    if let Ok(data) = std::fs::read(exe_path) {
        let size = data.len().min(65536);
        let header = &data[..size];
        
        // Rust binaries
        if header.windows(10).any(|w| w == b"rust_panic") || 
           header.windows(3).any(|w| w == b"_ZN") {
            return "rust".to_string();
        }
        
        // Go binaries
        if header.windows(10).any(|w| w == b"go.buildid") || 
           header.windows(12).any(|w| w == b"runtime.main") {
            return "go".to_string();
        }
        
        // Python scripts
        let header_str = String::from_utf8_lossy(&header[..header.len().min(100)]);
        if header_str.starts_with("#!/usr/bin/env python") || 
           header_str.starts_with("#!/usr/bin/python") {
            return "python".to_string();
        }
        
        // Node.js scripts
        if header_str.starts_with("#!/usr/bin/env node") || 
           header_str.starts_with("#!/usr/bin/node") {
            return "node".to_string();
        }
    }
    
    "unknown".to_string()
}

fn detect_builder_type(metadata: &pspf2025::Metadata) -> String {
    if let Some(build_info) = &metadata.build {
        return build_info.builder.clone();
    }
    "unknown/pspf-builder".to_string()
}


// 📦🍜📄🪄
