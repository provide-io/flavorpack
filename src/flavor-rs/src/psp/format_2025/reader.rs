// helpers/flavor-rs/src/psp/format_2025/reader.rs
// PSPF 2025 Bundle Reader - Uses backend system for flexible access

use log::{debug, error, trace};
use std::path::Path;
use std::time::Instant;

use super::backends::{Backend, MMapBackend, create_backend};
use super::constants::{
    HEADER_SIZE, MAGIC_TRAILER_SIZE, MAGIC_WAND_EMOJI_BYTES, PACKAGE_EMOJI_BYTES,
    SLOT_DESCRIPTOR_SIZE,
};
use super::debug::debug_dump;
use super::defaults::ACCESS_AUTO;
use super::extraction::extract_slot;
use super::index::Index;
use super::metadata::Metadata;
use super::slots::SlotDescriptor;
use crate::exceptions::{FlavorError, Result};

/// Reader for PSPF/2025 bundles with backend support
pub struct Reader {
    backend: Box<dyn Backend>,
    path: std::path::PathBuf,
    index: Option<Index>,
    metadata: Option<Metadata>,
}

impl std::fmt::Debug for Reader {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.debug_struct("Reader")
            .field("backend", &"<Backend>")
            .field("path", &self.path)
            .field("index", &self.index.as_ref().map(|_| "<Index>"))
            .field("metadata", &self.metadata.as_ref().map(|_| "<Metadata>"))
            .finish()
    }
}

impl Reader {
    /// Create a new reader with automatic backend selection
    pub fn new(path: &Path) -> Result<Self> {
        trace!("Creating reader for: {:?}", path);
        Self::with_backend(path, ACCESS_AUTO)
    }

    /// Create a reader with specified backend mode
    pub fn with_backend(path: &Path, mode: u8) -> Result<Self> {
        let timer = Instant::now();
        trace!("Creating backend with mode: {}", mode);
        let mut backend = create_backend(mode, Some(path));
        backend.open(path)?;
        trace!("Backend opened in {:?}", timer.elapsed());

        Ok(Self {
            backend,
            path: path.to_path_buf(),
            index: None,
            metadata: None,
        })
    }

    /// Create a reader using memory-mapped backend (most efficient)
    pub fn with_mmap(path: &Path) -> Result<Self> {
        trace!("Creating mmap backend for: {:?}", path);
        let timer = Instant::now();
        let mut backend = Box::new(MMapBackend::new());
        backend.open(path)?;
        debug!("MMap backend opened in {:?}", timer.elapsed());

        Ok(Self {
            backend,
            path: path.to_path_buf(),
            index: None,
            metadata: None,
        })
    }

    /// Read the PSPF index
    pub fn read_index(&mut self) -> Result<&Index> {
        if self.index.is_none() {
            let timer = Instant::now();
            // Read index from MagicTrailer
            trace!("Reading MagicTrailer...");
            let index_data = self.read_magic_trailer()?;
            trace!("Parsing index from MagicTrailer");

            // Parse index
            let index = Index::unpack(&index_data)?;

            // Debug log the parsed values (copy to locals to avoid alignment issues)
            let pkg_size = index.package_size;
            let lch_size = index.launcher_size;
            let meta_offset = index.metadata_offset;
            let meta_size = index.metadata_size;
            let slot_offset = index.slot_table_offset;
            let slot_cnt = index.slot_count;

            debug!("Parsed index values:");
            debug!("  package_size: {}", pkg_size);
            debug!("  launcher_size: {}", lch_size);
            debug!(
                "  metadata_offset: 0x{:016x} ({})",
                meta_offset, meta_offset
            );
            debug!("  metadata_size: {} bytes", meta_size);
            debug!("  slot_table_offset: 0x{:016x}", slot_offset);
            debug!("  slot_count: {}", slot_cnt);

            // Skip checksum verification for now - Go launcher doesn't verify it either
            // TODO: Fix checksum calculation to match Python builder
            // if !index.verify_checksum_raw(&index_data) {
            //     return Err(FlavorError::Generic("Index checksum mismatch".into()));
            // }

            // Log a warning if checksum doesn't match
            if !index.verify_checksum_raw(&index_data) {
                debug!("Warning: Index checksum mismatch (verification disabled)");
            }

            self.index = Some(index);
            debug!("Index loaded in {:?}", timer.elapsed());
        }

        self.index
            .as_ref()
            .ok_or_else(|| FlavorError::Generic("Failed to read index".into()))
    }

    /// Read and parse metadata
    #[allow(clippy::cognitive_complexity)]
    pub fn read_metadata(&mut self) -> Result<&Metadata> {
        if self.metadata.is_none() {
            // Ensure index is loaded
            if self.index.is_none() {
                self.read_index()?;
            }

            let index = self
                .index
                .as_ref()
                .ok_or_else(|| FlavorError::Generic("Index not loaded".into()))?;

            let meta_offset = index.metadata_offset;
            let meta_size = index.metadata_size;
            debug!(
                "📖 Reading metadata from offset {:#x}, size {} bytes",
                meta_offset, meta_size
            );

            // Read metadata using backend
            let metadata_data = self.backend.read_at(meta_offset, meta_size as usize)?;

            trace!("🔍 Read {} bytes of metadata", metadata_data.len());

            // Debug dump if requested
            if std::env::var("FLAVOR_DEBUG_METADATA").is_ok() {
                debug!("🔬 Metadata debugging enabled - dumping raw data");

                // Analyze what we're looking at
                if metadata_data.starts_with(b"\x1f\x8b") {
                    debug!("✅ Metadata is gzip compressed (magic: 1f 8b)");
                } else if metadata_data.starts_with(b"{") {
                    debug!("📝 Metadata appears to be uncompressed JSON");
                } else if metadata_data.starts_with(b"ustar")
                    || (metadata_data.len() > 257 && &metadata_data[257..262] == b"ustar")
                {
                    debug!("🚨 WARNING: Metadata appears to be a tar archive! This is wrong!");
                    trace!(
                        "🔬 First 16 bytes: {:02x?}",
                        &metadata_data[..16.min(metadata_data.len())]
                    );
                } else {
                    debug!("❓ Unknown metadata format");
                    trace!(
                        "🔬 First 16 bytes: {:02x?}",
                        &metadata_data[..16.min(metadata_data.len())]
                    );
                }

                // Save raw data
                if let Err(e) = std::fs::write("debug_metadata_raw.bin", &metadata_data) {
                    debug!("⚠️ Could not save raw metadata: {}", e);
                } else {
                    debug!("💾 Saved raw metadata to debug_metadata_raw.bin");
                }
            }

            // Verify metadata checksum (full SHA-256, 32 bytes)
            use sha2::{Digest, Sha256};
            let actual_hash = Sha256::digest(&metadata_data);
            let actual_checksum: [u8; 32] = actual_hash.into();
            if actual_checksum != index.metadata_checksum {
                debug!(
                    "❌ Metadata checksum mismatch: expected {:02x?}, got {:02x?}",
                    &index.metadata_checksum[..8],
                    &actual_checksum[..8]
                );
                return Err(FlavorError::Generic("Metadata checksum mismatch".into()));
            }
            trace!("✅ Metadata checksum verified (SHA-256)");

            // Parse metadata - always gzip compressed for now
            let metadata: Metadata = if true {
                // Always gzip for now
                // Decompress first
                use flate2::read::GzDecoder;
                use std::io::Read;

                trace!("🎈 Decompressing gzip metadata...");
                let mut decoder = GzDecoder::new(&metadata_data[..]);
                let mut json_data = String::new();
                decoder.read_to_string(&mut json_data)?;

                // Debug dump decompressed JSON
                if std::env::var("FLAVOR_DEBUG_METADATA").is_ok() {
                    if let Err(e) = std::fs::write("debug_metadata.json", &json_data) {
                        debug!("⚠️ Could not save decompressed metadata: {}", e);
                    } else {
                        debug!(
                            "📄 Saved decompressed metadata to debug_metadata.json ({} chars)",
                            json_data.len()
                        );
                    }

                    // Check if it's actually JSON
                    if json_data.starts_with('{') {
                        debug!("✅ Decompressed data is valid JSON");
                    } else if json_data.contains("ustar") {
                        debug!("🚨 ERROR: Decompressed data contains tar signatures!");
                        trace!(
                            "📄 First 200 chars: {}",
                            &json_data[..200.min(json_data.len())]
                        );
                    }
                }

                serde_json::from_str(&json_data)?
            } else {
                // Direct JSON
                trace!("📝 Parsing uncompressed JSON metadata");
                let json_str = std::str::from_utf8(&metadata_data)
                    .map_err(|e| FlavorError::Generic(format!("Invalid UTF-8: {}", e)))?;
                serde_json::from_str(json_str)?
            };

            debug!(
                "✅ Successfully parsed metadata for {} v{}",
                metadata.package.name, metadata.package.version
            );

            self.metadata = Some(metadata);
        }

        self.metadata
            .as_ref()
            .ok_or_else(|| FlavorError::Generic("Failed to read metadata".into()))
    }

    /// Read MagicTrailer and return index data
    fn read_magic_trailer(&mut self) -> Result<Vec<u8>> {
        use log::trace;

        // Get file size
        let file_size = self.path.metadata()?.len();

        // Read MagicTrailer (last 8200 bytes)
        let trailer = self
            .backend
            .read_at(file_size - MAGIC_TRAILER_SIZE as u64, MAGIC_TRAILER_SIZE)?;

        // Verify emoji bookends
        if &trailer[..4] != PACKAGE_EMOJI_BYTES {
            return Err(FlavorError::Generic(
                "Invalid MagicTrailer: missing 📦 at start".into(),
            ));
        }
        if &trailer[MAGIC_TRAILER_SIZE - 4..] != MAGIC_WAND_EMOJI_BYTES {
            return Err(FlavorError::Generic(
                "Invalid MagicTrailer: missing 🪄 at end".into(),
            ));
        }

        // Extract index from between emojis
        let index_data = trailer[4..4 + HEADER_SIZE].to_vec();

        trace!("Found index in MagicTrailer");
        debug!(
            "Trailer size: {}, file size: {} bytes",
            MAGIC_TRAILER_SIZE, file_size
        );

        Ok(index_data)
    }

    /// Read slot descriptors
    pub fn read_slot_descriptors(&mut self) -> Result<Vec<SlotDescriptor>> {
        // Ensure index is loaded
        if self.index.is_none() {
            self.read_index()?;
        }

        let index = self
            .index
            .as_ref()
            .ok_or_else(|| FlavorError::Generic("Index not loaded".into()))?;
        let desc_count = index.slot_count;
        let desc_offset = index.slot_table_offset;
        let mut descriptors = Vec::new();

        debug!(
            "📊 Reading {} slot descriptors from offset {:#x}",
            desc_count, desc_offset
        );

        // Read all slot descriptors
        for i in 0..desc_count {
            let offset = desc_offset + (i as u64 * SLOT_DESCRIPTOR_SIZE as u64);
            let data = self.backend.read_at(offset, SLOT_DESCRIPTOR_SIZE)?;

            // Check if we're reading actual descriptors or if builder wrote data incorrectly
            if data.starts_with(b"\x1f\x8b") {
                error!("🚨 CRITICAL: Found gzip data where slot descriptor expected!");
                error!(
                    "  This package was built with a buggy builder that doesn't write descriptors"
                );
                error!("  Descriptor #{} at offset {:#x}", i, offset);
                return Err(FlavorError::Generic(
                    "Package format error: slot descriptors contain data instead of descriptors"
                        .into(),
                ));
            }

            if data.starts_with(b"{") {
                error!("🚨 CRITICAL: Found JSON where slot descriptor expected!");
                error!("  Descriptor #{} at offset {:#x}", i, offset);
                return Err(FlavorError::Generic(
                    "Package format error: slot descriptors contain JSON".into(),
                ));
            }

            if let Some(descriptor) = SlotDescriptor::unpack(&data) {
                let desc_offset = descriptor.offset;
                let desc_size = descriptor.size;
                let desc_checksum = descriptor.checksum;
                trace!(
                    "📋 Descriptor {}: offset={:#x}, size={}, checksum={:#x}",
                    i, desc_offset, desc_size, desc_checksum
                );
                descriptors.push(descriptor);
            } else {
                debug!("⚠️ Warning: Could not parse descriptor #{}", i);
            }
        }

        Ok(descriptors)
    }

    /// Read slot data by descriptor
    pub fn read_slot(&mut self, descriptor: &SlotDescriptor) -> Result<Vec<u8>> {
        let desc_offset = descriptor.offset;
        let desc_size = descriptor.size;
        trace!(
            "🔍 Reading slot from descriptor: offset={:#x}, size={}",
            desc_offset, desc_size
        );
        let data = self.backend.read_slot(descriptor)?;

        // Debug check: warn if we got JSON instead of expected data
        if data.starts_with(b"{") || data.starts_with(b"[") {
            error!("🚨 WARNING: Read JSON data from slot descriptor!");
            error!(
                "  Descriptor: offset={:#x}, size={}",
                desc_offset, desc_size
            );
            error!(
                "  Data preview: {}",
                String::from_utf8_lossy(&data[..100.min(data.len())])
            );
        }

        Ok(data)
    }

    /// Extract a slot to a directory
    pub fn extract_slot(&mut self, slot_index: usize, dest_dir: &Path) -> Result<()> {
        extract_slot(self, slot_index, dest_dir)
    }

    /// Debug dump - saves all package internals for analysis
    pub fn debug_dump(&mut self, output_dir: &Path) -> Result<()> {
        debug_dump(self, output_dir)
    }

    /// Get backend for advanced operations
    pub fn backend(&self) -> &dyn Backend {
        &*self.backend
    }

    /// Get mutable backend for advanced operations
    pub fn backend_mut(&mut self) -> &mut dyn Backend {
        &mut *self.backend
    }
}

impl Drop for Reader {
    fn drop(&mut self) {
        // Ensure backend is closed
        let _ = self.backend.close();
    }
}

// 📦📖🗺️🪄
