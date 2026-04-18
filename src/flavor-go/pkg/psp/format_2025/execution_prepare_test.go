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

func TestPrepareBundlePathPEResourceSuccess(t *testing.T) {
	// Override hasPSPFResourceFn to return true
	// Override readPSPFFromResourceFn to return test bytes
	oldHas := hasPSPFResourceFn
	oldRead := readPSPFFromResourceFn
	t.Cleanup(func() {
		hasPSPFResourceFn = oldHas
		readPSPFFromResourceFn = oldRead
	})

	pspfData := []byte("fake-pspf-data-long-enough")
	hasPSPFResourceFn = func(path string, logger *slog.Logger) bool { return true }
	readPSPFFromResourceFn = func(path string, logger *slog.Logger) ([]byte, error) {
		return pspfData, nil
	}

	logger := logging.NewNullLogger()
	bundlePath, cleanup, err := prepareBundlePath("/fake/exe", logger)
	if err != nil {
		t.Fatalf("prepareBundlePath() error = %v", err)
	}
	if cleanup == nil {
		t.Fatal("expected cleanup function, got nil")
	}
	defer cleanup()

	data, err := os.ReadFile(bundlePath)
	if err != nil {
		t.Fatalf("ReadFile(bundlePath) error = %v", err)
	}
	if string(data) != string(pspfData) {
		t.Fatalf("unexpected temp file contents: %q", string(data))
	}
}

func TestPrepareBundlePathPEResourceReadError(t *testing.T) {
	oldHas := hasPSPFResourceFn
	oldRead := readPSPFFromResourceFn
	t.Cleanup(func() {
		hasPSPFResourceFn = oldHas
		readPSPFFromResourceFn = oldRead
	})

	hasPSPFResourceFn = func(path string, logger *slog.Logger) bool { return true }
	readPSPFFromResourceFn = func(path string, logger *slog.Logger) ([]byte, error) {
		return nil, errors.New("resource read failed")
	}

	logger := logging.NewNullLogger()
	_, _, err := prepareBundlePath("/fake/exe", logger)
	if err == nil {
		t.Fatal("expected error from PE resource read failure")
	}
}

func TestPrepareBundlePathNoPEResource(t *testing.T) {
	oldHas := hasPSPFResourceFn
	t.Cleanup(func() { hasPSPFResourceFn = oldHas })
	hasPSPFResourceFn = func(path string, logger *slog.Logger) bool { return false }

	logger := logging.NewNullLogger()
	bundlePath, cleanup, err := prepareBundlePath("/some/bundle.pspf", logger)
	if err != nil {
		t.Fatalf("prepareBundlePath() error = %v", err)
	}
	if cleanup != nil {
		t.Fatal("expected nil cleanup for non-PE path")
	}
	if bundlePath != "/some/bundle.pspf" {
		t.Fatalf("expected original path, got %q", bundlePath)
	}
}

func TestRemoveAllQuietlyLogsOnError(t *testing.T) {
	old := removeAllFn
	t.Cleanup(func() { removeAllFn = old })
	removeAllFn = func(path string) error {
		return errors.New("remove failed")
	}

	// Should not panic — just logs the error
	removeAllQuietly("/fake/path", "test-context", logging.NewNullLogger())
}
