//
// flavor/rust/flavor-packager-rs/src/utils.rs
//
use anyhow::{Context, Result};
use flate2::write::GzEncoder;
use flate2::Compression;
use std::fs::{self, File};
use std::io::{self, Read, Write};
use std::path::{Path, PathBuf};
use std::os::unix::fs::PermissionsExt;
use tar::{Builder, Header, EntryType};

pub fn create_tar_gz<P: AsRef<Path>, Q: AsRef<Path>>(
    source_dir: P, 
    output_path: Q
) -> Result<u64> {
    let tar_gz_file = File::create(&output_path)
        .with_context(|| format!("Failed to create tar.gz file: {:?}", output_path.as_ref()))?;
    
    let gz_encoder = GzEncoder::new(tar_gz_file, Compression::best());
    let mut tar_builder = Builder::new(gz_encoder);
    
    // Add directory and its contents recursively, preserving symlinks
    append_dir_all_with_symlinks(&mut tar_builder, source_dir.as_ref(), "cache")?;
    
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

fn append_dir_all_with_symlinks<W: Write>(
    builder: &mut Builder<W>,
    src_dir: &Path,
    dst_prefix: &str,
) -> Result<()> {
    let src_dir = src_dir.canonicalize()
        .with_context(|| format!("Failed to canonicalize source dir: {:?}", src_dir))?;
    
    append_dir_all_recursive(builder, &src_dir, &src_dir, dst_prefix)
}

fn append_dir_all_recursive<W: Write>(
    builder: &mut Builder<W>,
    base_dir: &Path,
    current_dir: &Path,
    dst_prefix: &str,
) -> Result<()> {
    for entry in fs::read_dir(current_dir)? {
        let entry = entry?;
        let path = entry.path();
        let metadata = fs::symlink_metadata(&path)?;
        
        // Calculate relative path from base directory
        let rel_path = path.strip_prefix(base_dir)
            .with_context(|| format!("Failed to strip prefix from {:?}", path))?;
        
        // Create destination path with prefix
        let dst_path = PathBuf::from(dst_prefix).join(rel_path);
        let dst_path_str = dst_path.to_string_lossy();
        
        if metadata.is_symlink() {
            // Handle symlinks
            let link_target = fs::read_link(&path)?;
            let mut header = Header::new_gnu();
            header.set_path(&dst_path)?;
            header.set_link_name(&link_target)?;
            header.set_entry_type(EntryType::Symlink);
            header.set_size(0);
            header.set_mode(0o777);
            header.set_mtime(metadata.modified()?.duration_since(std::time::UNIX_EPOCH)?.as_secs());
            header.set_cksum();
            
            builder.append(&header, &[][..])
                .with_context(|| format!("Failed to append symlink {:?}", path))?;
                
        } else if metadata.is_dir() {
            // Handle directories
            let mut header = Header::new_gnu();
            header.set_path(&dst_path)?;
            header.set_entry_type(EntryType::Directory);
            header.set_size(0);
            header.set_mode(metadata.permissions().mode());
            header.set_mtime(metadata.modified()?.duration_since(std::time::UNIX_EPOCH)?.as_secs());
            header.set_cksum();
            
            builder.append(&header, &[][..])
                .with_context(|| format!("Failed to append directory {:?}", path))?;
            
            // Recurse into directory
            append_dir_all_recursive(builder, base_dir, &path, dst_prefix)?;
            
        } else if metadata.is_file() {
            // Handle regular files
            let mut header = Header::new_gnu();
            header.set_path(&dst_path)?;
            header.set_size(metadata.len());
            header.set_mode(metadata.permissions().mode());
            header.set_mtime(metadata.modified()?.duration_since(std::time::UNIX_EPOCH)?.as_secs());
            header.set_cksum();
            
            let mut file = File::open(&path)?;
            builder.append(&header, &mut file)
                .with_context(|| format!("Failed to append file {:?}", path))?;
        }
    }
    
    Ok(())
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
