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

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn display_formats_each_variant_correctly() {
        let cases: Vec<(FlavorError, &str)> = vec![
            (
                FlavorError::UnsupportedFormat("v99".into()),
                "Unsupported format: v99",
            ),
            (
                FlavorError::VerificationFailed("bad sig".into()),
                "Verification failed: bad sig",
            ),
            (FlavorError::BuildError("oops".into()), "Build error: oops"),
            (
                FlavorError::LaunchError("boom".into()),
                "Launch error: boom",
            ),
            (FlavorError::Generic("misc".into()), "misc"),
        ];

        for (err, expected) in cases {
            assert_eq!(err.to_string(), expected);
        }
    }

    #[test]
    fn display_io_error_variant() {
        let io_err = std::io::Error::new(std::io::ErrorKind::NotFound, "gone");
        let err = FlavorError::IoError(io_err);
        assert!(err.to_string().contains("IO error"));
        assert!(err.to_string().contains("gone"));
    }

    #[test]
    fn display_json_error_variant() {
        let json_err = serde_json::from_str::<serde_json::Value>("not json").unwrap_err();
        let err = FlavorError::JsonError(json_err);
        assert!(err.to_string().contains("JSON error"));
    }

    #[test]
    fn from_io_error_converts() {
        let io_err = std::io::Error::new(std::io::ErrorKind::PermissionDenied, "denied");
        let err: FlavorError = io_err.into();
        assert!(matches!(err, FlavorError::IoError(_)));
    }

    #[test]
    fn from_serde_error_converts() {
        let json_err = serde_json::from_str::<serde_json::Value>("{bad}").unwrap_err();
        let err: FlavorError = json_err.into();
        assert!(matches!(err, FlavorError::JsonError(_)));
    }

    #[test]
    fn from_anyhow_error_converts() {
        let anyhow_err = anyhow::anyhow!("anyhow problem");
        let err: FlavorError = anyhow_err.into();
        assert!(matches!(err, FlavorError::Generic(_)));
        assert!(err.to_string().contains("anyhow problem"));
    }

    #[test]
    fn error_trait_is_implemented() {
        let err: Box<dyn std::error::Error> = Box::new(FlavorError::Generic("test".into()));
        assert!(err.to_string().contains("test"));
    }
}
