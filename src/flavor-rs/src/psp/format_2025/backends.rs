// SPDX-FileCopyrightText: Copyright (c) 2026 provide.io llc. All rights reserved.
// SPDX-License-Identifier: Apache-2.0

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

/// Maximum allocation size for a single read (4 GB)
const MAX_SLOT_SIZE: u64 = 4 * 1024 * 1024 * 1024;

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
        let slot_size = descriptor.size;
        if slot_size > MAX_SLOT_SIZE {
            return Err(FlavorError::Generic(format!(
                "Slot size {} exceeds maximum allowed size ({} bytes)",
                slot_size, MAX_SLOT_SIZE
            )));
        }
        let slot_offset = descriptor.offset;
        self.read_at(slot_offset, slot_size as usize)
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
        if size as u64 > MAX_SLOT_SIZE {
            return Err(FlavorError::Generic(format!(
                "Read size {} exceeds maximum allowed ({} bytes)",
                size, MAX_SLOT_SIZE
            )));
        }
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
        if size as u64 > MAX_SLOT_SIZE {
            return Err(FlavorError::Generic(format!(
                "Read size {} exceeds maximum allowed ({} bytes)",
                size, MAX_SLOT_SIZE
            )));
        }

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
        // Read the full slot by assembling chunks so callers (extraction,
        // verification) always receive complete data regardless of chunk_size.
        let total = descriptor.size;
        if total > MAX_SLOT_SIZE {
            return Err(FlavorError::Generic(format!(
                "Slot size {} exceeds maximum allowed size ({} bytes)",
                total, MAX_SLOT_SIZE
            )));
        }
        let mut buf = Vec::with_capacity(total as usize);
        let mut remaining = total;
        let mut offset = descriptor.offset;
        while remaining > 0 {
            let to_read = remaining.min(self.chunk_size as u64) as usize;
            let chunk = self.read_at(offset, to_read)?;
            if chunk.is_empty() {
                return Err(FlavorError::Generic(format!(
                    "Backend returned empty read at offset {:#x} (remaining {})",
                    offset, remaining
                )));
            }
            let n = chunk.len() as u64;
            buf.extend_from_slice(&chunk);
            offset += n;
            remaining -= n;
        }
        Ok(buf)
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
        if size as u64 > MAX_SLOT_SIZE {
            return Err(FlavorError::Generic(format!(
                "Read size {} exceeds maximum allowed ({} bytes)",
                size, MAX_SLOT_SIZE
            )));
        }
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

                // Use streaming for very large files (>100MB)
                if file_size > 100 * 1024 * 1024 {
                    mode = ACCESS_STREAM;
                // Use mmap for files over 1MB
                } else if file_size > 1024 * 1024 {
                    mode = ACCESS_MMAP;
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

#[cfg(test)]
mod tests {
    use super::*;
    use crate::psp::format_2025::defaults::{ACCESS_AUTO, DEFAULT_CHUNK_SIZE};
    use std::fs::{self, File};
    use tempfile::tempdir;

    fn write_temp_file(bytes: &[u8]) -> (tempfile::TempDir, std::path::PathBuf) {
        let dir = tempdir().expect("tempdir");
        let path = dir.path().join("bundle.bin");
        fs::write(&path, bytes).expect("write temp file");
        (dir, path)
    }

    #[test]
    fn file_backend_reads_caches_and_clears_on_close() {
        let (_dir, path) = write_temp_file(b"abcdefghij");
        let mut backend = FileBackend::new();

        backend.open(&path).expect("open");
        let first = backend.read_at(2, 4).expect("first read");
        let second = backend.read_at(2, 4).expect("cached read");

        assert_eq!(first, b"cdef");
        assert_eq!(second, b"cdef");
        assert_eq!(backend.cache.len(), 1);

        backend.close().expect("close");
        assert!(backend.file.is_none());
        assert!(backend.path.is_none());
        assert!(backend.cache.is_empty());
    }

    #[test]
    fn file_backend_evicts_cache_after_many_small_reads() {
        let mut data = Vec::with_capacity(256);
        data.extend((0u8..=255).cycle().take(200));
        let (_dir, path) = write_temp_file(&data);
        let mut backend = FileBackend::new();

        backend.open(&path).expect("open");
        for offset in 0..101u64 {
            let _ = backend.read_at(offset, 1).expect("read");
        }

        assert_eq!(backend.cache.len(), 81);
    }

    #[test]
    fn mmap_backend_reads_file_and_reports_view_error() {
        let (_dir, path) = write_temp_file(b"0123456789");
        let mut backend = MMapBackend::new();

        backend.open(&path).expect("open");
        assert_eq!(backend.read_at(4, 3).expect("read"), b"456");

        let err = backend.view_at(0, 1).expect_err("view should fail");
        assert!(
            matches!(err, FlavorError::Generic(message) if message.contains("safe file backend"))
        );

        backend.close().expect("close");
        assert!(backend.file.is_none());
        assert!(backend.mmap.is_none());
        assert!(backend.path.is_none());
    }

    #[test]
    fn stream_backend_chunks_reads_and_truncates_slot_reads() {
        let (_dir, path) = write_temp_file(b"abcdefghij");
        let mut backend = StreamBackend::new(4);

        backend.open(&path).expect("open");

        let descriptor = SlotDescriptor {
            size: 10,
            offset: 0,
            ..SlotDescriptor::new(1)
        };

        let chunks: Vec<_> = backend
            .stream_slot(&descriptor)
            .map(|chunk| chunk.expect("chunk"))
            .collect();
        assert_eq!(
            chunks,
            vec![b"abcd".to_vec(), b"efgh".to_vec(), b"ij".to_vec()]
        );

        // read_slot assembles all chunks into a complete buffer
        let slot = backend.read_slot(&descriptor).expect("slot read");
        assert_eq!(slot, b"abcdefghij");
    }

    #[test]
    fn hybrid_backend_reads_file_and_reports_view_error() {
        let (_dir, path) = write_temp_file(b"hello world");
        let mut backend = HybridBackend::new(64);

        backend.open(&path).expect("open");
        assert_eq!(backend.read_at(6, 5).expect("read"), b"world");

        let err = backend.view_at(0, 1).expect_err("view should fail");
        assert!(
            matches!(err, FlavorError::Generic(message) if message.contains("safe file backend"))
        );

        backend.close().expect("close");
        assert!(backend.file.is_none());
        assert!(backend.header_mmap.is_none());
        assert!(backend.path.is_none());
    }

    #[test]
    fn create_backend_auto_selects_expected_backends() {
        let (_small_dir, small_path) = write_temp_file(b"tiny");

        let small_backend = create_backend(ACCESS_AUTO, Some(&small_path));
        let small_err = small_backend
            .view_at(0, 1)
            .expect_err("small files should use file backend");
        assert!(
            matches!(small_err, FlavorError::Generic(message) if message == "View not supported by this backend")
        );

        let medium_dir = tempdir().expect("tempdir");
        let medium_path = medium_dir.path().join("medium.bin");
        File::create(&medium_path)
            .expect("create medium file")
            .set_len(2 * 1024 * 1024)
            .expect("set medium len");

        let medium_backend = create_backend(ACCESS_AUTO, Some(&medium_path));
        let medium_err = medium_backend
            .view_at(0, 1)
            .expect_err("medium files should use mmap backend");
        assert!(
            matches!(medium_err, FlavorError::Generic(message) if message.contains("safe file backend"))
        );

        let large_dir = tempdir().expect("tempdir");
        let large_path = large_dir.path().join("large.bin");
        File::create(&large_path)
            .expect("create large file")
            .set_len(101 * 1024 * 1024)
            .expect("set large len");

        let mut large_backend = create_backend(ACCESS_AUTO, Some(&large_path));
        large_backend.open(&large_path).expect("open large backend");
        let large_descriptor = SlotDescriptor {
            size: (DEFAULT_CHUNK_SIZE as u64) + 10,
            offset: 0,
            ..SlotDescriptor::new(2)
        };
        // read_slot returns the full slot (all chunks assembled), not just the first chunk
        let large_slot = large_backend
            .read_slot(&large_descriptor)
            .expect("stream slot");
        assert_eq!(large_slot.len(), (DEFAULT_CHUNK_SIZE) + 10);
    }

    #[test]
    fn read_slot_rejects_oversized_descriptors() {
        let mut backend = FileBackend::new();
        let descriptor = SlotDescriptor {
            size: MAX_SLOT_SIZE + 1,
            ..SlotDescriptor::new(99)
        };

        let err = backend
            .read_slot(&descriptor)
            .expect_err("oversized slot should fail");
        assert!(
            matches!(err, FlavorError::Generic(message) if message.contains("exceeds maximum allowed size"))
        );
    }
}
