// Package permissions provides utilities for parsing and handling file permissions
package permissions

import (
	"fmt"
	"strconv"
	"strings"
)

// Default permission constants (user-only access for security)
const (
	DefaultFilePerms       = 0o600 // Read/write for owner only
	DefaultExecutablePerms = 0o700 // Read/write/execute for owner only
	DefaultDirPerms        = 0o700 // Read/write/execute for owner only
)

// ParseOctalString parses an octal permission string into a uint16
// Handles formats like "755", "0755", "0o755"
func ParseOctalString(s string) (uint16, error) {
	if s == "" {
		return DefaultFilePerms, nil
	}

	// Remove common prefixes
	s = strings.TrimPrefix(s, "0o")
	s = strings.TrimPrefix(s, "0")

	// Parse as octal
	val, err := strconv.ParseUint(s, 8, 16)
	if err != nil {
		return DefaultFilePerms, fmt.Errorf("invalid permission string %q: %w", s, err)
	}

	return uint16(val), nil
}

// FormatOctal formats a permission value as an octal string
func FormatOctal(perm uint16) string {
	return fmt.Sprintf("0%o", perm)
}

// IsExecutable checks if permissions include execute bit for owner
func IsExecutable(perm uint16) bool {
	return perm&0o100 != 0
}

// IsDirectory checks if permissions are appropriate for a directory
func IsDirectory(perm uint16) bool {
	// Directories need execute permission to be traversable
	return perm&0o100 != 0
}
