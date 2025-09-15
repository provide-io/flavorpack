package config

// ValidationDefaults contains default validation settings for FlavorPack
type ValidationDefaults struct {
	// DefaultValidationLevel is the default validation level when not specified
	DefaultValidationLevel string

	// WarningOutput determines where validation warnings are sent
	WarningOutput string

	// ErrorOutput determines where validation errors are sent
	ErrorOutput string
}

// GetValidationDefaults returns the default validation configuration
func GetValidationDefaults() ValidationDefaults {
	return ValidationDefaults{
		DefaultValidationLevel: "standard", // Default to standard validation with warnings
		WarningOutput:         "stderr",   // Send warnings to stderr
		ErrorOutput:          "stderr",   // Send errors to stderr
	}
}

// SecurityDefaults contains default security settings
type SecurityDefaults struct {
	// RequireIntegrityVerification determines if integrity verification is required by default
	RequireIntegrityVerification bool

	// RequireSignatureVerification determines if signature verification is required by default
	RequireSignatureVerification bool

	// WarnOnChecksumMismatch determines if checksum mismatches should emit warnings
	WarnOnChecksumMismatch bool
}

// GetSecurityDefaults returns the default security configuration
func GetSecurityDefaults() SecurityDefaults {
	return SecurityDefaults{
		RequireIntegrityVerification: true, // Require integrity verification by default
		RequireSignatureVerification: true, // Require signature verification by default
		WarnOnChecksumMismatch:       true, // Warn on checksum mismatches
	}
}