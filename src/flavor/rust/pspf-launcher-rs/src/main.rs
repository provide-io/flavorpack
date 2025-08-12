use anyhow::{anyhow, Context, Result};
use flate2::read::GzDecoder;
use serde::Deserialize;
use std::env;
use std::fs::{self, File};
use std::io::{Read, Seek, SeekFrom};
use std::path::{Path, PathBuf};
use std::process::{Command, Stdio};
use tar::Archive;
use tempfile::TempDir;

const PSPF_MAGIC: &[u8] = b"PSPF2025";
const INDEX_SIZE: u64 = 256;
const MAX_SEARCH_SIZE: u64 = 10 * 1024 * 1024; // 10MB

#[repr(C, packed)]
struct PSPFIndex {
    format_magic: [u8; 8],        // "PSPF2025"
    format_version: u32,           // 0x20250001
    index_checksum: u32,           // Adler-32 of index block
    package_size: u64,             // Total file size
    launcher_size: u64,            // Size of launcher binary
    metadata_offset: u64,          // Offset to metadata archive
    metadata_size: u64,            // Size of metadata archive
    slot_table_offset: u64,        // Offset to slot table
    slot_table_size: u64,          // Size of slot table
    slot_count: u32,               // Number of slots
    flags: u32,                    // Feature flags
    ephemeral_public_key: [u8; 32], // Ephemeral public key
    metadata_checksum: [u8; 32],   // SHA256 of metadata
    reserved: [u8; 120],           // Reserved for future use
}

#[derive(Debug, Deserialize)]
struct Metadata {
    format: String,
    package: PackageInfo,
    slots: Vec<SlotMetadata>,
    execution: ExecutionInfo,
}

#[derive(Debug, Deserialize)]
struct PackageInfo {
    name: String,
    version: String,
}

#[derive(Debug, Deserialize)]
struct SlotMetadata {
    index: usize,
    name: String,
    size: i64,
    compressed_size: i64,
    checksum: String,
    compression: String,
    purpose: String,
    lifecycle: String,
}

#[derive(Debug, Deserialize)]
struct ExecutionInfo {
    primary_slot: usize,
    command: String,
    #[serde(default)]
    environment: std::collections::HashMap<String, String>,
}

fn main() -> Result<()> {
    // Check if CLI mode is enabled
    if env::var("PSPF_CLI_ENABLED").unwrap_or_default() == "true" {
        eprintln!("PSPF CLI mode not yet implemented");
        std::process::exit(1);
    }

    // Get the path to our own executable
    let exe_path = env::current_exe()
        .context("Failed to get executable path")?;

    // Create reader for our bundle
    let mut reader = Reader::new(&exe_path)?;

    // Read metadata
    let metadata = reader.read_metadata()?;

    // Create cache directory
    let cache_dir = TempDir::new_in(env::temp_dir())
        .context("Failed to create cache directory")?;

    // Extract all slots
    let mut slot_paths = std::collections::HashMap::new();
    for (i, slot) in metadata.slots.iter().enumerate() {
        let slot_path = reader.extract_slot(i, &cache_dir)?;
        slot_paths.insert(slot.index, slot_path);
    }

    // Prepare execution
    let mut command = metadata.execution.command.clone();
    
    // Substitute slot references in command
    for (idx, path) in &slot_paths {
        let placeholder = format!("{{slot:{}}}", idx);
        command = command.replace(&placeholder, path.to_str().unwrap());
    }

    // Parse command
    let parts: Vec<&str> = command.split_whitespace().collect();
    if parts.is_empty() {
        return Err(anyhow!("Empty command"));
    }

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

    // Set environment
    for (k, mut v) in metadata.execution.environment {
        // Substitute slot references
        for (idx, path) in &slot_paths {
            let placeholder = format!("{{slot:{}}}", idx);
            v = v.replace(&placeholder, path.to_str().unwrap());
        }
        cmd.env(k, v);
    }

    // Set working directory to primary slot if specified
    if let Some(primary_path) = slot_paths.get(&metadata.execution.primary_slot) {
        if let Some(parent) = primary_path.parent() {
            cmd.current_dir(parent);
        }
    }

    // Connect stdio
    cmd.stdin(Stdio::inherit())
        .stdout(Stdio::inherit())
        .stderr(Stdio::inherit());

    // Execute
    let status = cmd.status()
        .context("Failed to execute command")?;

    // Exit with same code
    std::process::exit(status.code().unwrap_or(1));
}

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

    fn extract_slot(&mut self, index: usize, cache_dir: &TempDir) -> Result<PathBuf> {
        let idx = self.read_index()?;

        // Read slot table entry
        self.file.seek(SeekFrom::Start(idx.slot_table_offset + (index as u64 * 20)))?;
        let mut entry_data = vec![0u8; 20];
        self.file.read_exact(&mut entry_data)?;

        let offset = u64::from_le_bytes(entry_data[0..8].try_into()?);
        let size = u64::from_le_bytes(entry_data[8..16].try_into()?);
        let _checksum = u32::from_le_bytes(entry_data[16..20].try_into()?);

        // Read slot data
        self.file.seek(SeekFrom::Start(offset))?;
        let mut slot_data = vec![0u8; size as usize];
        self.file.read_exact(&mut slot_data)?;

        // Get metadata to check compression
        let metadata = self.read_metadata()?;
        let slot_meta = &metadata.slots[index];

        // Decompress if needed
        let decompressed = match slot_meta.compression.as_str() {
            "gzip" => {
                let mut gz = GzDecoder::new(&slot_data[..]);
                let mut result = Vec::new();
                gz.read_to_end(&mut result)?;
                result
            }
            _ => slot_data,
        };

        // Write to cache
        let slot_path = cache_dir.path().join(&slot_meta.name);
        fs::write(&slot_path, decompressed)?;

        // Make executable if needed
        if slot_meta.purpose == "executable" {
            #[cfg(unix)]
            {
                use std::os::unix::fs::PermissionsExt;
                let mut perms = fs::metadata(&slot_path)?.permissions();
                perms.set_mode(0o755);
                fs::set_permissions(&slot_path, perms)?;
            }
        }

        Ok(slot_path)
    }
}

// Manual implementation of Copy for PSPFIndex
impl Copy for PSPFIndex {}

impl Clone for PSPFIndex {
    fn clone(&self) -> Self {
        *self
    }
}