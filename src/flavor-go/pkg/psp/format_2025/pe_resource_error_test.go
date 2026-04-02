package format_2025

import (
	"errors"
	"testing"

	"github.com/hashicorp/go-hclog"
)

// stubPEResourceReadError injects hasPSPFResourceFn to return true and
// readPSPFFromResourceFn to return an error. This makes prepareBundlePath
// return an error at the readPSPFFromResourceFn call (line 67-70 of execution.go).
// Returns a restore function.
func stubPEResourceReadError(t *testing.T) func() {
	t.Helper()
	oldHas := hasPSPFResourceFn
	oldRead := readPSPFFromResourceFn
	hasPSPFResourceFn = func(path string, logger hclog.Logger) bool { return true }
	readPSPFFromResourceFn = func(path string, logger hclog.Logger) ([]byte, error) {
		return nil, errors.New("injected: failed to read PSPF from PE resource")
	}
	return func() {
		hasPSPFResourceFn = oldHas
		readPSPFFromResourceFn = oldRead
	}
}

// TestPrepareBundlePathReadResourceError covers lines 68-70 in execution.go:
// when readPSPFFromResourceFn returns an error, prepareBundlePath returns an error.
func TestPrepareBundlePathReadResourceError(t *testing.T) {
	restore := stubPEResourceReadError(t)
	defer restore()

	logger := hclog.NewNullLogger()
	_, _, err := prepareBundlePath("/fake/exe", logger)
	if err == nil {
		t.Fatal("expected error when readPSPFFromResourceFn fails")
	}
}

// TestShowBundleInfoPrepareBundlePathError covers lines 18-21 in launcher_cli.go:
// when prepareBundlePath returns an error, showBundleInfo calls osExitFn(1).
func TestShowBundleInfoPrepareBundlePathError(t *testing.T) {
	restore := stubPEResourceReadError(t)
	defer restore()

	exitCode, panicked := withStubbedExit(func() {
		showBundleInfo("/fake/exe", hclog.NewNullLogger())
	})
	if panicked {
		t.Fatal("unexpected non-exit panic in showBundleInfo")
	}
	if exitCode != 1 {
		t.Fatalf("expected exit code 1, got %d", exitCode)
	}
}

// TestShowMetadataPrepareBundlePathError covers lines 196-199 in launcher_cli.go:
// when prepareBundlePath returns an error, showMetadata calls osExitFn(1).
func TestShowMetadataPrepareBundlePathError(t *testing.T) {
	restore := stubPEResourceReadError(t)
	defer restore()

	exitCode, panicked := withStubbedExit(func() {
		showMetadata("/fake/exe", hclog.NewNullLogger())
	})
	if panicked {
		t.Fatal("unexpected non-exit panic in showMetadata")
	}
	if exitCode != 1 {
		t.Fatalf("expected exit code 1, got %d", exitCode)
	}
}

// TestVerifyBundlePrepareBundlePathError covers lines 234-237 in launcher_cli.go:
// when prepareBundlePath returns an error, verifyBundle calls osExitFn(1).
func TestVerifyBundlePrepareBundlePathError(t *testing.T) {
	restore := stubPEResourceReadError(t)
	defer restore()

	exitCode, panicked := withStubbedExit(func() {
		verifyBundle("/fake/exe", hclog.NewNullLogger())
	})
	if panicked {
		t.Fatal("unexpected non-exit panic in verifyBundle")
	}
	if exitCode != 1 {
		t.Fatalf("expected exit code 1, got %d", exitCode)
	}
}

// TestExtractSlotPrepareBundlePathError covers lines 106-109 in launcher_cli.go:
// when prepareBundlePath returns an error, extractSlot calls osExitFn(1).
func TestExtractSlotPrepareBundlePathError(t *testing.T) {
	restore := stubPEResourceReadError(t)
	defer restore()

	exitCode, panicked := withStubbedExit(func() {
		extractSlot("/fake/exe", "0", t.TempDir(), hclog.NewNullLogger())
	})
	if panicked {
		t.Fatal("unexpected non-exit panic in extractSlot")
	}
	if exitCode != 1 {
		t.Fatalf("expected exit code 1, got %d", exitCode)
	}
}

// TestRunBundleWithCwdPrepareBundlePathErrorPE covers lines 135-138 in execution.go:
// when prepareBundlePath returns an error (via PE resource path), runBundleWithCwd returns it.
func TestRunBundleWithCwdPrepareBundlePathErrorPE(t *testing.T) {
	restore := stubPEResourceReadError(t)
	defer restore()

	logger := hclog.NewNullLogger()
	_, err := runBundleWithCwd("/fake/exe", nil, t.TempDir(), logger)
	if err == nil {
		t.Fatal("expected error when prepareBundlePath fails in runBundleWithCwd")
	}
}

// TestRunBundleWithCwdPrepareBundlePathCleanup covers lines 139-141 in execution.go:
// when prepareBundlePath returns a temp path with a cleanup function, the cleanup
// is deferred. We trigger this by having readPSPFFromResourceFn succeed (return a
// valid bundle via the stub) but NewReaderWithLogger subsequently fail.
func TestRunBundleWithCwdPrepareBundlePathCleanup(t *testing.T) {
	oldHas := hasPSPFResourceFn
	oldRead := readPSPFFromResourceFn
	t.Cleanup(func() {
		hasPSPFResourceFn = oldHas
		readPSPFFromResourceFn = oldRead
	})
	// Return "has resource" = true with invalid (tiny) bundle data → NewReaderWithLogger fails
	hasPSPFResourceFn = func(path string, logger hclog.Logger) bool { return true }
	readPSPFFromResourceFn = func(path string, logger hclog.Logger) ([]byte, error) {
		return []byte("not-a-real-pspf-bundle-data"), nil
	}

	logger := hclog.NewNullLogger()
	_, err := runBundleWithCwd("/fake/exe", nil, t.TempDir(), logger)
	// We expect an error (NewReaderWithLogger fails on tiny data).
	if err == nil {
		t.Fatal("expected error when bundle data is invalid in runBundleWithCwd")
	}
}

// TestExtractSlotInvalidSlotIndex covers lines 99-102 in launcher_cli.go:
// when the slot string is not a valid integer, extractSlot calls osExitFn(1).
func TestExtractSlotInvalidSlotIndex(t *testing.T) {
	bundle := buildLauncherTestBundle(t)
	logger := hclog.NewNullLogger()

	exitCode, panicked := withStubbedExit(func() {
		extractSlot(bundle, "not-an-int", t.TempDir(), logger)
	})
	if panicked {
		t.Fatal("unexpected non-exit panic in extractSlot with invalid slot index")
	}
	if exitCode != 1 {
		t.Fatalf("expected exit code 1 for invalid slot index, got %d", exitCode)
	}
}

// TestExtractSlotOutOfRange covers lines 131-134 in launcher_cli.go:
// when the slot index is out of range, extractSlot calls osExitFn(1).
func TestExtractSlotOutOfRange(t *testing.T) {
	bundle := buildLauncherTestBundle(t)
	logger := hclog.NewNullLogger()

	exitCode, panicked := withStubbedExit(func() {
		extractSlot(bundle, "999", t.TempDir(), logger)
	})
	if panicked {
		t.Fatal("unexpected non-exit panic in extractSlot with out-of-range slot")
	}
	if exitCode != 1 {
		t.Fatalf("expected exit code 1 for out-of-range slot, got %d", exitCode)
	}
}
