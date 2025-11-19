// helpers/flavor-rs/src/psp/format_2025/backends.rs
// Backend implementations for PSPF bundle access - mmap, file, and stream

use log::{debug, trace};
use memmap2::Mmap;
use std::collections::HashMap;
use std::fs::File;
use std::io::{Read, Seek, SeekFrom};
use std::path::Path;
use std::time::Instant;

use super::defaults::{ACCESS_AUTO, ACCESS_FILE, ACCESS_MMAP, ACCESS_STREAM, DEFAULT_CHUNK_SIZE};
use super::slots::SlotDescriptor;
use crate::exceptions::{FlavorError, Result};

/// Trait for PSPF bundle access backends
pub trait Backend: Send + Sync {
    /// Open the bundle file
    fn open(&mut self, path: &Path) -> Result<()>;

    /// Close the bundle file
    fn close(&mut self) -> Result<()>;

    /// Read data at specific offset
    fn read_at(&mut self, offset: u64, size: usize) -> Result<Vec<u8>>;

    /// Read slot data based on descriptor
    fn read_slot(&mut self, descriptor: &SlotDescriptor) -> Result<Vec<u8>> {
        self.read_at(descriptor.offset, descriptor.size as usize)
    }

    /// Get a view of data without copying (if supported)
    fn view_at(&self, _offset: u64, _size: usize) -> Result<&[u8]> {
        Err(FlavorError::Generic(
            "View not supported by this backend".into(),
        ))
    }
}

/// Memory-mapped file access backend
pub struct MMapBackend {
    file: Option<File>,
    mmap: Option<Mmap>,
    path: Option<std::path::PathBuf>,
}

impl std::fmt::Debug for MMapBackend {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.debug_struct("MMapBackend")
            .field("file", &self.file.as_ref().map(|_| "<File>"))
            .field(
                "mmap",
                &self
                    .mmap
                    .as_ref()
                    .map(|m| format!("<Mmap {} bytes>", m.len())),
            )
            .field("path", &self.path)
            .finish()
    }
}

impl Default for MMapBackend {
    fn default() -> Self {
        Self::new()
    }
}

impl MMapBackend {
    pub fn new() -> Self {
        MMapBackend {
            file: None,
            mmap: None,
            path: None,
        }
    }

    /// Prefetch pages for better performance
    #[cfg(unix)]
    pub fn prefetch(&self, _offset: u64, _size: usize) -> Result<()> {
        // Performance hint removed to avoid unsafe code
        // The OS will handle memory management automatically
        Ok(())
    }

    #[cfg(not(unix))]
    pub fn prefetch(&self, _offset: u64, _size: usize) -> Result<()> {
        // No-op on non-Unix platforms
        Ok(())
    }
}

impl Backend for MMapBackend {
    fn open(&mut self, path: &Path) -> Result<()> {
        let timer = Instant::now();
        let file = File::open(path).map_err(FlavorError::IoError)?;

        let file_size = file.metadata().map_err(FlavorError::IoError)?.len();
        trace!("📂 Opening file for mmap: {} bytes", file_size);

        // Note: Memory mapping removed to avoid unsafe code
        // Using file I/O for safety, with some performance trade-off
        debug!(
            "📁 File backend opened {} ({} bytes) in {:?}",
            path.display(),
            file_size,
            timer.elapsed()
        );

        self.file = Some(file);
        self.mmap = None; // No memory mapping for safety
        self.path = Some(path.to_path_buf());

        Ok(())
    }

    fn close(&mut self) -> Result<()> {
        self.mmap = None;
        self.file = None;
        self.path = None;
        Ok(())
    }

    fn read_at(&mut self, offset: u64, size: usize) -> Result<Vec<u8>> {
        trace!("🔍 Safe file read_at: offset={}, size={}", offset, size);
        if let Some(file) = &mut self.file {
            let timer = Instant::now();
            file.seek(SeekFrom::Start(offset))
                .map_err(FlavorError::IoError)?;

            let mut buffer = vec![0u8; size];
            file.read_exact(&mut buffer).map_err(FlavorError::IoError)?;
            trace!("✅ Safe file read {} bytes in {:?}", size, timer.elapsed());
            Ok(buffer)
        } else {
            Err(FlavorError::Generic("Backend not opened".into()))
        }
    }

    fn view_at(&self, _offset: u64, _size: usize) -> Result<&[u8]> {
        // Zero-copy view not available without memory mapping
        Err(FlavorError::Generic(
            "View not supported by safe file backend".into(),
        ))
    }
}

/// Traditional file I/O backend
pub struct FileBackend {
    file: Option<File>,
    path: Option<std::path::PathBuf>,
    cache: HashMap<(u64, usize), Vec<u8>>,
}

impl std::fmt::Debug for FileBackend {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.debug_struct("FileBackend")
            .field("file", &self.file.as_ref().map(|_| "<File>"))
            .field("path", &self.path)
            .field("cache_entries", &self.cache.len())
            .finish()
    }
}

impl Default for FileBackend {
    fn default() -> Self {
        Self::new()
    }
}

impl FileBackend {
    pub fn new() -> Self {
        FileBackend {
            file: None,
            path: None,
            cache: HashMap::new(),
        }
    }
}

impl Backend for FileBackend {
    fn open(&mut self, path: &Path) -> Result<()> {
        let timer = Instant::now();
        let file = File::open(path).map_err(FlavorError::IoError)?;

        let file_size = file.metadata().map_err(FlavorError::IoError)?.len();
        debug!(
            "📁 File backend opened {} ({} bytes) in {:?}",
            path.display(),
            file_size,
            timer.elapsed()
        );

        self.file = Some(file);
        self.path = Some(path.to_path_buf());
        self.cache.clear();

        Ok(())
    }

    fn close(&mut self) -> Result<()> {
        self.file = None;
        self.path = None;
        self.cache.clear();
        Ok(())
    }

    fn read_at(&mut self, offset: u64, size: usize) -> Result<Vec<u8>> {
        trace!("🗓️ File read_at: offset={}, size={}", offset, size);

        // Check cache first
        let cache_key = (offset, size);
        if let Some(cached) = self.cache.get(&cache_key) {
            trace!("⚡ Cache hit for offset={}, size={}", offset, size);
            return Ok(cached.clone());
        }

        if let Some(file) = &mut self.file {
            let timer = Instant::now();
            file.seek(SeekFrom::Start(offset))
                .map_err(FlavorError::IoError)?;

            let mut buffer = vec![0u8; size];
            file.read_exact(&mut buffer).map_err(FlavorError::IoError)?;
            trace!("✅ File read {} bytes in {:?}", size, timer.elapsed());

            // Cache small reads
            if size <= 4096 {
                self.cache.insert(cache_key, buffer.clone());

                // Limit cache size
                if self.cache.len() > 100 {
                    // Remove oldest entries (simple FIFO)
                    let keys: Vec<_> = self.cache.keys().take(20).cloned().collect();
                    for key in keys {
                        self.cache.remove(&key);
                    }
                }
            }

            Ok(buffer)
        } else {
            Err(FlavorError::Generic("Backend not opened".into()))
        }
    }
}

/// Streaming backend - never loads full slots into memory
pub struct StreamBackend {
    file: Option<File>,
    path: Option<std::path::PathBuf>,
    chunk_size: usize,
}

impl std::fmt::Debug for StreamBackend {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.debug_struct("StreamBackend")
            .field("file", &self.file.as_ref().map(|_| "<File>"))
            .field("path", &self.path)
            .field("chunk_size", &self.chunk_size)
            .finish()
    }
}

impl StreamBackend {
    pub fn new(chunk_size: usize) -> Self {
        StreamBackend {
            file: None,
            path: None,
            chunk_size,
        }
    }

    pub fn with_default_chunk_size() -> Self {
        Self::new(DEFAULT_CHUNK_SIZE)
    }

    /// Stream slot data in chunks
    pub fn stream_slot<'a>(
        &'a mut self,
        descriptor: &SlotDescriptor,
    ) -> impl Iterator<Item = Result<Vec<u8>>> + 'a {
        let mut offset = descriptor.offset;
        let mut remaining = descriptor.size;
        let chunk_size = self.chunk_size;

        std::iter::from_fn(move || {
            if remaining == 0 {
                return None;
            }

            let to_read = std::cmp::min(chunk_size as u64, remaining) as usize;
            let result = self.read_at(offset, to_read);

            if result.is_ok() {
                offset += to_read as u64;
                remaining -= to_read as u64;
            }

            Some(result)
        })
    }
}

impl Backend for StreamBackend {
    fn open(&mut self, path: &Path) -> Result<()> {
        let file = File::open(path).map_err(FlavorError::IoError)?;

        self.file = Some(file);
        self.path = Some(path.to_path_buf());

        Ok(())
    }

    fn close(&mut self) -> Result<()> {
        self.file = None;
        self.path = None;
        Ok(())
    }

    fn read_at(&mut self, offset: u64, size: usize) -> Result<Vec<u8>> {
        if let Some(file) = &mut self.file {
            // Limit read size for streaming
            let read_size = std::cmp::min(size, self.chunk_size);

            file.seek(SeekFrom::Start(offset))
                .map_err(FlavorError::IoError)?;

            let mut buffer = vec![0u8; read_size];
            file.read_exact(&mut buffer).map_err(FlavorError::IoError)?;

            Ok(buffer)
        } else {
            Err(FlavorError::Generic("Backend not opened".into()))
        }
    }

    fn read_slot(&mut self, descriptor: &SlotDescriptor) -> Result<Vec<u8>> {
        // For streaming, only read first chunk
        let size = std::cmp::min(descriptor.size as usize, self.chunk_size);
        self.read_at(descriptor.offset, size)
    }
}

/// Hybrid backend - uses mmap for index/metadata, file I/O for slots
pub struct HybridBackend {
    file: Option<File>,
    header_mmap: Option<Mmap>,
    path: Option<std::path::PathBuf>,
    header_size: usize,
}

impl std::fmt::Debug for HybridBackend {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.debug_struct("HybridBackend")
            .field("file", &self.file.as_ref().map(|_| "<File>"))
            .field(
                "header_mmap",
                &self
                    .header_mmap
                    .as_ref()
                    .map(|m| format!("<Mmap {} bytes>", m.len())),
            )
            .field("path", &self.path)
            .field("header_size", &self.header_size)
            .finish()
    }
}

impl HybridBackend {
    pub fn new(header_size: usize) -> Self {
        HybridBackend {
            file: None,
            header_mmap: None,
            path: None,
            header_size,
        }
    }

    pub fn with_default_header_size() -> Self {
        Self::new(1024 * 1024) // 1MB default
    }
}

impl Backend for HybridBackend {
    fn open(&mut self, path: &Path) -> Result<()> {
        let file = File::open(path).map_err(FlavorError::IoError)?;

        // Get file size
        let metadata = file.metadata().map_err(FlavorError::IoError)?;
        let _file_size = metadata.len() as usize;

        // Note: Header memory mapping removed to avoid unsafe code
        // Using file I/O for all operations

        self.file = Some(file);
        self.header_mmap = None; // No memory mapping for safety
        self.path = Some(path.to_path_buf());

        Ok(())
    }

    fn close(&mut self) -> Result<()> {
        self.header_mmap = None;
        self.file = None;
        self.path = None;
        Ok(())
    }

    fn read_at(&mut self, offset: u64, size: usize) -> Result<Vec<u8>> {
        // Use safe file I/O for all operations
        if let Some(file) = &mut self.file {
            file.seek(SeekFrom::Start(offset))
                .map_err(FlavorError::IoError)?;

            let mut buffer = vec![0u8; size];
            file.read_exact(&mut buffer).map_err(FlavorError::IoError)?;

            Ok(buffer)
        } else {
            Err(FlavorError::Generic("Backend not opened".into()))
        }
    }

    fn view_at(&self, _offset: u64, _size: usize) -> Result<&[u8]> {
        // Zero-copy view not available without memory mapping
        Err(FlavorError::Generic(
            "View not available in safe file backend".into(),
        ))
    }
}

/// Factory function to create the appropriate backend
pub fn create_backend(mode: u8, path: Option<&Path>) -> Box<dyn Backend> {
    let mut mode = mode;

    if mode == ACCESS_AUTO {
        // Auto-select based on file size and platform
        if let Some(p) = path {
            if let Ok(metadata) = std::fs::metadata(p) {
                let file_size = metadata.len();

                // Use mmap for files over 1MB
                if file_size > 1024 * 1024 {
                    mode = ACCESS_MMAP;
                // Use streaming for very large files
                } else if file_size > 100 * 1024 * 1024 {
                    mode = ACCESS_STREAM;
                } else {
                    mode = ACCESS_FILE;
                }
            } else {
                mode = ACCESS_FILE;
            }
        } else {
            mode = ACCESS_FILE;
        }
    }

    // Create the appropriate backend
    match mode {
        ACCESS_MMAP => Box::new(MMapBackend::new()),
        ACCESS_STREAM => Box::new(StreamBackend::with_default_chunk_size()),
        ACCESS_FILE => Box::new(FileBackend::new()),
        _ => Box::new(HybridBackend::with_default_header_size()),
    }
}

// 📦💾🗺️🪄
