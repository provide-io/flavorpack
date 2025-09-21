// Package workenv provides validation for work environments
package workenv

import (
	"encoding/json"
	"os"
	"path/filepath"
	"time"
)

// ValidationMarker represents the extraction completion marker
type ValidationMarker struct {
	Timestamp   time.Time `json:"timestamp"`
	PackageName string    `json:"package_name"`
	Version     string    `json:"version"`
	Checksum    string    `json:"checksum"`
}

// IsValid checks if a workenv is valid and complete
func IsValid(path string, packageName, version, checksum string) bool {
	markerPath := filepath.Join(path, ".extraction.complete")

	// Check if marker exists
	data, err := os.ReadFile(markerPath)
	if err != nil {
		return false
	}

	// Parse marker
	var marker ValidationMarker
	if err := json.Unmarshal(data, &marker); err != nil {
		return false
	}

	// Validate marker matches current package
	if marker.PackageName != packageName || marker.Version != version {
		return false
	}

	// If we have a checksum, validate it matches
	if checksum != "" && marker.Checksum != checksum {
		return false
	}

	// Check if marker is not too old (optional: 30 days)
	if time.Since(marker.Timestamp) > 30*24*time.Hour {
		return false
	}

	// Check that essential directories exist
	essentialDirs := []string{"bin", "lib"}
	for _, dir := range essentialDirs {
		dirPath := filepath.Join(path, dir)
		if info, err := os.Stat(dirPath); err != nil || !info.IsDir() {
			return false
		}
	}

	return true
}

// MarkComplete marks a workenv as extraction complete
func MarkComplete(path string, packageName, version, checksum string) error {
	markerPath := filepath.Join(path, ".extraction.complete")

	marker := ValidationMarker{
		Timestamp:   time.Now(),
		PackageName: packageName,
		Version:     version,
		Checksum:    checksum,
	}

	data, err := json.MarshalIndent(marker, "", "  ")
	if err != nil {
		return err
	}

	return os.WriteFile(markerPath, data, 0644)
}

// MarkIncomplete marks a workenv as incomplete (failed extraction)
func MarkIncomplete(path string, reason string) error {
	markerPath := filepath.Join(path, ".extraction.incomplete")

	marker := map[string]interface{}{
		"timestamp": time.Now(),
		"reason":    reason,
	}

	data, err := json.MarshalIndent(marker, "", "  ")
	if err != nil {
		return err
	}

	// Remove complete marker if it exists
	os.Remove(filepath.Join(path, ".extraction.complete"))

	return os.WriteFile(markerPath, data, 0644)
}

// Clean removes invalid or incomplete workenvs
func Clean(path string) error {
	// Remove incomplete marker
	os.Remove(filepath.Join(path, ".extraction.incomplete"))

	// Remove complete marker
	os.Remove(filepath.Join(path, ".extraction.complete"))

	// Remove lock file if present
	os.Remove(filepath.Join(path, ".extraction.lock"))

	// Optionally remove the entire directory
	// return os.RemoveAll(path)

	return nil
}
