package main

import (
	"os"
	"os/exec"
	"strings"
	"testing"

	"github.com/provide-io/flavor/go/flavor/pkg/psp/format_2025"
)

// TestLauncherMainPanicRecovery exercises the panic-recovery defer in main().
// The subprocess triggers a panic via executablePathFn, which is recovered and
// prints "PANIC:" to stderr before calling os.Exit(ExitPanic).
func TestLauncherMainPanicRecovery(t *testing.T) {
	t.Parallel()

	cmd := exec.Command(os.Args[0], "-test.run=TestLauncherPanicHelperProcess")
	cmd.Env = append(os.Environ(), "GO_WANT_LAUNCHER_PANIC_HELPER=1")

	out, err := cmd.CombinedOutput()
	if err == nil {
		t.Fatalf("expected process to fail with panic exit code")
	}
	exitErr, ok := err.(*exec.ExitError)
	if !ok {
		t.Fatalf("expected *exec.ExitError, got %T: %v", err, err)
	}
	if exitErr.ExitCode() != format_2025.ExitPanic {
		t.Fatalf("expected exit code %d (ExitPanic), got %d\n%s", format_2025.ExitPanic, exitErr.ExitCode(), out)
	}
	if !strings.Contains(string(out), "PANIC:") {
		t.Fatalf("expected 'PANIC:' in output, got %q", string(out))
	}
}

// TestLauncherPanicHelperProcess is the subprocess helper that causes a panic in main().
func TestLauncherPanicHelperProcess(t *testing.T) {
	if os.Getenv("GO_WANT_LAUNCHER_PANIC_HELPER") != "1" {
		return
	}
	oldFn := executablePathFn
	t.Cleanup(func() { executablePathFn = oldFn })
	// Returning successfully triggers LaunchWithLogLevel with a nonexistent path,
	// but that takes a different path. Instead force a panic from executablePathFn.
	executablePathFn = func() (string, error) {
		panic("test panic from executablePathFn")
	}
	main()
}
