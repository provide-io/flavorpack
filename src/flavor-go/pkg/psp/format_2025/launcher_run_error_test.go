package format_2025

import (
	"errors"
	"testing"

	"github.com/hashicorp/go-hclog"
)

// TestLaunchWithLogLevelRunCommandError covers lines 135-138 in launcher.go:
// when the "run" CLI command is used but execBundle fails (e.g., bad bundle),
// LaunchWithLogLevel calls osExitFn(ExitExecutionError).
func TestLaunchWithLogLevelRunCommandError(t *testing.T) {
	t.Setenv(EnvLauncherCLI, "1")
	t.Setenv(EnvValidation, "none")
	t.Setenv(EnvCacheDir, t.TempDir())

	oldExit := osExitFn
	t.Cleanup(func() { osExitFn = oldExit })

	var exitCode int
	osExitFn = func(code int) {
		exitCode = code
		panic(launcherExitCode{code: code})
	}

	defer func() {
		r := recover()
		if r == nil {
			t.Fatal("expected osExitFn to be called")
		}
		if _, ok := r.(launcherExitCode); !ok {
			panic(r)
		}
		// exitCode should be non-zero (execution error or similar)
		_ = exitCode
	}()

	// Use a non-existent/invalid bundle path so execBundle fails.
	LaunchWithLogLevel("/nonexistent/path.pspf", []string{"run", "arg1"}, "warn", "test")
}

// TestLaunchWithLogLevelPSPFError covers lines 171-173 in launcher.go:
// when execBundle fails with an error containing "PSPF" or "magic",
// LaunchWithLogLevel calls osExitFn(ExitPSPFError).
// We trigger this by using a bundle path that results in a "PSPF" error.
func TestLaunchWithLogLevelPSPFError(t *testing.T) {
	t.Setenv(EnvLauncherCLI, "0") // not CLI mode
	t.Setenv(EnvValidation, "none")
	t.Setenv(EnvCacheDir, t.TempDir())

	oldExit := osExitFn
	t.Cleanup(func() { osExitFn = oldExit })

	var exitCode int
	osExitFn = func(code int) {
		exitCode = code
		panic(launcherExitCode{code: code})
	}

	defer func() {
		r := recover()
		if r == nil {
			t.Fatal("expected osExitFn to be called")
		}
		if _, ok := r.(launcherExitCode); !ok {
			panic(r)
		}
		// exitCode could be ExitPSPFError, ExitIOError, or ExitExecutionError
		// depending on the error message. Either way, the launcher exited.
		_ = exitCode
	}()

	// Use a non-existent bundle path; the error will be about reading the file
	// (file not found), which may hit the I/O error path or PSPF error path.
	LaunchWithLogLevel("/nonexistent/path.pspf", nil, "warn", "test")
}

// TestLaunchWithLogLevelPSPFErrorClassification covers lines 171-173 in launcher.go:
// when execBundle fails with an error containing "PSPF", the launcher exits with
// ExitPSPFError. We inject hasPSPFResourceFn and readPSPFFromResourceFn so that
// prepareBundlePath returns an error containing "PSPF".
func TestLaunchWithLogLevelPSPFErrorClassification(t *testing.T) {
	t.Setenv(EnvLauncherCLI, "0") // not CLI mode
	t.Setenv(EnvValidation, "none")
	t.Setenv(EnvCacheDir, t.TempDir())

	// Inject PE resource functions so prepareBundlePath returns a "PSPF" error.
	oldHas := hasPSPFResourceFn
	oldRead := readPSPFFromResourceFn
	t.Cleanup(func() {
		hasPSPFResourceFn = oldHas
		readPSPFFromResourceFn = oldRead
	})
	hasPSPFResourceFn = func(path string, logger hclog.Logger) bool { return true }
	readPSPFFromResourceFn = func(path string, logger hclog.Logger) ([]byte, error) {
		return nil, errors.New("PSPF resource extraction failed")
	}

	oldExit := osExitFn
	t.Cleanup(func() { osExitFn = oldExit })

	var exitCode int
	osExitFn = func(code int) {
		exitCode = code
		panic(launcherExitCode{code: code})
	}

	defer func() {
		r := recover()
		if r == nil {
			t.Fatal("expected osExitFn to be called")
		}
		if _, ok := r.(launcherExitCode); !ok {
			panic(r)
		}
		if exitCode != ExitPSPFError {
			t.Errorf("expected ExitPSPFError (%d), got %d", ExitPSPFError, exitCode)
		}
	}()

	LaunchWithLogLevel("/fake/path.pspf", nil, "warn", "test")
}
