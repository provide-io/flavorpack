// SPDX-FileCopyrightText: Copyright (c) 2026 provide.io llc. All rights reserved.
// SPDX-License-Identifier: Apache-2.0

package format_2025

import (
	"errors"
	"log/slog"
	"os"
	"testing"

	"github.com/provide-io/flavor/go/flavor/pkg/logging"
)

// TestPrepareBundlePathCreateTempFails covers execution.go:77-80
// (createTempFn failure when PSPF is a PE resource).
func TestPrepareBundlePathCreateTempFails(t *testing.T) {
	logger := logging.NewNullLogger()

	// Inject hasPSPFResourceFn to pretend the bundle has a PE resource
	oldHas := hasPSPFResourceFn
	oldRead := readPSPFFromResourceFn
	oldCreate := createTempFn
	t.Cleanup(func() {
		hasPSPFResourceFn = oldHas
		readPSPFFromResourceFn = oldRead
		createTempFn = oldCreate
	})

	hasPSPFResourceFn = func(_ string, _ *slog.Logger) bool { return true }
	readPSPFFromResourceFn = func(_ string, _ *slog.Logger) ([]byte, error) {
		return []byte("pspf-data"), nil
	}
	createTempFn = func(_, _ string) (*os.File, error) {
		return nil, errors.New("injected createTemp failure")
	}

	_, _, err := prepareBundlePath("/fake/bundle.pspf", logger)
	if err == nil {
		t.Fatal("expected error from createTempFn failure")
	}
}

// TestPrepareBundlePathWriteFailure covers execution.go:87-93
// (Write failure after createTemp succeeds).
func TestPrepareBundlePathWriteFailure(t *testing.T) {
	logger := logging.NewNullLogger()

	oldHas := hasPSPFResourceFn
	oldRead := readPSPFFromResourceFn
	oldCreate := createTempFn
	t.Cleanup(func() {
		hasPSPFResourceFn = oldHas
		readPSPFFromResourceFn = oldRead
		createTempFn = oldCreate
	})

	pspfData := []byte("pspf-data")
	hasPSPFResourceFn = func(_ string, _ *slog.Logger) bool { return true }
	readPSPFFromResourceFn = func(_ string, _ *slog.Logger) ([]byte, error) {
		return pspfData, nil
	}

	// Create a file, then close it so writes fail with "file already closed"
	createTempFn = func(dir, pattern string) (*os.File, error) {
		f, err := os.CreateTemp(dir, pattern)
		if err != nil {
			return nil, err
		}
		// Close it immediately — subsequent Write will fail
		f.Close()
		return f, nil
	}

	_, _, err := prepareBundlePath("/fake/bundle.pspf", logger)
	if err == nil {
		t.Fatal("expected error from Write failure on closed temp file")
	}
}

// TestPrepareBundlePathIncompleteWrite covers execution.go:96-101
// (incomplete write: bytesWritten != len(pspfData)).
// We create a temp file that succeeds on Write but returns fewer bytes.
// Since we can't easily make os.File return incomplete writes, we test this
// path indirectly via a pipe that has limited capacity.
// Actually this path requires bytesWritten < len(pspfData) with err==nil,
// which is impossible for a normal file. We verify the normal write works correctly,
// and accept that this particular unreachable check exists.
// Note: file.Write returning (n<len, nil) is impossible per Go's io.Writer contract.
// We leave this test as a compilation smoke test.
func TestPrepareBundlePathNormalPEResourceExtraction(t *testing.T) {
	logger := logging.NewNullLogger()

	oldHas := hasPSPFResourceFn
	oldRead := readPSPFFromResourceFn
	t.Cleanup(func() {
		hasPSPFResourceFn = oldHas
		readPSPFFromResourceFn = oldRead
	})

	pspfData := []byte("pspf-data")
	hasPSPFResourceFn = func(_ string, _ *slog.Logger) bool { return true }
	readPSPFFromResourceFn = func(_ string, _ *slog.Logger) ([]byte, error) {
		return pspfData, nil
	}

	bundlePath, cleanup, err := prepareBundlePath("/fake/bundle.pspf", logger)
	if err != nil {
		t.Fatalf("prepareBundlePath() error = %v", err)
	}
	if cleanup == nil {
		t.Fatal("expected cleanup function for PE resource path")
	}
	if bundlePath == "" {
		t.Fatal("expected non-empty bundle path")
	}
	defer cleanup()
}

// TestRunBundleWithCwdReaderCloseLogs covers execution.go:145-147
// (reader.Close failure logs error).
func TestRunBundleWithCwdReaderCloseLogs(t *testing.T) {
	cacheRoot := t.TempDir()
	t.Setenv(EnvCacheDir, cacheRoot)
	t.Setenv(EnvValidation, "none")
	t.Setenv(EnvWorkenvCache, "false")

	bundle := buildSingleSlotBundleForTests(t, []byte("data"), []byte("data"), nil, SlotMetadata{
		ID:     "slot",
		Target: "{workenv}",
	}, 0, false)

	oldClose := runBundleReaderCloseFn
	t.Cleanup(func() { runBundleReaderCloseFn = oldClose })
	runBundleReaderCloseFn = func(r *Reader) error {
		_ = r.Close()
		return errors.New("injected reader close failure")
	}

	logger := logging.NewNullLogger()
	// The close error should be logged but not prevent the function from returning a cmd
	cmd, err := runBundleWithCwd(bundle, nil, t.TempDir(), logger)
	if err != nil {
		t.Fatalf("runBundleWithCwd() error = %v (close error should be non-fatal)", err)
	}
	if cmd == nil {
		t.Fatal("expected non-nil cmd")
	}
}
