// helpers/flavor-rs/src/psp/operations/mod.rs
// PSPF/2025 Operation System

pub mod bundle;
pub mod compress;
pub mod chain;
pub mod operation;

pub use chain::{pack_operations, unpack_operations, operations_to_string, string_to_operations};
pub use operation::{Operation, OperationError, OperationResult};

// Re-export operation constants
pub const OP_NONE: u8 = 0x00;

// Bundle operations (0x01-0x0F)
pub const OP_TAR: u8 = 0x01;

// Compression operations (0x10-0x2F)
pub const OP_GZIP: u8 = 0x10;
pub const OP_BZIP2: u8 = 0x13;
pub const OP_XZ: u8 = 0x16;
pub const OP_ZSTD: u8 = 0x1B;