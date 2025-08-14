use anyhow::{anyhow, Context, Result};
use flate2::read::GzDecoder;
use log::{debug, error, info, trace, warn};
use serde::{Deserialize, Serialize};
use serde_json::Value;
use std::env;
use std::fs::{self, File};
use std::io::{Read, Seek, SeekFrom, Write};
use std::os::unix::fs::PermissionsExt;
use std::path::{Path, PathBuf};
use std::process::{Command, Stdio};
use tar::Archive;
use tempfile::TempDir;

mod verify;

const PSPF_MAGIC: &[u8] = b"PSPF2025";

const MAX_SEARCH_SIZE: u64 = 10 * 1024 * 1024; // 10MB

use pspf_common::{PSPFIndex, INDEX_SIZE};

#[derive(Debug, Deserialize, Serialize)]
struct Metadata {
    format: String,
    package: PackageInfo,
    slots: Vec<SlotMetadata>,
    execution: ExecutionInfo,
    #[serde(skip_serializing_if = "Option::is_none")]
    build: Option<BuildInfo>,
    #[serde(skip_serializing_if = "Option::is_none")]
    cache_validation: Option<CacheValidationInfo>,
    #[serde(skip_serializing_if = "Option::is_none")]
    runtime: Option<RuntimeInfo>,
    #[serde(default)]
    setup_commands: Vec<Value>,
}

#[derive(Debug, Deserialize, Serialize)]
struct CacheValidationInfo {
    check_file: String,
    expected_content: String,
}

#[derive(Debug, Deserialize, Serialize)]
struct PackageInfo {
    name: String,
    version: String,
}

#[derive(Debug, Deserialize, Serialize)]
struct SlotMetadata {
    index: usize,
    name: String,
    size: i64,
    compressed_size: i64,
    checksum: String,
    encoding: String,
    purpose: String,
    lifecycle: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    extract_to: Option<String>,
}

#[derive(Debug, Deserialize, Serialize)]
struct ExecutionInfo {
    primary_slot: usize,
    command: String,
    #[serde(default)]
    environment: std::collections::HashMap<String, String>,
}

#[derive(Debug, Deserialize, Serialize)]
struct BuildInfo {
    builder: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    version: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    timestamp: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    host: Option<String>,
}

#[derive(Debug, Deserialize, Serialize)]
struct RuntimeInfo {
    #[serde(skip_serializing_if = "Option::is_none")]
    env: Option<RuntimeEnv>,
}

#[derive(Debug, Deserialize, Serialize)]
struct RuntimeEnv {
    #[serde(skip_serializing_if = "Option::is_none")]
    unset: Option<Vec<String>>,
    #[serde(skip_serializing_if = "Option::is_none")]
    map: Option<std::collections::HashMap<String, String>>,
    #[serde(skip_serializing_if = "Option::is_none")]
    set: Option<std::collections::HashMap<String, String>>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pass: Option<Vec<String>>,
}

/// 🚀 Main entry point for the PSPF Rust launcher
/// 
/// The launcher follows this execution flow:
/// 1. Initialize logging based on FLAVOR_LOG_LEVEL/FLAVOR_RUST_LOG_LEVEL
/// 2. Capture the user's current working directory (CWD)
/// 3. Check for special modes (verify, CLI commands)
/// 4. Read and validate the PSPF package format
/// 5. Extract metadata and slots to a temporary work environment
/// 6. Run setup commands if needed (or skip if environment is cached/valid)
/// 7. Execute the primary command while preserving the user's CWD
/// 
/// The launcher ensures all subprocesses run in the user's original directory
/// while having access to the extracted work environment via FLAVOR_WORKENV.
fn main() -> Result<()> {
    // 🚀 Initialize logging with FLAVOR_LOG_LEVEL
    // Prioritize FLAVOR_RUST_LOG_LEVEL, then FLAVOR_LOG_LEVEL, then default to "info"
    let log_level = env::var("FLAVOR_RUST_LOG_LEVEL")
        .or_else(|_| env::var("FLAVOR_LOG_LEVEL"))
        .unwrap_or_else(|_| "info".to_string());
    
    env_logger::Builder::from_env(env_logger::Env::default())
        .filter_level(log_level.parse().unwrap_or(log::LevelFilter::Info))
        .format_timestamp_millis()
        .init();
    
    // 🦀 Log launcher info
    info!("🦀 PSPF Rust Launcher v{} starting...", env!("CARGO_PKG_VERSION"));
    info!("🏗️ Built with Rust {}", env!("CARGO_PKG_RUST_VERSION"));
    debug!("🔍 Debug logging enabled at level: {}", log_level);
    
    // 🌍 Log incoming environment variables
    let env_vars: Vec<(String, String)> = env::vars().collect();
    debug!("📊 Environment variables received from parent process: count={}", env_vars.len());
    
    // Log all environment variables in trace mode
    if log::log_enabled!(log::Level::Trace) {
        for (key, value) in &env_vars {
            trace!("🔑 Env var: {}={}", key, value);
        }
    }
    
    // 📍 Get the path to our own executable
    let exe_path = env::current_exe()
        .context("Failed to get executable path")?;
    debug!("📦 Bundle path: {:?}", exe_path);
    
    // 📂 Capture user's current working directory early
    let user_cwd = env::current_dir()
        .context("Failed to get current directory")?;
    debug!("📂 User working directory: {:?}", user_cwd);

    // 🔍 Check for verify mode
    let args: Vec<String> = env::args().collect();
    if args.len() > 1 && args[1] == "verify" {
        info!("🔐 Running in verify mode");
        return verify::verify_package(&exe_path);
    }

    // 🖥️ Check if CLI mode is enabled
    if env::var("FLAVOR_LAUNCHER_CLI").unwrap_or_default() == "true" {
        info!("💻 Running in CLI mode");
        if args.len() < 2 {
            show_bundle_info(&exe_path)?;
            return Ok(());
        }
        
        match args[1].as_str() {
            "info" => show_bundle_info(&exe_path)?,
            "run" => run_bundle(&exe_path, &args[2..])?,
            "extract" => {
                if args.len() < 4 {
                    eprintln!("Usage: {} extract <slot> <dir>", args[0]);
                    std::process::exit(1);
                }
                extract_slot(&exe_path, &args[2], &args[3])?;
            }
            "metadata" => show_metadata(&exe_path)?,
            "verify" => verify_bundle(&exe_path)?,
            _ => {
                eprintln!("Unknown command: {}", args[1]);
                eprintln!("Available commands: info, run, extract, metadata, verify");
                std::process::exit(1);
            }
        }
        return Ok(());
    }

    // 📖 Create reader for our bundle
    let mut reader = Reader::new(&exe_path)?;
    info!("📖 Reading PSPF bundle");

    // 📋 Read metadata
    let metadata = reader.read_metadata()?;
    info!("📦 Package: {} v{}", metadata.package.name, metadata.package.version);
    debug!("🎯 Primary slot: {}", metadata.execution.primary_slot);
    debug!("🔧 Command: {}", metadata.execution.command);

    // 🗂️ Create work environment directory
    let workenv_dir = TempDir::new_in(env::temp_dir())
        .context("Failed to create work environment directory")?;
    info!("📁 Work environment: {:?}", workenv_dir.path());

    // 📤 Extract all slots
    info!("📤 Extracting {} slots...", metadata.slots.len());
    let mut slot_paths = std::collections::HashMap::new();
    for (i, slot) in metadata.slots.iter().enumerate() {
        debug!("📦 Extracting slot {}: {} ({} bytes)", i, slot.name, slot.size);
        let slot_path = reader.extract_slot(i, workenv_dir.path())?;
        debug!("✅ Extracted to: {:?}", slot_path);
        slot_paths.insert(slot.index, slot_path);
    }

    // 🔍 Check work environment validity
    // If a validation file is specified, check if the environment is already set up
    let workenv_valid = if let Some(cache_validation) = &metadata.cache_validation {
        check_workenv_validity(workenv_dir.path(), cache_validation)
    } else {
        false
    };
    
    if workenv_valid {
        info!("✅ Work environment is valid, skipping setup");
    } else {
        // 🔧 Run setup commands
        if !metadata.setup_commands.is_empty() {
            info!("🔧 Running {} setup commands...", metadata.setup_commands.len());
            execute_setup_commands(&metadata.setup_commands, workenv_dir.path(), &metadata.package, &user_cwd)?;
        }
    }
    
    // 🎯 Prepare execution
    let mut command = metadata.execution.command.clone();
    
    // 🔄 Substitute slot references in command
    for (idx, path) in &slot_paths {
        let placeholder = format!("{{slot:{}}}", idx);
        command = command.replace(&placeholder, path.to_str().unwrap());
    }
    
    // 🔄 Substitute work environment and package info
    command = command.replace("{workenv}", workenv_dir.path().to_str().unwrap());
    command = command.replace("{package_name}", &metadata.package.name);
    command = command.replace("{version}", &metadata.package.version);
    
    debug!("🎯 Final command: {}", command);

    // 🔪 Parse command
    let parts: Vec<&str> = command.split_whitespace().collect();
    if parts.is_empty() {
        error!("❌ Empty command");
        return Err(anyhow!("Empty command"));
    }
    debug!("🔪 Command parts: {:?}", parts);

    // Build command with arguments
    let mut cmd = Command::new(parts[0]);
    
    // Add command arguments
    if parts.len() > 1 {
        cmd.args(&parts[1..]);
    }
    
    // Add original arguments (skip our own executable name)
    let args: Vec<String> = env::args().skip(1).collect();
    if !args.is_empty() {
        cmd.args(&args);
    }

    // 🌍 CRITICAL: Inherit all parent environment variables
    let mut env_map: std::collections::HashMap<String, String> = env::vars().collect();
    debug!("🌍 Inheriting parent environment: {} variables", env_map.len());
    
    // 🔄 Process runtime.env configuration if present
    if let Some(runtime) = &metadata.runtime {
        if let Some(runtime_env) = &runtime.env {
            debug!("🔄 Processing runtime.env configuration");
            process_runtime_env(&mut env_map, runtime_env);
        }
    }
    
    // Apply the processed environment to the command
    for (key, value) in &env_map {
        cmd.env(key, value);
    }

    // Set additional environment from package metadata
    debug!("➕ Adding package-defined environment variables: count={}", metadata.execution.environment.len());
    for (k, mut v) in metadata.execution.environment {
        // Substitute slot references
        for (idx, path) in &slot_paths {
            let placeholder = format!("{{slot:{}}}", idx);
            v = v.replace(&placeholder, path.to_str().unwrap());
        }
        // Substitute work environment and package info
        v = v.replace("{workenv}", workenv_dir.path().to_str().unwrap());
        v = v.replace("{package_name}", &metadata.package.name);
        v = v.replace("{version}", &metadata.package.version);
        cmd.env(&k, &v);
        trace!("➕ Added package env var: {}={}", k, v);
    }
    
    // 🌍 Add FLAVOR_WORKENV environment variable
    cmd.env("FLAVOR_WORKENV", workenv_dir.path());
    
    // 📂 Set working directory to user's original directory
    debug!("📂 Setting working directory to: {:?}", user_cwd);
    cmd.current_dir(&user_cwd);

    // Connect stdio
    cmd.stdin(Stdio::inherit())
        .stdout(Stdio::inherit())
        .stderr(Stdio::inherit());

    // 🚀 Execute
    info!("🚀 Executing: {}", parts[0]);
    debug!("🎯 Command details: args={:?}, cwd={:?}", &parts[1..], user_cwd);
    debug!("📊 Final environment state: all parent vars + package vars passed to subprocess");
    
    // In trace mode, log all environment variables being passed
    if log::log_enabled!(log::Level::Trace) {
        trace!("🌍 Environment variables being passed to subprocess:");
        // Note: We can't easily enumerate cmd.env after building, but we know we passed all parent env + additions
        trace!("  → All parent environment variables inherited");
        trace!("  → Plus FLAVOR_WORKENV and package-specific variables");
    }
    
    let status = cmd.status()
        .context("Failed to execute command")?;

    // 🏁 Exit with same code
    let exit_code = status.code().unwrap_or(1);
    if exit_code == 0 {
        info!("✅ Process exited successfully");
    } else {
        error!("❌ Process exited with code: {}", exit_code);
    }
    std::process::exit(exit_code);
}

/// 📖 Reader for PSPF package files
/// Handles reading the package structure including:
/// - Launcher binary (native executable)
/// - PSPF index (256-byte header)
/// - Metadata archive (compressed psp.json)
/// - Slot table (24-byte entries per slot)
/// - Slot data (payload files)
struct Reader {
    file: File,
    launcher_size: u64,
}

impl Reader {
    fn new(path: &Path) -> Result<Self> {
        let mut file = File::open(path)?;
        let launcher_size = Self::detect_launcher_size(&mut file)?;
        Ok(Self { file, launcher_size })
    }

    fn detect_launcher_size(file: &mut File) -> Result<u64> {
        file.seek(SeekFrom::Start(0))?;

        // Search for PSPF magic in chunks
        const CHUNK_SIZE: usize = 1024 * 1024; // 1MB
        let mut buffer = vec![0u8; CHUNK_SIZE];
        let mut offset = 0u64;

        while offset < MAX_SEARCH_SIZE {
            file.seek(SeekFrom::Start(offset))?;
            let n = file.read(&mut buffer)?;
            if n == 0 {
                break;
            }

            if let Some(pos) = buffer[..n]
                .windows(PSPF_MAGIC.len())
                .position(|window| window == PSPF_MAGIC)
            {
                return Ok(offset + pos as u64);
            }

            offset += CHUNK_SIZE as u64;
        }

        Err(anyhow!("Invalid PSPF magic"))
    }

    fn read_index(&mut self) -> Result<PSPFIndex> {
        self.file.seek(SeekFrom::Start(self.launcher_size))?;
        
        let mut buf = vec![0u8; INDEX_SIZE as usize];
        self.file.read_exact(&mut buf)?;

        // Parse index fields from buffer (matching Go layout)
        let mut index = PSPFIndex {
            format_magic: [0; 8],
            format_version: 0,
            index_checksum: 0,
            package_size: 0,
            launcher_size: 0,
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

        index.format_magic.copy_from_slice(&buf[0..8]);
        index.format_version = u32::from_le_bytes(buf[8..12].try_into()?);
        index.index_checksum = u32::from_le_bytes(buf[12..16].try_into()?);
        index.package_size = u64::from_le_bytes(buf[16..24].try_into()?);
        index.launcher_size = u64::from_le_bytes(buf[24..32].try_into()?);
        index.metadata_offset = u64::from_le_bytes(buf[32..40].try_into()?);
        index.metadata_size = u64::from_le_bytes(buf[40..48].try_into()?);
        index.slot_table_offset = u64::from_le_bytes(buf[48..56].try_into()?);
        index.slot_table_size = u64::from_le_bytes(buf[56..64].try_into()?);
        index.slot_count = u32::from_le_bytes(buf[64..68].try_into()?);
        index.flags = u32::from_le_bytes(buf[68..72].try_into()?);
        index.ephemeral_public_key.copy_from_slice(&buf[72..104]);
        index.metadata_checksum.copy_from_slice(&buf[104..136]);
        index.reserved.copy_from_slice(&buf[136..256]);

        // Verify magic
        if &index.format_magic != b"PSPF2025" {
            return Err(anyhow!("Invalid index magic"));
        }

        // Verify checksum
        let mut check_buf = buf.clone();
        check_buf[12..16].copy_from_slice(&[0, 0, 0, 0]);
        let calculated = adler::adler32_slice(&check_buf);
        if calculated != index.index_checksum {
            return Err(anyhow!("Index checksum mismatch"));
        }

        Ok(index)
    }

    fn read_metadata(&mut self) -> Result<Metadata> {
        let index = self.read_index()?;

        // Read metadata archive
        self.file.seek(SeekFrom::Start(index.metadata_offset))?;
        let mut metadata_data = vec![0u8; index.metadata_size as usize];
        self.file.read_exact(&mut metadata_data)?;

        // Extract metadata from tar.gz
        let gz = GzDecoder::new(&metadata_data[..]);
        let mut tar = Archive::new(gz);

        for entry in tar.entries()? {
            let mut entry = entry?;
            if entry.path()?.to_str() == Some("psp.json") {
                let mut content = String::new();
                entry.read_to_string(&mut content)?;
                return Ok(serde_json::from_str(&content)?);
            }
        }

        Err(anyhow!("psp.json not found in metadata"))
    }

    // 🔍 Check if data is a tar archive
    /// Detects if the given data is a tar archive by checking for:
    /// 1. "ustar" magic at offset 257 (POSIX tar format)
    /// 2. ASCII-printable characters in the name field
    /// 3. Valid tar structure (as a fallback test)
    fn is_tarball(&self, data: &[u8]) -> bool {
        // Check for tar magic header (ustar)
        if data.len() >= 512 {
            // Check for ustar magic at offset 257
            if data.len() > 262 && &data[257..262] == b"ustar" {
                return true;
            }
            // Also check if it looks like a tar header (name field is ASCII)
            let is_ascii = data[..100.min(data.len())].iter()
                .take_while(|&&b| b != 0)
                .all(|&b| b >= 32 && b <= 126);
            
            if is_ascii && data.len() >= 512 {
                // Try to parse as tar to be sure
                let mut tar = Archive::new(&data[..]);
                if tar.entries().is_ok() {
                    return true;
                }
            }
        }
        false
    }
    
    fn extract_slot(&mut self, index: usize, output_dir: &Path) -> Result<PathBuf> {
        let idx = self.read_index()?;

        // Read slot table entry (24 bytes per entry)
        self.file.seek(SeekFrom::Start(idx.slot_table_offset + (index as u64 * 24)))?;
        let mut entry_data = vec![0u8; 24];
        self.file.read_exact(&mut entry_data)?;

        let offset = u64::from_le_bytes(entry_data[0..8].try_into()?);
        let size = u64::from_le_bytes(entry_data[8..16].try_into()?);
        let checksum = u32::from_le_bytes(entry_data[16..20].try_into()?);
        let _encoding = entry_data[20];
        let _purpose = entry_data[21];
        let _lifecycle = entry_data[22];
        let _reserved = entry_data[23];

        // Read slot data
        self.file.seek(SeekFrom::Start(offset))?;
        let mut slot_data = vec![0u8; size as usize];
        self.file.read_exact(&mut slot_data)?;
        
        // Verify checksum of compressed data
        let calculated_checksum = adler::adler32_slice(&slot_data);
        if calculated_checksum != checksum {
            return Err(anyhow!("Slot checksum mismatch: expected {}, got {}", checksum, calculated_checksum));
        }

        // Get metadata to check encoding
        let metadata = self.read_metadata()?;
        let slot_meta = &metadata.slots[index];

        // Decompress if needed
        let decompressed = match slot_meta.encoding.as_str() {
            "gzip" => {
                let mut gz = GzDecoder::new(&slot_data[..]);
                let mut result = Vec::new();
                gz.read_to_end(&mut result)?;
                result
            }
            _ => slot_data,
        };

        // 📦 Check if this is a tarball that needs extraction
        let slot_path = if self.is_tarball(&decompressed) {
            debug!("📦 Slot {} is a tarball, extracting...", index);
            
            // Determine extraction directory
            let extract_dir = if let Some(extract_to) = slot_meta.extract_to.as_ref() {
                if extract_to == "." {
                    output_dir.to_path_buf()
                } else {
                    output_dir.join(extract_to)
                }
            } else {
                output_dir.join(&slot_meta.name)
            };
            
            // 📁 Ensure extraction directory exists
            fs::create_dir_all(&extract_dir)?;
            
            // 📤 Extract tarball
            let mut tar = Archive::new(&decompressed[..]);
            tar.unpack(&extract_dir)?;
            
            extract_dir
        } else {
            // 📄 Single file - write directly
            let slot_path = output_dir.join(&slot_meta.name);
            fs::write(&slot_path, decompressed)?;
            
            // 🔧 Make executable if needed
            if slot_meta.purpose == "executable" || slot_meta.purpose == "tool" {
                #[cfg(unix)]
                {
                    use std::os::unix::fs::PermissionsExt;
                    let mut perms = fs::metadata(&slot_path)?.permissions();
                    perms.set_mode(0o755);
                    fs::set_permissions(&slot_path, perms)?;
                }
            }
            
            slot_path
        };

        Ok(slot_path)
    }
}

// Manual implementation of Copy for PSPFIndex


// CLI command implementations

fn show_bundle_info(exe_path: &Path) -> Result<()> {
    let mut reader = Reader::new(exe_path)?;
    let index = reader.read_index()?;
    let metadata = reader.read_metadata()?;
    
    // Detect launcher type
    let launcher_type = detect_launcher_type(exe_path);
    let builder_type = detect_builder_type(&metadata);
    
    // Calculate encoding info
    let mut total_original = 0i64;
    let mut total_compressed = 0i64;
    let mut encoding_types = std::collections::HashSet::new();
    
    for slot in &metadata.slots {
        total_original += slot.size;
        total_compressed += slot.compressed_size;
        if !slot.encoding.is_empty() && slot.encoding != "none" {
            encoding_types.insert(slot.encoding.clone());
        }
    }
    
    let encoding_info = if encoding_types.is_empty() {
        "none".to_string()
    } else {
        let types: Vec<_> = encoding_types.into_iter().collect();
        if total_original > 0 {
            let ratio = (total_compressed as f64 / total_original as f64) * 100.0;
            format!("{} compressed to {:.0}%", types.join(", "), ratio)
        } else {
            types.join(", ")
        }
    };
    
    // Verify status
    let verify_status = if verify_magic(exe_path).is_ok() { "✓" } else { "✗" };
    
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

fn run_bundle(exe_path: &Path, args: &[String]) -> Result<()> {
    // Simply execute the bundle with the provided arguments
    let mut all_args = vec![exe_path.to_string_lossy().to_string()];
    all_args.extend(args.iter().cloned());
    
    // Unset CLI environment variable and re-execute
    unsafe {
        env::remove_var("FLAVOR_LAUNCHER_CLI");
    }
    
    let status = Command::new(exe_path)
        .args(args)
        .stdin(Stdio::inherit())
        .stdout(Stdio::inherit())
        .stderr(Stdio::inherit())
        .status()?;
    
    std::process::exit(status.code().unwrap_or(1));
}

fn extract_slot(exe_path: &Path, slot_str: &str, output_dir: &str) -> Result<()> {
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

fn show_metadata(exe_path: &Path) -> Result<()> {
    let mut reader = Reader::new(exe_path)?;
    let metadata = reader.read_metadata()?;
    
    let json = serde_json::to_string_pretty(&metadata)?;
    println!("{}", json);
    
    Ok(())
}

fn verify_bundle(exe_path: &Path) -> Result<()> {
    println!("Verifying bundle integrity...");
    
    let mut errors = Vec::new();
    let mut reader = Reader::new(exe_path)?;
    
    // Check magic
    match verify_magic(exe_path) {
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
                match tempfile::tempdir() {
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

fn verify_magic(exe_path: &Path) -> Result<()> {
    let mut file = File::open(exe_path)?;
    let file_size = file.metadata()?.len();
    
    if file_size < 256 + 16 {
        return Err(anyhow!("File too small"));
    }
    
    // Search for PSPF magic starting from the launcher size
    let mut search_start = 0;
    while search_start < file_size.min(MAX_SEARCH_SIZE) {
        file.seek(SeekFrom::Start(search_start))?;
        
        let mut buffer = vec![0u8; 8];
        if file.read_exact(&mut buffer).is_err() {
            break;
        }
        
        if &buffer == PSPF_MAGIC {
            return Ok(());
        }
        
        search_start += 1;
    }
    
    Err(anyhow!("PSPF magic not found"))
}

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
           header.windows(12).any(|w| w == b"runtime.main") {
            return "go".to_string();
        }
    }
    
    "unknown".to_string()
}

fn detect_builder_type(metadata: &Metadata) -> String {
    if let Some(build_info) = &metadata.build {
        return build_info.builder.clone();
    }
    "unknown/pspf-builder".to_string()
}

// 🔍 Check if work environment is valid
/// Validates the work environment by checking if a specific file exists with expected content.
/// This allows skipping redundant setup if the environment is already properly initialized.
fn check_workenv_validity(workenv_dir: &Path, validation: &CacheValidationInfo) -> bool {
    let check_path = validation.check_file
        .replace("{workenv}", workenv_dir.to_str().unwrap());
    
    debug!("🔍 Checking work environment validity: {}", check_path);
    
    match fs::read_to_string(&check_path) {
        Ok(content) => {
            let is_valid = content.trim() == validation.expected_content;
            if is_valid {
                debug!("✅ Work environment validation passed");
            } else {
                debug!("❌ Work environment validation failed: expected '{}', got '{}'", validation.expected_content, content.trim());
            }
            is_valid
        }
        Err(_) => {
            debug!("❌ Work environment validation file not found");
            false
        }
    }
}

// 🔧 Execute setup commands
/// Processes and executes all setup commands required to initialize the work environment.
/// Supports multiple command types:
/// - enumerate_and_execute: Find files matching a pattern and execute a command with them
/// - write_file: Create a file with specified content and permissions
/// - execute: Run a shell command (default for string commands)
/// All commands preserve the user's current working directory.
fn execute_setup_commands(commands: &[Value], workenv_dir: &Path, package: &PackageInfo, user_cwd: &Path) -> Result<()> {
    // 📁 Create metadata directory
    let metadata_dir = workenv_dir.join("metadata");
    fs::create_dir_all(&metadata_dir)?;
    
    for (i, cmd) in commands.iter().enumerate() {
        debug!("🔧 Processing setup command {}", i);
        
        match cmd {
            Value::String(s) => {
                // Legacy string command
                execute_command(s, workenv_dir, package, user_cwd)?;
            }
            Value::Object(map) => {
                let cmd_type = map.get("type").and_then(|v| v.as_str()).unwrap_or("");
                
                match cmd_type {
                    "enumerate_and_execute" => {
                        let command = map.get("command").and_then(|v| v.as_str()).unwrap_or("");
                        let command = substitute_placeholders(command, workenv_dir, package);
                        
                        if let Some(enumerate) = map.get("enumerate").and_then(|v| v.as_object()) {
                            let path = enumerate.get("path").and_then(|v| v.as_str()).unwrap_or("");
                            let pattern = enumerate.get("pattern").and_then(|v| v.as_str()).unwrap_or("");
                            
                            let path = substitute_placeholders(path, workenv_dir, package);
                            let glob_pattern = format!("{}/{}", path, pattern);
                            
                            debug!("📂 Enumerating files: {}", glob_pattern);
                            let files: Vec<_> = glob::glob(&glob_pattern)?
                                .filter_map(Result::ok)
                                .collect();
                            
                            if !files.is_empty() {
                                let parts: Vec<_> = command.split_whitespace().collect();
                                if !parts.is_empty() {
                                    let cmd_name = parts[0];
                                    let mut args: Vec<String> = parts[1..].iter().map(|s| s.to_string()).collect();
                                    let file_count = files.len();
                                    for file in files {
                                        args.push(file.to_string_lossy().to_string());
                                    }
                                    
                                    info!("🚀 Executing: {} with {} files", cmd_name, file_count);
                                    let args_refs: Vec<&str> = args.iter().map(|s| s.as_str()).collect();
                                    run_command(cmd_name, &args_refs, workenv_dir, user_cwd)?;
                                }
                            }
                        }
                    }
                    "write_file" => {
                        let path = map.get("path").and_then(|v| v.as_str()).unwrap_or("");
                        let content = map.get("content").and_then(|v| v.as_str()).unwrap_or("");
                        let mode = map.get("mode").and_then(|v| v.as_u64()).unwrap_or(0o644) as u32;
                        
                        let path = substitute_placeholders(path, workenv_dir, package);
                        let content = substitute_placeholders(content, workenv_dir, package);
                        
                        debug!("📝 Writing file: {} (mode: {:o})", path, mode);
                        
                        // Ensure parent directory exists
                        if let Some(parent) = Path::new(&path).parent() {
                            fs::create_dir_all(parent)?;
                        }
                        
                        let mut file = File::create(&path)?;
                        writeln!(file, "{}", content)?;
                        
                        // Set permissions
                        #[cfg(unix)]
                        {
                            let permissions = fs::Permissions::from_mode(mode);
                            fs::set_permissions(&path, permissions)?;
                        }
                    }
                    _ => {
                        let command = map.get("command").and_then(|v| v.as_str()).unwrap_or("");
                        execute_command(command, workenv_dir, package, user_cwd)?;
                    }
                }
            }
            _ => {
                warn!("⚠️ Unknown setup command type");
            }
        }
    }
    
    Ok(())
}

// 🔄 Substitute placeholders
/// Replaces template placeholders in text with actual values.
/// Supported placeholders:
/// - {workenv}: Path to the work environment directory
/// - {package_name}: Name of the package
/// - {version}: Version of the package
fn substitute_placeholders(text: &str, workenv_dir: &Path, package: &PackageInfo) -> String {
    text.replace("{workenv}", workenv_dir.to_str().unwrap())
        .replace("{package_name}", &package.name)
        .replace("{version}", &package.version)
}

// 🚀 Execute a command
/// Executes a single command string after substituting placeholders.
/// The command is split on whitespace to separate the executable from arguments.
/// Preserves the user's current working directory.
fn execute_command(command: &str, workenv_dir: &Path, package: &PackageInfo, user_cwd: &Path) -> Result<()> {
    let command = substitute_placeholders(command, workenv_dir, package);
    let parts: Vec<_> = command.split_whitespace().collect();
    
    if parts.is_empty() {
        return Ok(());
    }
    
    run_command(parts[0], &parts[1..], workenv_dir, user_cwd)
}

/// Process runtime environment operations in order:
/// 1. unset - Remove specified variables
/// 2. map - Map/rename variables  
/// 3. set - Set specific values
/// 4. pass - Verify required variables exist
fn process_runtime_env(env_map: &mut std::collections::HashMap<String, String>, runtime_env: &RuntimeEnv) {
    // 1. Process unset operations
    if let Some(unset_list) = &runtime_env.unset {
        debug!("🗑️ Processing unset operations: count={}", unset_list.len());
        for key in unset_list {
            if env_map.remove(key).is_some() {
                trace!("🗑️ Unset env var: {}", key);
            }
        }
    }
    
    // 2. Process map operations
    if let Some(map_ops) = &runtime_env.map {
        debug!("🔄 Processing map operations: count={}", map_ops.len());
        for (from, to) in map_ops {
            if let Some(value) = env_map.remove(from) {
                env_map.insert(to.clone(), value.clone());
                trace!("🔄 Mapped env var: {} -> {} = {}", from, to, value);
            }
        }
    }
    
    // 3. Process set operations
    if let Some(set_ops) = &runtime_env.set {
        debug!("✏️ Processing set operations: count={}", set_ops.len());
        for (key, value) in set_ops {
            env_map.insert(key.clone(), value.clone());
            trace!("✏️ Set env var: {} = {}", key, value);
        }
    }
    
    // 4. Process pass operations (verify required variables exist)
    if let Some(pass_list) = &runtime_env.pass {
        debug!("✅ Processing pass operations: count={}", pass_list.len());
        for key in pass_list {
            if env_map.contains_key(key) {
                trace!("✅ Verified env var exists: {}", key);
            } else {
                warn!("⚠️ Required environment variable not found: {}", key);
            }
        }
    }
}

// 🏃 Run a command with arguments
/// Executes a command with the given arguments in the user's working directory.
/// Sets up the environment with:
/// - FLAVOR_WORKENV pointing to the work environment
/// - PATH prepended with {workenv}/bin for access to installed tools
/// Returns an error if the command fails to execute or returns non-zero exit code.
fn run_command(cmd: &str, args: &[&str], workenv_dir: &Path, user_cwd: &Path) -> Result<()> {
    debug!("🏃 Running: {} {:?} in {:?}", cmd, args, user_cwd);
    
    let mut command = Command::new(cmd);
    command.args(args);
    
    // 📂 Set working directory to user's directory
    command.current_dir(user_cwd);
    
    // 🌍 CRITICAL: Inherit all parent environment variables
    for (key, value) in env::vars() {
        command.env(&key, &value);
    }
    
    // 🌍 Override/add FLAVOR_WORKENV environment variable
    command.env("FLAVOR_WORKENV", workenv_dir);
    
    // 📍 Prepend workenv/bin to PATH
    if let Ok(path) = env::var("PATH") {
        let new_path = format!("{}/bin:{}", workenv_dir.to_str().unwrap(), path);
        command.env("PATH", new_path);
    }
    
    let output = command.output()?;
    
    if !output.status.success() {
        error!("❌ Command failed: {} {:?}", cmd, args);
        error!("📝 stdout: {}", String::from_utf8_lossy(&output.stdout));
        error!("📝 stderr: {}", String::from_utf8_lossy(&output.stderr));
        return Err(anyhow!("Command failed with exit code: {:?}", output.status.code()));
    }
    
    Ok(())
}
