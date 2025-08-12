//! Error types for Flavor PSPF 2025

use std::fmt;
use std::io;

#[derive(Debug)]
pub enum FlavorError {
    // Format errors
    InvalidMagic,
    InvalidVersion,
    InvalidIndexSize,
    ChecksumMismatch,
    InvalidEmojiMagic,
    
    // Slot errors
    SlotNotFound,
    InvalidSlotIndex,
    SlotExtractionFailed(String),
    
    // Security errors
    IntegrityCheckFailed,
    SignatureInvalid,
    NoIntegritySeal,
    
    // Execution errors
    ExecutionFailed(String),
    MissingSlot(usize),
    
    // IO errors
    Io(io::Error),
    
    // Other errors
    InvalidData(String),
    CompressionError(String),
    SerializationError(String),
}

impl fmt::Display for FlavorError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            FlavorError::InvalidMagic => write!(f, "Invalid PSPF magic"),
            FlavorError::InvalidVersion => write!(f, "Unsupported PSPF version"),
            FlavorError::InvalidIndexSize => write!(f, "Invalid index size"),
            FlavorError::ChecksumMismatch => write!(f, "Checksum mismatch"),
            FlavorError::InvalidEmojiMagic => write!(f, "Invalid emoji magic"),
            
            FlavorError::SlotNotFound => write!(f, "Slot not found"),
            FlavorError::InvalidSlotIndex => write!(f, "Invalid slot index"),
            FlavorError::SlotExtractionFailed(msg) => write!(f, "Slot extraction failed: {}", msg),
            
            FlavorError::IntegrityCheckFailed => write!(f, "Integrity check failed"),
            FlavorError::SignatureInvalid => write!(f, "Invalid signature"),
            FlavorError::NoIntegritySeal => write!(f, "No integrity seal found"),
            
            FlavorError::ExecutionFailed(msg) => write!(f, "Execution failed: {}", msg),
            FlavorError::MissingSlot(idx) => write!(f, "Referenced slot {} missing", idx),
            
            FlavorError::Io(err) => write!(f, "IO error: {}", err),
            FlavorError::InvalidData(msg) => write!(f, "Invalid data: {}", msg),
            FlavorError::CompressionError(msg) => write!(f, "Compression error: {}", msg),
            FlavorError::SerializationError(msg) => write!(f, "Serialization error: {}", msg),
        }
    }
}

impl std::error::Error for FlavorError {
    fn source(&self) -> Option<&(dyn std::error::Error + 'static)> {
        match self {
            FlavorError::Io(err) => Some(err),
            _ => None,
        }
    }
}

impl From<io::Error> for FlavorError {
    fn from(err: io::Error) -> Self {
        FlavorError::Io(err)
    }
}

impl From<serde_json::Error> for FlavorError {
    fn from(err: serde_json::Error) -> Self {
        FlavorError::SerializationError(err.to_string())
    }
}

pub type Result<T> = std::result::Result<T, FlavorError>;