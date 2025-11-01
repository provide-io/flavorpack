package main

import (
	"fmt"
	"os"
	"runtime"
	"runtime/debug"
	"time"

	"github.com/provide-io/flavor/go/flavor/pkg/psp/format_2025"
)

const version = "0.3.0"

// Windows crash debugging - write diagnostics before anything else
func init() {
	// On Windows, write startup diagnostic immediately
	if runtime.GOOS == "windows" {
		// Write to stderr immediately (will be captured in logs)
		fmt.Fprintf(os.Stderr, "[GO-LAUNCHER-DEBUG] init() called, GOOS=%s GOARCH=%s\n", runtime.GOOS, runtime.GOARCH)
	}
}

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
	// Windows debugging - log entry to main()
	if runtime.GOOS == "windows" {
		fmt.Fprintf(os.Stderr, "[GO-LAUNCHER-DEBUG] main() started\n")
	}

	// Set up panic recovery to return specific exit code
	defer func() {
		if r := recover(); r != nil {
			fmt.Fprintf(os.Stderr, "[GO-LAUNCHER-ERROR] PANIC: %v\n", r)
			debug.PrintStack()
			os.Exit(format_2025.ExitPanic)
		}
	}()

	if runtime.GOOS == "windows" {
		fmt.Fprintf(os.Stderr, "[GO-LAUNCHER-DEBUG] Getting executable path...\n")
	}

	exePath, err := os.Executable()
	if err != nil {
		fmt.Fprintf(os.Stderr, "[GO-LAUNCHER-ERROR] Failed to get executable path: %v\n", err)
		os.Exit(format_2025.ExitIOError)
	}

	if runtime.GOOS == "windows" {
		fmt.Fprintf(os.Stderr, "[GO-LAUNCHER-DEBUG] Executable path: %s\n", exePath)
		fmt.Fprintf(os.Stderr, "[GO-LAUNCHER-DEBUG] Args count: %d\n", len(os.Args))
		if len(os.Args) > 0 {
			fmt.Fprintf(os.Stderr, "[GO-LAUNCHER-DEBUG] Args[0]: %s\n", os.Args[0])
		}
	}

	// Check for --version flag before launching
	if len(os.Args) > 1 && os.Args[1] == "--version" {
		fmt.Printf("flavor-go-launcher %s\n", version)
		fmt.Printf("Built: %s\n", getBuilderTimestamp())
		os.Exit(0)
	}

	// Check for --log-level flag
	var logLevel string
	var logSource string
	var args []string

	if len(os.Args) > 2 && os.Args[1] == "--log-level" {
		logLevel = os.Args[2]
		logSource = "CLI --log-level"
		args = os.Args[3:] // Skip --log-level and its value
	} else {
		args = os.Args[1:]
	}

	// Launch with error handling
	// Note: LaunchWithLogLevel calls os.Exit directly on error
	if runtime.GOOS == "windows" {
		fmt.Fprintf(os.Stderr, "[GO-LAUNCHER-DEBUG] Calling LaunchWithLogLevel(exePath=%s, args=%v, logLevel=%s)\n", exePath, args, logLevel)
	}
	format_2025.LaunchWithLogLevel(exePath, args, logLevel, logSource)

	// If we reach here, launch didn't call os.Exit (shouldn't happen)
	if runtime.GOOS == "windows" {
		fmt.Fprintf(os.Stderr, "[GO-LAUNCHER-DEBUG] LaunchWithLogLevel returned (unexpected)\n")
	}
}

// Test 3: Trigger rebuild Mon Aug 18 15:45:13 PDT 2025
