package format_2025

import "encoding/json"

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
	Command string `json:"command"`
	// Environment is read from "env", the key Python writes into the manifest
	// it hands this builder. It was tagged "environment", so a caller's
	// execution environment was dropped at build time before it ever reached a
	// bundle (#36). "environment" is still accepted for older manifests.
	Environment map[string]string `json:"env,omitempty"`
}

// UnmarshalJSON reads the execution environment from "env", falling back to the
// "environment" key older manifests use. If both are present, "env" wins.
func (c *ExecutionConfig) UnmarshalJSON(data []byte) error {
	type executionConfigAlias ExecutionConfig
	aux := struct {
		*executionConfigAlias
		Legacy map[string]string `json:"environment,omitempty"`
	}{executionConfigAlias: (*executionConfigAlias)(c)}

	if err := json.Unmarshal(data, &aux); err != nil {
		return err
	}
	if len(c.Environment) == 0 {
		c.Environment = aux.Legacy
	}
	return nil
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
