//! PSPF 2025 Format Implementation
//! 
//! This module provides the PSPF 2025 format while maintaining compatibility with v0.1

pub mod spec;
pub mod builder;
pub mod reader;
pub mod launcher;
pub mod errors;

pub use spec::*;
pub use builder::Builder;
pub use reader::Reader;
pub use launcher::Launcher;
pub use errors::{FlavorError, Result};

// Re-export commonly used types
pub use spec::{PSPFIndex, SlotMetadata, Metadata, PackageInfo};

// Format constants
pub const PSPF_MAGIC: &[u8; 8] = b"PSPF2025";
pub const PSPF_VERSION: u32 = 0x20250001;
pub const INDEX_SIZE: usize = 256;
pub const EMOJI_MAGIC_SIZE: usize = 16;
pub const SLOT_ALIGNMENT: u64 = 8;