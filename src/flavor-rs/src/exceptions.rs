//! Error types for flavor

use std::fmt;

/// Main error type for flavor operations
#[derive(Debug)]
pub enum FlavorError {
    /// Package format not supported
    UnsupportedFormat(String),

    /// Package verification failed
    VerificationFailed(String),

    /// Build error
    BuildError(String),

    /// Launch error
    LaunchError(String),

    /// IO error
    IoError(std::io::Error),

    /// JSON parsing error
    JsonError(serde_json::Error),

    /// Generic error with message
    Generic(String),
}

impl fmt::Display for FlavorError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            FlavorError::UnsupportedFormat(msg) => write!(f, "Unsupported format: {msg}"),
            FlavorError::VerificationFailed(msg) => write!(f, "Verification failed: {msg}"),
            FlavorError::BuildError(msg) => write!(f, "Build error: {msg}"),
            FlavorError::LaunchError(msg) => write!(f, "Launch error: {msg}"),
            FlavorError::IoError(err) => write!(f, "IO error: {err}"),
            FlavorError::JsonError(err) => write!(f, "JSON error: {err}"),
            FlavorError::Generic(msg) => write!(f, "{msg}"),
        }
    }
}

impl std::error::Error for FlavorError {}

impl From<std::io::Error> for FlavorError {
    fn from(err: std::io::Error) -> Self {
        FlavorError::IoError(err)
    }
}

impl From<serde_json::Error> for FlavorError {
    fn from(err: serde_json::Error) -> Self {
        FlavorError::JsonError(err)
    }
}

impl From<anyhow::Error> for FlavorError {
    fn from(err: anyhow::Error) -> Self {
        FlavorError::Generic(err.to_string())
    }
}

/// Result type for flavor operations
pub type Result<T> = std::result::Result<T, FlavorError>;
