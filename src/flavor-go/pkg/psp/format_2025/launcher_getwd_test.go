// SPDX-FileCopyrightText: Copyright (c) 2026 provide.io llc. All rights reserved.
// SPDX-License-Identifier: Apache-2.0

package format_2025

import (
	"errors"
	"testing"
)

// withLauncherExitTrap overrides osExitFn so it panics with a launcherExitCode.
// Returns a pointer to the captured exit code and a cleanup function.
func withLauncherExitTrap(t *testing.T) (captured *int, cleanup func()) {
	t.Helper()
	old := osExitFn
	var code int
	captured = &code
	osExitFn = func(c int) {
		code = c
		panic(launcherExitCode{code: c})
	}
	return captured, func() { osExitFn = old }
}

// catchLauncherExit runs fn and catches a launcherExitCode panic.
// Returns (true, exitCode) if osExitFn was called, (false, 0) otherwise.
// Unexpected panics are re-panicked.
func catchLauncherExit(fn func()) (exited bool, code int) {
	defer func() {
		r := recover()
		if r == nil {
			return
		}
		ec, ok := r.(launcherExitCode)
		if !ok {
			panic(r)
		}
		exited = true
		code = ec.code
	}()
	fn()
	return false, 0
}

// TestLaunchWithLogLevelOsGetWdFailure covers launcher.go:105-108
// (osGetWdFn failure → osExitFn(ExitIOError)).
func TestLaunchWithLogLevelOsGetWdFailure(t *testing.T) {
	bundle := buildLauncherTestBundle(t)

	oldGetWd := osGetWdFn
	t.Cleanup(func() { osGetWdFn = oldGetWd })
	osGetWdFn = func() (string, error) {
		return "", errors.New("injected getwd failure")
	}

	_, cleanup := withLauncherExitTrap(t)
	defer cleanup()

	exited, code := catchLauncherExit(func() {
		LaunchWithLogLevel(bundle, nil, "warn", "test")
	})

	if !exited {
		t.Fatal("expected LaunchWithLogLevel to call osExitFn due to getwd failure")
	}
	if code != ExitIOError {
		t.Fatalf("expected exit code ExitIOError (%d), got %d", ExitIOError, code)
	}
}

// TestLaunchWithLogLevelExtractInvalidArgsCLI covers launcher.go:140
// (CLI mode "extract" with insufficient args → osExitFn(ExitInvalidArgs)).
func TestLaunchWithLogLevelExtractInvalidArgsCLI(t *testing.T) {
	bundle := buildLauncherTestBundle(t)
	t.Setenv(EnvLauncherCLI, "1")
	t.Setenv(EnvValidation, "none")
	t.Setenv(EnvWorkenvCache, "false")
	t.Setenv(EnvCacheDir, t.TempDir())

	_, cleanup := withLauncherExitTrap(t)
	defer cleanup()

	exited, code := catchLauncherExit(func() {
		// "extract" with only 1 arg (needs 3: "extract", slot_index, output_dir)
		LaunchWithLogLevel(bundle, []string{"extract", "0"}, "warn", "test")
	})

	if !exited {
		t.Fatal("expected LaunchWithLogLevel to call osExitFn for invalid extract args")
	}
	if code != ExitInvalidArgs {
		t.Fatalf("expected exit code ExitInvalidArgs (%d), got %d", ExitInvalidArgs, code)
	}
}

// TestLaunchWithLogLevelExecBundleError covers launcher.go:181
// (non-CLI exec mode: execBundle returns error → osExitFn(ExitExecutionError or similar)).
func TestLaunchWithLogLevelExecBundleError(t *testing.T) {
	bundle := buildLauncherTestBundle(t)
	// Non-CLI mode (EnvLauncherCLI not set)
	t.Setenv(EnvLauncherCLI, "")
	t.Setenv(EnvValidation, "none")
	t.Setenv(EnvWorkenvCache, "false")
	t.Setenv(EnvCacheDir, t.TempDir())

	// Inject syscallExecFn to return an error so execBundle fails
	oldExec := syscallExecFn
	t.Cleanup(func() { syscallExecFn = oldExec })
	syscallExecFn = func(argv0 string, argv []string, envv []string) error {
		return errors.New("injected exec failure")
	}

	_, cleanup := withLauncherExitTrap(t)
	defer cleanup()

	exited, _ := catchLauncherExit(func() {
		LaunchWithLogLevel(bundle, nil, "warn", "test")
	})

	if !exited {
		t.Fatal("expected LaunchWithLogLevel to call osExitFn after exec failure")
	}
}
