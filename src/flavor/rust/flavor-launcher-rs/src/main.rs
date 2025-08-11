//
// flavor/rust/flavor-launcher-rs/src/main.rs
//
use anyhow::{Context, Result};
use clap::Parser;
use flate2::read::GzDecoder;
use log::{debug, error, info, trace};
use sha2::{Digest, Sha256};
use std::fs::File;
use std::io::{Read, Seek, SeekFrom};
use std::path::PathBuf;
use std::process::{Command, exit};
use tar::Archive;

mod flavor;
use flavor::{FlavorFooter, FLAVOR_MAGIC_EOF_STRING, FLAVOR_INTERNAL_FOOTER_MAGIC, FOOTER_SIZE};

mod verification;
use verification::verify_package_signature;

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

fn main() {
    // Check if we should show developer CLI instead of running the package
    if std::env::var("FLAVOR_LAUNCHER_CLI").is_ok() {
        // Parse CLI args and show developer interface
        let args = Cli::parse();
        
        // Initialize logging
        let log_level = if args.verbose { "trace" } else { "info" };
        env_logger::Builder::from_env(
            env_logger::Env::default()
                .default_filter_or(log_level)
                .default_write_style_or("never")
        )
        .target(env_logger::Target::Stderr)
        .format_timestamp_secs()
        .init();
        
        // TODO: Implement developer CLI commands (verify, inspect, extract, etc.)
        eprintln!("Developer CLI mode enabled. Commands not yet implemented.");
        eprintln!("Available flags: --verbose, --cache-dir, --force-extract");
        exit(0);
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

    // Read metadata to get entry point
    let mut metadata_path = cache_dir.join("metadata/config.json");
    if !metadata_path.exists() {
        // Old structure from Go/Rust packagers
        metadata_path = cache_dir.join("cache/metadata/config.json");
    }
    let config_data = std::fs::read_to_string(&metadata_path)
        .with_context(|| format!("Could not read metadata from {}", metadata_path.display()))?;

    let entry_point = extract_entry_point(&config_data)
        .context("Could not find entry point in metadata")?;

    trace!("🎯 Found entry point: entry_point={}", entry_point);

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
    let max_data_end = *data_ends.iter().max().unwrap();
    
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


// 📦🍜📄🪄
