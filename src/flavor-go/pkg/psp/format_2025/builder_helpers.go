package format_2025

import (
	"crypto/sha256"
	"encoding/binary"
	"os"
	"runtime/debug"
	"time"
)

// hashSlotName computes a hash of the slot name (SHA256, first 8 bytes as uint64)
func hashSlotName(name string) uint64 {
	hash := sha256.Sum256([]byte(name))
	return binary.LittleEndian.Uint64(hash[:8])
}

// getBuilderTimestamp returns the compilation time of the builder binary
func getBuilderTimestamp() string {
	// Try to get build info from runtime
	if info, ok := debug.ReadBuildInfo(); ok {
		// Look for vcs.time setting (Go 1.18+)
		for _, setting := range info.Settings {
			if setting.Key == "vcs.time" {
				// Parse and format the time
				if t, err := time.Parse(time.RFC3339, setting.Value); err == nil {
					return t.UTC().Format(time.RFC3339)
				}
				return setting.Value
			}
		}
	}

	// Fallback: get the builder binary's modification time
	if exePath, err := os.Executable(); err == nil {
		if stat, err := os.Stat(exePath); err == nil {
			return stat.ModTime().UTC().Format(time.RFC3339)
		}
	}

	// Last resort: return current time
	return time.Now().UTC().Format(time.RFC3339)
}
