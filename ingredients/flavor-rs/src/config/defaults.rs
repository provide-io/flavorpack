//! Default configuration values for FlavorPack

/// ValidationLevel represents different levels of security validation
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum ValidationLevel {
    /// Full security checks, fail on any issue (most secure)
    Strict,
    /// Normal validation, warnings for minor issues (default)
    Standard,
    /// Skip signature checks, warn on checksum mismatches
    Relaxed,
    /// Only critical checks, continue on most warnings
    Minimal,
    /// Skip all validation (testing only, NOT RECOMMENDED)
    None,
}

impl ValidationLevel {
    /// Parse validation level from string (case insensitive)
    pub fn from_str(s: &str) -> Option<Self> {
        match s.to_lowercase().as_str() {
            "strict" => Some(ValidationLevel::Strict),
            "standard" => Some(ValidationLevel::Standard),
            "relaxed" => Some(ValidationLevel::Relaxed),
            "minimal" => Some(ValidationLevel::Minimal),
            "none" => Some(ValidationLevel::None),
            _ => None,
        }
    }

    /// Convert validation level to string
    pub fn as_str(&self) -> &'static str {
        match self {
            ValidationLevel::Strict => "strict",
            ValidationLevel::Standard => "standard",
            ValidationLevel::Relaxed => "relaxed",
            ValidationLevel::Minimal => "minimal",
            ValidationLevel::None => "none",
        }
    }
}

/// Default validation configuration
#[derive(Debug, Clone)]
pub struct ValidationDefaults {
    /// Default validation level when not specified
    pub default_validation_level: ValidationLevel,
    /// Where to send validation warnings
    pub warning_output: &'static str,
    /// Where to send validation errors
    pub error_output: &'static str,
}

impl Default for ValidationDefaults {
    fn default() -> Self {
        Self {
            default_validation_level: ValidationLevel::Standard, // Default to standard with warnings
            warning_output: "stderr",
            error_output: "stderr",
        }
    }
}

/// Default security configuration
#[derive(Debug, Clone)]
pub struct SecurityDefaults {
    /// Require integrity verification by default
    pub require_integrity_verification: bool,
    /// Require signature verification by default
    pub require_signature_verification: bool,
    /// Warn on checksum mismatches
    pub warn_on_checksum_mismatch: bool,
}

impl Default for SecurityDefaults {
    fn default() -> Self {
        Self {
            require_integrity_verification: true,
            require_signature_verification: true,
            warn_on_checksum_mismatch: true,
        }
    }
}

/// Get default validation configuration
pub fn get_validation_defaults() -> ValidationDefaults {
    ValidationDefaults::default()
}

/// Get default security configuration
pub fn get_security_defaults() -> SecurityDefaults {
    SecurityDefaults::default()
}