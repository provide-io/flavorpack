package main

import (
	"fmt"
	"os"
	"runtime/debug"

	"github.com/provide-io/flavor/go/flavor/pkg/psp/format_2025"
)

// Version and BuildTime are injected at link time via -ldflags "-X main.Version=...".
// Without these declarations the -X flags in the Makefile and ci/build-go-helpers.sh
// silently do nothing.
var (
	Version   = "dev"
	BuildTime = ""
)

var executablePathFn = os.Executable
var launchFn = format_2025.LaunchWithLogLevel

func init() {
	v := Version
	if BuildTime != "" {
		v += " built " + BuildTime
	}
	format_2025.LauncherVersion = v
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
