package format_2025

import "os"

func getLauncherPath(unused string) string {
	// Check environment variable
	if launcherBin := os.Getenv("FLAVOR_LAUNCHER_BIN"); launcherBin != "" {
		return launcherBin
	}

	// No fallback - launcher must be explicitly specified
	return ""
}

func AlignOffset(offset int64, alignment int64) int64 {
	return (offset + alignment - 1) & ^(alignment - 1)
}
