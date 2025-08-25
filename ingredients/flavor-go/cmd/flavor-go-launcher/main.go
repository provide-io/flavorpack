package main

import (
	"fmt"
	"os"
	"runtime/debug"
	"time"

	"github.com/provide-io/flavor/go/flavor/pkg/psp/format_2025"
)

const version = "0.3.0"

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
	exePath, err := os.Executable()
	if err != nil {
		panic(err)
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

	format_2025.LaunchWithLogLevel(exePath, args, logLevel, logSource)
}
// Test 3: Trigger rebuild Mon Aug 18 15:45:13 PDT 2025
