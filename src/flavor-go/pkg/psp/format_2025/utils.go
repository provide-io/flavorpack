// SPDX-FileCopyrightText: Copyright (c) 2026 provide.io llc. All rights reserved.
// SPDX-License-Identifier: Apache-2.0

package format_2025

import "os"

func getLauncherPath(unused string) string {
	// Check environment variable
	if launcherBin := os.Getenv(EnvLauncherBin); launcherBin != "" {
		return launcherBin
	}

	// No fallback - launcher must be explicitly specified
	return ""
}

func AlignOffset(offset int64, alignment int64) int64 {
	return (offset + alignment - 1) & ^(alignment - 1)
}
