//go:build !windows
// +build !windows

package format_2025

import (
	"fmt"

	"github.com/hashicorp/go-hclog"
)

// EmbedPSPFAsResource is a stub for non-Windows platforms.
// On Unix, we append PSPF data instead of embedding as resources.
func EmbedPSPFAsResource(exePath string, pspfData []byte, logger hclog.Logger) error {
	return fmt.Errorf("PE resource embedding is only supported on Windows")
}

// ReadPSPFFromResource is a stub for non-Windows platforms.
// On Unix, we read PSPF data from EOF instead of resources.
func ReadPSPFFromResource(exePath string, logger hclog.Logger) ([]byte, error) {
	return nil, fmt.Errorf("PE resource reading is only supported on Windows")
}

// HasPSPFResource is a stub for non-Windows platforms.
func HasPSPFResource(exePath string, logger hclog.Logger) bool {
	return false
}
