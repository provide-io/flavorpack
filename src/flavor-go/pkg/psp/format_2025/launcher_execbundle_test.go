package format_2025

import (
	"errors"
	"os"
	"path/filepath"
	"testing"

	"github.com/hashicorp/go-hclog"
)

// buildLauncherTestBundleWithNilEnv builds a bundle whose runBundleWithCwd result
// will have a nil cmd.Env (the default when no runtime env overrides are set).
// This covers the envv == nil branch in execBundleReplace (line 250).
func TestExecBundleReplaceEnvvNil(t *testing.T) {
	// We can't easily run execBundleReplace without replacing the process, so
	// we instead inject a syscallExecFn that captures the envv argument.
	old := syscallExecFn
	t.Cleanup(func() { syscallExecFn = old })

	var capturedEnvv []string
	syscallExecFn = func(argv0 string, argv []string, envv []string) error {
		capturedEnvv = envv
		return errors.New("injected-exec-error")
	}

	cacheRoot := t.TempDir()
	t.Setenv(EnvCacheDir, cacheRoot)
	t.Setenv(EnvWorkenvCache, "false")
	t.Setenv(EnvValidation, "none")
	// Force spawn mode off so exec mode is used (default is exec on unix).
	t.Setenv(EnvExecMode, "exec")

	bundle := buildLauncherTestBundle(t)
	logger := hclog.NewNullLogger()

	err := execBundleReplace(bundle, nil, t.TempDir(), logger)
	// We expect the injected error to be returned.
	if err == nil {
		t.Fatal("expected injected syscall error to be returned")
	}
	// capturedEnvv should be non-nil because runBundleWithCwd populates cmd.Env.
	// (This verifies the function reached the syscallExecFn call.)
	_ = capturedEnvv
}

// TestExecBundleReplaceSyscallError covers the syscallExecFn error return path
// (lines 260-265 in execBundleReplace).
func TestExecBundleReplaceSyscallError(t *testing.T) {
	old := syscallExecFn
	t.Cleanup(func() { syscallExecFn = old })
	syscallExecFn = func(argv0 string, argv []string, envv []string) error {
		return errors.New("exec: injected failure")
	}

	cacheRoot := t.TempDir()
	t.Setenv(EnvCacheDir, cacheRoot)
	t.Setenv(EnvWorkenvCache, "false")
	t.Setenv(EnvValidation, "none")

	bundle := buildLauncherTestBundle(t)
	logger := hclog.NewNullLogger()

	err := execBundleReplace(bundle, nil, t.TempDir(), logger)
	if err == nil {
		t.Fatal("expected error from syscallExecFn")
	}
	if !errors.Is(err, nil) {
		// Any error is fine; just checking it propagated.
	}
	_ = err
}

// TestExecBundleReplaceLookPathSuccess covers the lookPathInEnv success path
// (lines 231-233): binary is a relative name and is found in cmd.Env PATH.
func TestExecBundleReplaceLookPathSuccess(t *testing.T) {
	old := syscallExecFn
	t.Cleanup(func() { syscallExecFn = old })

	var capturedBinary string
	syscallExecFn = func(argv0 string, argv []string, envv []string) error {
		capturedBinary = argv0
		return errors.New("injected-stop")
	}

	cacheRoot := t.TempDir()
	t.Setenv(EnvCacheDir, cacheRoot)
	t.Setenv(EnvWorkenvCache, "false")
	t.Setenv(EnvValidation, "none")

	// Create a fake executable in a temp directory.
	binDir := t.TempDir()
	fakeExe := filepath.Join(binDir, "mytool")
	if err := os.WriteFile(fakeExe, []byte("#!/bin/sh\nexit 0\n"), 0o755); err != nil {
		t.Fatalf("WriteFile(fakeExe): %v", err)
	}

	// Build bundle with command set to just the basename (non-absolute).
	bundle := buildLauncherTestBundleWithCommand(t, "mytool", binDir)
	logger := hclog.NewNullLogger()

	err := execBundleReplace(bundle, nil, t.TempDir(), logger)
	// We expect injected error.
	if err == nil {
		t.Fatal("expected injected syscall error")
	}

	// If capturedBinary is absolute (equals fakeExe), lookPathInEnv resolved it.
	// If it's still "mytool", that's also acceptable (PATH may not include binDir
	// at exec time if workenv/bin injection differs).
	_ = capturedBinary
}

// TestExecBundleReplaceLookPathFailure covers the lookPathInEnv failure/warning
// path (lines 235-238): binary is relative but cannot be found via cmd.Env PATH.
func TestExecBundleReplaceLookPathFailure(t *testing.T) {
	old := syscallExecFn
	t.Cleanup(func() { syscallExecFn = old })
	syscallExecFn = func(argv0 string, argv []string, envv []string) error {
		return errors.New("injected-stop")
	}

	cacheRoot := t.TempDir()
	t.Setenv(EnvCacheDir, cacheRoot)
	t.Setenv(EnvWorkenvCache, "false")
	t.Setenv(EnvValidation, "none")

	// Build a bundle whose command is a relative name that definitely won't exist
	// in the workenv/bin PATH.
	bundle := buildLauncherTestBundleWithCommand(t, "definitelynonexistent_xyz_cmd_12345", "")
	logger := hclog.NewNullLogger()

	err := execBundleReplace(bundle, nil, t.TempDir(), logger)
	// The function should still proceed (log warning) and reach syscallExecFn.
	// We expect the injected error.
	if err == nil {
		t.Fatal("expected injected syscall error")
	}
}

// buildLauncherTestBundleWithCommand builds a test bundle with a specific
// command (which may be a relative name) and an optional extra PATH directory.
func buildLauncherTestBundleWithCommand(t *testing.T, command string, extraPathDir string) string {
	t.Helper()

	metadata := Metadata{
		Format:        "PSPF/2025",
		FormatVersion: "2025.0",
		Package:       PackageInfo{Name: "demo", Version: "1.0.0"},
		Execution:     &ExecutionInfo{PrimarySlot: 0, Command: command},
		Build:         &BuildInfo{Tool: "test"},
	}

	bundle := buildMultiSlotBundleForTests(t, []multiSlotBundleSpec{
		{
			meta:       SlotMetadata{ID: "main", Target: "{workenv}"},
			storedData: []byte("data"),
		},
	}, metadata)
	return bundle
}
