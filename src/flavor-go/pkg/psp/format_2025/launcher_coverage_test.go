package format_2025

import (
	"os"
	"path/filepath"
	"testing"
)

// TestLaunchWithLogLevelJsonNoColon exercises the "json" prefix without a colon,
// which must fall back to actualLevel = "info".
func TestLaunchWithLogLevelJsonNoColon(t *testing.T) {
	bundle := buildLauncherTestBundle(t)

	// "json" without a colon → jsonFormat=true, actualLevel="info"
	t.Setenv(EnvLauncherCLI, "1")
	LaunchWithLogLevel(bundle, []string{"info"}, "json", "test")
}

// TestLaunchWithLogLevelJsonNoColonWithLogPath exercises the "json" prefix without
// a colon together with a log file path, covering both the json-no-colon branch
// and the EnvLogPath file creation branch.
func TestLaunchWithLogLevelJsonNoColonWithLogPath(t *testing.T) {
	bundle := buildLauncherTestBundle(t)
	logPath := filepath.Join(t.TempDir(), "launcher.log")

	t.Setenv(EnvLauncherCLI, "1")
	t.Setenv(EnvLogPath, logPath)
	LaunchWithLogLevel(bundle, []string{"info"}, "json", "test")

	if _, err := os.Stat(logPath); err != nil {
		t.Fatalf("expected log file to be created: %v", err)
	}
}

// TestLaunchWithLogLevelHelpCommand exercises the "help" CLI command path.
func TestLaunchWithLogLevelHelpCommand(t *testing.T) {
	bundle := buildLauncherTestBundle(t)

	t.Setenv(EnvLauncherCLI, "1")
	LaunchWithLogLevel(bundle, []string{"help"}, "warn", "test")
}

// TestLaunchWithLogLevelHelpDashDash exercises the "--help" CLI command path.
func TestLaunchWithLogLevelHelpDashDash(t *testing.T) {
	bundle := buildLauncherTestBundle(t)

	t.Setenv(EnvLauncherCLI, "1")
	LaunchWithLogLevel(bundle, []string{"--help"}, "warn", "test")
}

// TestLaunchWithLogLevelVerifyCommand exercises the "verify" CLI command path.
func TestLaunchWithLogLevelVerifyCommand(t *testing.T) {
	bundle := buildLauncherTestBundle(t)

	t.Setenv(EnvLauncherCLI, "1")
	LaunchWithLogLevel(bundle, []string{"verify"}, "warn", "test")
}

// TestLaunchWithLogLevelUnknownCommand exercises the default unknown command path.
// The function calls osExitFn which is stubbed in tests via the package variable.
func TestLaunchWithLogLevelUnknownCommand(t *testing.T) {
	bundle := buildLauncherTestBundle(t)

	// Stub osExitFn to prevent actual process exit.
	oldExit := osExitFn
	t.Cleanup(func() { osExitFn = oldExit })
	var exitCode int
	osExitFn = func(code int) { exitCode = code; panic("exit") }

	t.Setenv(EnvLauncherCLI, "1")

	func() {
		defer func() { _ = recover() }()
		LaunchWithLogLevel(bundle, []string{"unknown-command-xyz"}, "warn", "test")
	}()

	if exitCode != ExitInvalidArgs {
		t.Fatalf("expected ExitInvalidArgs (%d), got %d", ExitInvalidArgs, exitCode)
	}
}

// TestLaunchWithLogLevelExtractShortArgs exercises the extract command with
// fewer than 3 arguments (missing output dir), which calls osExitFn.
func TestLaunchWithLogLevelExtractShortArgs(t *testing.T) {
	bundle := buildLauncherTestBundle(t)

	oldExit := osExitFn
	t.Cleanup(func() { osExitFn = oldExit })
	var exitCode int
	osExitFn = func(code int) { exitCode = code; panic("exit") }

	t.Setenv(EnvLauncherCLI, "1")

	func() {
		defer func() { _ = recover() }()
		LaunchWithLogLevel(bundle, []string{"extract", "0"}, "warn", "test")
	}()

	if exitCode != ExitInvalidArgs {
		t.Fatalf("expected ExitInvalidArgs (%d), got %d", ExitInvalidArgs, exitCode)
	}
}

// TestLaunchWithLogLevelEnvLogPathNotWritable exercises the EnvLogPath branch when
// the path cannot be opened (e.g., directory missing). The logger should fall back
// to os.Stderr without panicking.
func TestLaunchWithLogLevelEnvLogPathNotWritable(t *testing.T) {
	bundle := buildLauncherTestBundle(t)

	// Point to a non-existent directory — OpenFile will fail, output falls back.
	t.Setenv(EnvLogPath, filepath.Join(t.TempDir(), "nonexistent_dir", "launcher.log"))
	t.Setenv(EnvLauncherCLI, "1")

	// Should not panic even if the log file cannot be opened.
	LaunchWithLogLevel(bundle, []string{"info"}, "warn", "test")
}
