package format_2025

import (
	"os"
	"strconv"
	"strings"
)

// Exit codes for different error types
const (
	ExitPanic           = 101
	ExitPSPFError       = 102
	ExitExtractionError = 103
	ExitExecutionError  = 104
	ExitInvalidArgs     = 105
	ExitIOError         = 106
)

// ValidationLevel represents different levels of security validation
type ValidationLevel int

const (
	ValidationStrict   ValidationLevel = iota // Default - full security checks, fail on any issue
	ValidationStandard                        // Normal validation, warnings for minor issues
	ValidationRelaxed                         // Skip signature checks, warn on checksum mismatches
	ValidationMinimal                         // Only critical checks, continue on most warnings
	ValidationNone                            // Skip all validation (testing only)
)

// getValidationLevel determines the validation level from environment or defaults
func getValidationLevel() ValidationLevel {
	// Check FLAVOR_VALIDATION variable
	if val := os.Getenv("FLAVOR_VALIDATION"); val != "" {
		switch strings.ToLower(val) {
		case "strict":
			return ValidationStrict
		case "standard":
			return ValidationStandard
		case "relaxed":
			return ValidationRelaxed
		case "minimal":
			return ValidationMinimal
		case "none":
			return ValidationNone
		}
	}

	// Use default from local defaults
	switch strings.ToLower(DefaultValidationLevel) {
	case "strict":
		return ValidationStrict
	case "standard":
		return ValidationStandard
	case "relaxed":
		return ValidationRelaxed
	case "minimal":
		return ValidationMinimal
	case "none":
		return ValidationNone
	default:
		return ValidationStandard // Fallback to standard if invalid
	}
}

// isEnvTrue checks if an environment variable is set to a true value
func isEnvTrue(key string) bool {
	val := os.Getenv(key)
	if val == "" {
		return false
	}

	valLower := strings.ToLower(val)
	if valLower == "on" || valLower == "yes" {
		return true
	}

	result, err := strconv.ParseBool(val)
	return err == nil && result
}
