//! PSPF/2025 format implementation

pub mod backends;
pub mod builder;
pub mod checksums;
pub mod cli;
pub mod constants;
pub mod crypto;
pub mod debug;
pub mod defaults;
pub mod execution;
pub mod extraction;
pub mod index;
pub mod keys;
pub mod launcher;
pub mod locking;
pub mod manifest;
pub mod metadata;
pub mod operations;
pub mod packaging;
pub mod paths;
pub mod pe_resources;
pub mod pe_utils;
pub mod reader;
pub mod runtime;
pub mod slots;
pub mod verifier;

// Re-export main functions
pub use builder::build;
pub use launcher::launch;
pub use verifier::verify;

// Re-export types for advanced usage
pub use index::Index;
pub use metadata::Metadata;
pub use reader::Reader;
pub use slots::SlotDescriptor;
