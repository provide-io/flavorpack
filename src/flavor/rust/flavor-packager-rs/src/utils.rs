//
// flavor/rust/flavor-packager-rs/src/utils.rs
//
use anyhow::{Context, Result};
use flate2::write::GzEncoder;
use flate2::Compression;
use std::fs::{self, File};
use std::io::{self, Read, Write};
use std::path::Path;
use tar::Builder;

pub fn create_tar_gz<P: AsRef<Path>, Q: AsRef<Path>>(
    source_dir: P, 
    output_path: Q
) -> Result<u64> {
    let tar_gz_file = File::create(&output_path)
        .with_context(|| format!("Failed to create tar.gz file: {:?}", output_path.as_ref()))?;
    
    let gz_encoder = GzEncoder::new(tar_gz_file, Compression::best());
    let mut tar_builder = Builder::new(gz_encoder);
    
    // Add the entire directory recursively
    tar_builder.append_dir_all(".", &source_dir)
        .with_context(|| format!("Failed to add directory to tar.gz: {:?}", source_dir.as_ref()))?;
    
    let gz_encoder = tar_builder.into_inner()
        .context("Failed to finalize tar archive")?;
    
    let tar_gz_file = gz_encoder.finish()
        .context("Failed to finalize gz compression")?;
    
    let file_size = tar_gz_file.metadata()?.len();
    
    log::info!(
        "Created tar.gz: {:?} ({} bytes)", 
        output_path.as_ref(), 
        file_size
    );
    
    Ok(file_size)
}

pub fn copy_file<P: AsRef<Path>, Q: AsRef<Path>>(
    source: P, 
    dest: Q
) -> Result<u64> {
    let bytes_copied = fs::copy(&source, &dest)
        .with_context(|| {
            format!(
                "Failed to copy file from {:?} to {:?}", 
                source.as_ref(), 
                dest.as_ref()
            )
        })?;
    
    log::debug!(
        "Copied file: {:?} -> {:?} ({} bytes)",
        source.as_ref(),
        dest.as_ref(),
        bytes_copied
    );
    
    Ok(bytes_copied)
}

pub fn read_file_bytes<P: AsRef<Path>>(path: P) -> Result<Vec<u8>> {
    fs::read(&path)
        .with_context(|| format!("Failed to read file: {:?}", path.as_ref()))
}

pub fn write_file_bytes<P: AsRef<Path>>(path: P, data: &[u8]) -> Result<()> {
    fs::write(&path, data)
        .with_context(|| format!("Failed to write file: {:?}", path.as_ref()))
}

pub fn append_to_file<P: AsRef<Path>>(path: P, data: &[u8]) -> Result<()> {
    let mut file = fs::OpenOptions::new()
        .create(true)
        .append(true)
        .open(&path)
        .with_context(|| format!("Failed to open file for appending: {:?}", path.as_ref()))?;
    
    file.write_all(data)
        .with_context(|| format!("Failed to append to file: {:?}", path.as_ref()))
}

pub fn get_file_size<P: AsRef<Path>>(path: P) -> Result<u64> {
    let metadata = fs::metadata(&path)
        .with_context(|| format!("Failed to get file metadata: {:?}", path.as_ref()))?;
    
    Ok(metadata.len())
}

pub fn ensure_parent_dir<P: AsRef<Path>>(path: P) -> Result<()> {
    if let Some(parent) = path.as_ref().parent() {
        fs::create_dir_all(parent)
            .with_context(|| format!("Failed to create parent directory: {:?}", parent))?;
    }
    Ok(())
}

/// Copy data from reader to writer and return bytes copied
pub fn copy_with_progress<R: Read, W: Write>(
    mut reader: R,
    mut writer: W,
) -> Result<u64> {
    let mut buffer = [0; 8192];
    let mut total_bytes = 0u64;
    
    loop {
        let bytes_read = reader.read(&mut buffer)?;
        if bytes_read == 0 {
            break;
        }
        
        writer.write_all(&buffer[..bytes_read])?;
        total_bytes += bytes_read as u64;
    }
    
    Ok(total_bytes)
}


// 📦🍜📄🪄
