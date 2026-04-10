package format_2025

import (
	"os"
	"path/filepath"
	"runtime"
	"testing"

	"github.com/provide-io/flavor/go/flavor/pkg/logging"
)

// TestSpawnBundleSuccessPathNoOpExit exercises the success branch of spawnBundle
// where cmd.Wait() returns nil. With a no-op osExitFn, execution continues past
// osExitFn(0) to the "unreachable code" logger.Error + return statement.
func TestSpawnBundleSuccessPathNoOpExit(t *testing.T) {
	if runtime.GOOS == "windows" {
		t.Skip("spawn test uses /bin/true which is not available on Windows")
	}

	bundle := buildLauncherTestBundle(t)
	logger := logging.NewNullLogger()

	cacheRoot := t.TempDir()
	t.Setenv(EnvCacheDir, cacheRoot)
	t.Setenv(EnvWorkenvCache, "false")
	t.Setenv(EnvValidation, "none")

	old := osExitFn
	var capturedCode int
	osExitFn = func(code int) { capturedCode = code }
	t.Cleanup(func() { osExitFn = old })

	// With a no-op osExitFn, spawnBundle should return the "unreachable code" error
	// after the process exits successfully (exit code 0).
	err := spawnBundle(bundle, nil, t.TempDir(), logger)
	if err == nil {
		t.Fatal("expected error from no-op osExitFn path (unreachable code executed)")
	}
	if capturedCode != 0 {
		t.Fatalf("expected osExitFn called with code 0, got %d", capturedCode)
	}
}

// TestSpawnBundleFailingCommandNoOpExit exercises the non-zero exit branch
// of spawnBundle. When the child exits non-zero and osExitFn is a no-op,
// execution continues past osExitFn(exitCode) to the CRITICAL logger.Error.
// After that, because the type assertion succeeded (we have an *exec.ExitError),
// the function falls through to the "Failed to extract exit code" error return.
func TestSpawnBundleFailingCommandNoOpExit(t *testing.T) {
	if runtime.GOOS == "windows" {
		t.Skip("spawn test uses /bin/false which is not available on Windows")
	}

	// Build a bundle whose command is /bin/false (exits 1).
	metadata := Metadata{
		Format:        "PSPF/2025",
		FormatVersion: "2025.0",
		Package:       PackageInfo{Name: "demo-fail", Version: "1.0.0"},
		Execution:     &ExecutionInfo{PrimarySlot: 0, Command: "/bin/false"},
		Build:         &BuildInfo{Tool: "test"},
	}
	bundle := buildMultiSlotBundleForTests(t, []multiSlotBundleSpec{
		{
			meta:         SlotMetadata{ID: "main", Target: "{workenv}"},
			storedData:   []byte(""),
			originalData: []byte(""),
		},
	}, metadata)

	logger := logging.NewNullLogger()
	cacheRoot := t.TempDir()
	t.Setenv(EnvCacheDir, cacheRoot)
	t.Setenv(EnvWorkenvCache, "false")
	t.Setenv(EnvValidation, "none")

	old := osExitFn
	var capturedCode int
	osExitFn = func(code int) { capturedCode = code }
	t.Cleanup(func() { osExitFn = old })

	// With a no-op osExitFn, spawnBundle should return an error.
	// The ExitError path calls osExitFn(exitCode) (no-op) then logs
	// "CRITICAL: os.Exit returned unexpectedly" and falls through to
	// "Failed to extract exit code" return.
	err := spawnBundle(bundle, nil, t.TempDir(), logger)
	// The function should return the wrapped exit error from cmd.Wait.
	if err == nil {
		t.Fatal("expected error when child process exits non-zero with no-op osExitFn")
	}
	if capturedCode == 0 {
		t.Fatal("expected osExitFn called with non-zero exit code")
	}
}

// TestSpawnBundleWorkenvSetup exercises spawnBundle with FLAVOR_WORKENV set.
func TestSpawnBundleWorkenvSetup(t *testing.T) {
	if runtime.GOOS == "windows" {
		t.Skip("spawn test uses /bin/true which is not available on Windows")
	}

	bundle := buildLauncherTestBundle(t)
	logger := logging.NewNullLogger()

	workenvDir := filepath.Join(t.TempDir(), "custom_workenv")
	t.Setenv(EnvWorkenv, workenvDir)
	t.Setenv(EnvWorkenvCache, "false")
	t.Setenv(EnvValidation, "none")

	old := osExitFn
	osExitFn = func(code int) {}
	t.Cleanup(func() { osExitFn = old })

	// Should either error or succeed — just verify no panic.
	_ = spawnBundle(bundle, nil, t.TempDir(), logger)
	// Remove the custom workenv env after the test to avoid polluting others.
	os.Unsetenv(EnvWorkenv)
}

// TestSpawnBundlePrepareFails verifies that spawnBundle returns a non-nil error
// when the bundle path is invalid (prepareBundlePath/NewReaderWithLogger fails).
func TestSpawnBundlePrepareFails(t *testing.T) {
	logger := logging.NewNullLogger()
	err := spawnBundle("/nonexistent/path/fake.psp", nil, t.TempDir(), logger)
	if err == nil {
		t.Fatal("expected error for non-existent bundle path")
	}
}
