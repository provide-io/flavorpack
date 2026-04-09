package format_2025

import (
	"strings"
	"testing"

	"github.com/provide-io/flavor/go/flavor/pkg/logging"
)

// TestExecBundleReplaceSyscallExecNilError covers the "impossible" path at
// lines 269-270 in execBundleReplace: when syscallExecFn returns nil (should
// never happen in practice, but the code guards against it).
func TestExecBundleReplaceSyscallExecNilError(t *testing.T) {
	old := syscallExecFn
	syscallExecFn = func(argv0 string, argv []string, envv []string) error {
		return nil // Simulate "impossible" nil return from syscall.Exec
	}
	t.Cleanup(func() { syscallExecFn = old })

	cacheRoot := t.TempDir()
	t.Setenv(EnvCacheDir, cacheRoot)
	t.Setenv(EnvWorkenvCache, "false")
	t.Setenv(EnvValidation, "none")

	bundle := buildLauncherTestBundle(t)
	logger := logging.NewNullLogger()

	err := execBundleReplace(bundle, nil, t.TempDir(), logger)
	if err == nil {
		t.Fatal("expected error from nil syscallExec return")
	}
	if !strings.Contains(err.Error(), "unexpectedly") {
		t.Fatalf("unexpected error message: %v", err)
	}
}
