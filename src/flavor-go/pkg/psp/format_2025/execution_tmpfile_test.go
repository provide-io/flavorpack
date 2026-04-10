package format_2025

import (
	"errors"
	"log/slog"
	"os"
	"testing"

	"github.com/provide-io/flavor/go/flavor/pkg/logging"
)

// TestPrepareBundlePathIncompleteWrite covers execution.go:105-110
// (bytesWritten != len(pspfData) → incomplete write error).
func TestPrepareBundlePathIncompleteWrite(t *testing.T) {
	bundle := buildLauncherTestBundle(t)
	data, err := os.ReadFile(bundle)
	if err != nil {
		t.Fatalf("ReadFile() error = %v", err)
	}

	// Inject hasPSPFResourceFn to claim PE resource is present
	oldHas := hasPSPFResourceFn
	t.Cleanup(func() { hasPSPFResourceFn = oldHas })
	hasPSPFResourceFn = func(_ string, _ *slog.Logger) bool { return true }

	// Inject readPSPFFromResourceFn to return actual bundle data
	oldRead := readPSPFFromResourceFn
	t.Cleanup(func() { readPSPFFromResourceFn = oldRead })
	readPSPFFromResourceFn = func(_ string, _ *slog.Logger) ([]byte, error) { return data, nil }

	// Inject tmpFileWriteFn to return short write (0 bytes, no error)
	oldWrite := tmpFileWriteFn
	t.Cleanup(func() { tmpFileWriteFn = oldWrite })
	tmpFileWriteFn = func(f *os.File, d []byte) (int, error) {
		_ = f.Close() // close real file to avoid FD leak
		return 0, nil // zero bytes written, no error → triggers incomplete write check
	}

	logger := logging.NewNullLogger()
	_, _, prepErr := prepareBundlePath(bundle, logger)
	if prepErr == nil {
		t.Fatal("expected error from prepareBundlePath due to incomplete write")
	}
}

// TestPrepareBundlePathCloseFailure covers execution.go:113-118
// (tmpFile.Close returns error → error returned from prepareBundlePath).
func TestPrepareBundlePathCloseFailure(t *testing.T) {
	bundle := buildLauncherTestBundle(t)
	data, err := os.ReadFile(bundle)
	if err != nil {
		t.Fatalf("ReadFile() error = %v", err)
	}

	// Inject hasPSPFResourceFn and readPSPFFromResourceFn
	oldHas := hasPSPFResourceFn
	t.Cleanup(func() { hasPSPFResourceFn = oldHas })
	hasPSPFResourceFn = func(_ string, _ *slog.Logger) bool { return true }

	oldRead := readPSPFFromResourceFn
	t.Cleanup(func() { readPSPFFromResourceFn = oldRead })
	readPSPFFromResourceFn = func(_ string, _ *slog.Logger) ([]byte, error) { return data, nil }

	// Inject tmpFileWriteFn to report full write (so we get past the incomplete write check)
	oldWrite := tmpFileWriteFn
	t.Cleanup(func() { tmpFileWriteFn = oldWrite })
	tmpFileWriteFn = func(f *os.File, d []byte) (int, error) {
		// Write just enough bytes to satisfy len(d) check but don't actually write all
		n, err := f.Write(d)
		return n, err
	}

	// Inject tmpFileCloseFn to return an error
	oldClose := tmpFileCloseFn
	t.Cleanup(func() { tmpFileCloseFn = oldClose })
	tmpFileCloseFn = func(f *os.File) error {
		_ = f.Close() // close for real to avoid FD leak
		return errors.New("injected close failure")
	}

	logger := logging.NewNullLogger()
	_, _, prepErr := prepareBundlePath(bundle, logger)
	if prepErr == nil {
		t.Fatal("expected error from prepareBundlePath due to close failure")
	}
}
