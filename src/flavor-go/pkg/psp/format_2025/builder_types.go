package format_2025

// BuildOptions represents the configuration for building a PSPF package.
//
// This struct defines the complete configuration needed to build a PSPF/2025
// package. It aligns with Python's BuildOptions and Rust's BuildOptions for
// cross-language consistency. The structure matches the JSON manifest format
// used by all PSPF builders.
//
// Required fields:
// - Package: Basic package metadata (name, version, description)
// - Execution: How to run the package (command, environment, primary slot)
//
// Optional fields:
// - Slots: List of data slots to include in the package
// - Launcher: Path to the native launcher binary
// - Runtime: Runtime environment configuration
// - CacheValidation: Cache validation rules
// - SetupCommands: Commands to run during setup
type BuildOptions struct {
	// Package metadata (required per SPEC)
	Package PackageConfig `json:"package"`

	// Execution configuration (required per SPEC)
	Execution ExecutionConfig `json:"execution"`

	// Slots configuration
	Slots []Slot `json:"slots"`

	// Optional configuration
	Launcher        string                 `json:"launcher,omitempty"`
	CacheValidation *CacheValidationConfig `json:"cache_validation,omitempty"`
	SetupCommands   []interface{}          `json:"setup_commands,omitempty"`
	Runtime         *RuntimeConfig         `json:"runtime,omitempty"`
}

// PackageConfig contains basic package metadata
type PackageConfig struct {
	Name        string `json:"name"`
	Version     string `json:"version"`
	Description string `json:"description,omitempty"`
}

// ExecutionConfig defines how the package should be executed
type ExecutionConfig struct {
	PrimarySlot int               `json:"primary_slot,omitempty"`
	Command     string            `json:"command"`
	Environment map[string]string `json:"environment,omitempty"`
}

// RuntimeConfig contains runtime environment configuration
type RuntimeConfig struct {
	Env map[string]interface{} `json:"env,omitempty"`
}

// CacheValidationConfig defines cache validation rules
type CacheValidationConfig struct {
	CheckFile       string `json:"check_file"`
	ExpectedContent string `json:"expected_content,omitempty"`
}

// Slot defines a data slot to be included in the package
type Slot struct {
	Slot        *int   `json:"slot,omitempty"`        // Optional: position validator
	ID          string `json:"id"`                    // Arbitrary identifier
	Source      string `json:"source"`                // Source path
	Target      string `json:"target"`                // Destination in workenv
	Purpose     string `json:"purpose"`               // Role of the slot
	Lifecycle   string `json:"lifecycle"`             // Cache management
	Resolution  string `json:"resolution,omitempty"`  // When to resolve: build|runtime|lazy
	Operations  string `json:"operations"`            // Operations chain (e.g., "gzip", "tar.gz")
	Permissions string `json:"permissions,omitempty"` // Unix permissions (e.g., "0755")
}
