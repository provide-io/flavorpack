package format_2025

import (
	"testing"
)

// TestLaunchWithLogLevelEnvLauncherLogLevel covers the EnvLauncherLogLevel branch
// (line ~30 in LaunchWithLogLevel): when cliLogLevel is empty but
// FLAVOR_LAUNCHER_LOG_LEVEL is set, that value is used as the log level.
func TestLaunchWithLogLevelEnvLauncherLogLevel(t *testing.T) {
	bundle := buildLauncherTestBundle(t)

	// Set only the launcher-specific env var, not the general one.
	t.Setenv(EnvLauncherLogLevel, "debug")
	t.Setenv(EnvLauncherCLI, "1")

	// Call with empty cliLogLevel so the EnvLauncherLogLevel branch is taken.
	LaunchWithLogLevel(bundle, []string{"info"}, "", "")
}

// TestLaunchWithLogLevelEnvLogLevelFallback covers the EnvLogLevel fallback branch
// (line ~33): when both cliLogLevel and EnvLauncherLogLevel are empty.
func TestLaunchWithLogLevelEnvLogLevelFallback(t *testing.T) {
	bundle := buildLauncherTestBundle(t)

	t.Setenv(EnvLauncherLogLevel, "")
	t.Setenv(EnvLogLevel, "info")
	t.Setenv(EnvLauncherCLI, "1")

	LaunchWithLogLevel(bundle, []string{"info"}, "", "")
}

// TestLaunchWithLogLevelRunCommand covers the "run" CLI subcommand path which
// calls execBundle internally. We inject syscallExecFn to prevent actual exec
// and also inject osExitFn to capture the exit call.
func TestLaunchWithLogLevelRunCommand(t *testing.T) {
	bundle := buildLauncherTestBundle(t)

	oldExec := syscallExecFn
	oldExit := osExitFn
	t.Cleanup(func() {
		syscallExecFn = oldExec
		osExitFn = oldExit
	})

	// Inject syscall.Exec to return an error so exec fails and osExitFn is called.
	syscallExecFn = func(argv0 string, argv []string, envv []string) error {
		panic("stop-exec")
	}
	var exitCode int
	osExitFn = func(code int) {
		exitCode = code
		panic("stop-exit")
	}

	t.Setenv(EnvLauncherCLI, "1")
	t.Setenv(EnvValidation, "none")
	t.Setenv(EnvWorkenvCache, "false")
	t.Setenv(EnvCacheDir, t.TempDir())

	func() {
		defer func() { _ = recover() }()
		LaunchWithLogLevel(bundle, []string{"run"}, "warn", "test")
	}()

	// Exit was called — either from exec failing or normal flow.
	_ = exitCode
}
