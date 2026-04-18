// SPDX-FileCopyrightText: Copyright (c) 2026 provide.io llc. All rights reserved.
// SPDX-License-Identifier: Apache-2.0

package format_2025

import (
	"testing"
)

// TestLaunchWithLogLevelJsonWithColon covers line 47 in launcher.go:
// the "json:level" format where actualLevel = parts[1].
// E.g. "json:debug" sets jsonFormat=true, actualLevel="debug".
func TestLaunchWithLogLevelJsonWithColon(t *testing.T) {
	bundle := buildLauncherTestBundle(t)

	t.Setenv(EnvLauncherCLI, "1")
	// "json:debug" → jsonFormat=true, actualLevel="debug" (parts[1] branch)
	LaunchWithLogLevel(bundle, []string{"info"}, "json:debug", "test")
}

// TestLaunchWithLogLevelRunCommandError covers lines 136-138 in launcher.go:
// when execBundle returns an error (not CLI run) — the error handling with
// PSPF/magic/extract/slot/file/I/O string detection.
// We simulate this by providing a bad bundle and running in non-CLI mode.
func TestLaunchWithLogLevelRunCommandNonCLIError(t *testing.T) {
	// Use a non-existent bundle to cause execBundle to fail.
	// In non-CLI mode (EnvLauncherCLI not set), LaunchWithLogLevel calls execBundle directly.
	nonExistent := t.TempDir() + "/nonexistent.psp"

	oldExit := osExitFn
	t.Cleanup(func() { osExitFn = oldExit })
	var exitCode int
	osExitFn = func(code int) {
		exitCode = code
		panic("stop-exit")
	}

	t.Setenv(EnvValidation, "none")
	t.Setenv(EnvWorkenvCache, "false")
	t.Setenv(EnvCacheDir, t.TempDir())

	func() {
		defer func() { _ = recover() }()
		LaunchWithLogLevel(nonExistent, nil, "warn", "test")
	}()

	// Some exit code should have been called (ExitPSPFError, ExitIOError, or ExitExecutionError).
	if exitCode == 0 {
		t.Fatalf("expected non-zero exit code, got %d", exitCode)
	}
}
