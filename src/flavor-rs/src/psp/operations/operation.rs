// SPDX-FileCopyrightText: Copyright (c) 2026 provide.io llc. All rights reserved.
// SPDX-License-Identifier: Apache-2.0

// helpers/flavor-rs/src/psp/operations/operation.rs
// Base operation trait and types

use std::io::{Read, Write};

pub type OperationResult<T> = Result<T, OperationError>;

#[derive(Debug, thiserror::Error)]
pub enum OperationError {
    #[error("IO error: {0}")]
    Io(#[from] std::io::Error),
    
    #[error("Compression error: {0}")]
    Compression(String),
    
    #[error("Archive error: {0}")]
    Archive(String),
    
    #[error("Operation not reversible")]
    NotReversible,
    
    #[error("Unknown operation: 0x{0:02x}")]
    UnknownOperation(u8),
    
    #[error("Invalid data: {0}")]
    InvalidData(String),
}

/// Trait for all operations
pub trait Operation: Send + Sync {
    /// Returns the operation identifier
    fn id(&self) -> u8;
    
    /// Returns the human-readable name
    fn name(&self) -> &str;
    
    /// Applies the operation to input data
    fn apply(&self, input: &[u8]) -> OperationResult<Vec<u8>>;
    
    /// Applies the operation to a stream
    fn apply_stream(&self, input: &mut dyn Read, output: &mut dyn Write) -> OperationResult<()>;
    
    /// Reverses the operation (e.g., decompress for compression)
    fn reverse(&self, input: &[u8]) -> OperationResult<Vec<u8>>;
    
    /// Reverses the operation on a stream
    fn reverse_stream(&self, input: &mut dyn Read, output: &mut dyn Write) -> OperationResult<()>;
    
    /// Returns true if the operation is reversible
    fn can_reverse(&self) -> bool {
        true
    }
    
    /// Estimates the output size given input size
    fn estimate_size(&self, input_size: u64) -> u64 {
        input_size
    }
}

/// Get operation name by ID
pub fn get_name(id: u8) -> &'static str {
    match id {
        super::OP_NONE => "NONE",
        super::OP_TAR => "TAR",
        super::OP_GZIP => "GZIP",
        super::OP_BZIP2 => "BZIP2",
        super::OP_XZ => "XZ",
        super::OP_ZSTD => "ZSTD",
        _ => "UNKNOWN",
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn get_name_returns_correct_names_for_known_ops() {
        assert_eq!(get_name(super::super::OP_NONE), "NONE");
        assert_eq!(get_name(super::super::OP_TAR), "TAR");
        assert_eq!(get_name(super::super::OP_GZIP), "GZIP");
        assert_eq!(get_name(super::super::OP_BZIP2), "BZIP2");
        assert_eq!(get_name(super::super::OP_XZ), "XZ");
        assert_eq!(get_name(super::super::OP_ZSTD), "ZSTD");
    }

    #[test]
    fn get_name_returns_unknown_for_unrecognized_ops() {
        assert_eq!(get_name(0xFF), "UNKNOWN");
        assert_eq!(get_name(0x50), "UNKNOWN");
    }

    #[test]
    fn operation_error_display_formats_correctly() {
        let io_err = OperationError::Io(std::io::Error::new(
            std::io::ErrorKind::Other,
            "disk full",
        ));
        assert!(io_err.to_string().contains("disk full"));

        let comp_err = OperationError::Compression("bad data".into());
        assert!(comp_err.to_string().contains("bad data"));

        let arch_err = OperationError::Archive("corrupt".into());
        assert!(arch_err.to_string().contains("corrupt"));

        let not_rev = OperationError::NotReversible;
        assert!(not_rev.to_string().contains("not reversible"));

        let unknown = OperationError::UnknownOperation(0xAB);
        assert!(unknown.to_string().contains("0xab"));

        let invalid = OperationError::InvalidData("bad".into());
        assert!(invalid.to_string().contains("bad"));
    }
}