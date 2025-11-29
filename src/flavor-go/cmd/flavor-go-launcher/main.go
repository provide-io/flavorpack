//
// SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
// SPDX-License-Identifier: Apache-2.0
//

package main

import (
	"fmt"
	"os"
	"runtime/debug"

	"github.com/provide-io/flavor/go/flavor/pkg/psp/format_2025"
)

func main() {
	// Set up panic recovery to return specific exit code
	defer func() {
		if r := recover(); r != nil {
			fmt.Fprintf(os.Stderr, "PANIC: %v\n", r)
			debug.PrintStack()
			os.Exit(format_2025.ExitPanic)
		}
	}()

	exePath, err := os.Executable()
	if err != nil {
		fmt.Fprintf(os.Stderr, "Failed to get executable path: %v\n", err)
		os.Exit(format_2025.ExitIOError)
	}

	// Launch with error handling
	// Note: LaunchWithLogLevel calls os.Exit directly on error
	// All arguments are passed through - launcher only intercepts args when FLAVOR_LAUNCHER_CLI=1
	format_2025.LaunchWithLogLevel(exePath, os.Args[1:], "", "")
}
