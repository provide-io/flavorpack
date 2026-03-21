// SPDX-FileCopyrightText: Copyright (c) 2026 provide.io llc. All rights reserved.
// SPDX-License-Identifier: Apache-2.0

package main

import (
	"fmt"
	"os"
	"runtime/debug"

	"github.com/provide-io/flavor/go/flavor/pkg/psp/format_2025"
)

const version = "0.3.21"

// Phase 19 cache invalidation: Force rebuild with CGO enabled for Windows (2025-10-31)

func getBuilderTimestamp() string {
	// Try to get vcs.time from build info
	if info, ok := debug.ReadBuildInfo(); ok {
		for _, setting := range info.Settings {
			if setting.Key == "vcs.time" {
				if t, err := time.Parse(time.RFC3339, setting.Value); err == nil {
					return t.UTC().Format(time.RFC3339)
				}
			}
		}
	}
	// Fallback to binary modification time
	if exePath, err := os.Executable(); err == nil {
		if stat, err := os.Stat(exePath); err == nil {
			return stat.ModTime().UTC().Format(time.RFC3339)
		}
	}
	return time.Now().UTC().Format(time.RFC3339)
}

func main() {
	// Set up panic recovery to return specific exit code
	defer func() {
		if r := recover(); r != nil {
			fmt.Fprintf(os.Stderr, "PANIC: %v\n", r)
			debug.PrintStack()
			os.Exit(format_2025.ExitPanic)
		}
	}()

	exePath, err := executablePathFn()
	if err != nil {
		fmt.Fprintf(os.Stderr, "Failed to get executable path: %v\n", err)
		os.Exit(format_2025.ExitIOError)
	}

	// Launch with error handling
	// Note: LaunchWithLogLevel calls os.Exit directly on error
	// All arguments are passed through - launcher only intercepts args when FLAVOR_LAUNCHER_CLI=1
	launchFn(exePath, os.Args[1:], "", "")
}
