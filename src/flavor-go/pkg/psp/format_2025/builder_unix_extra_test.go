// SPDX-FileCopyrightText: Copyright (c) 2026 provide.io llc. All rights reserved.
// SPDX-License-Identifier: Apache-2.0

//go:build !windows
// +build !windows

package format_2025

import (
	"bytes"
	"testing"

	"github.com/provide-io/flavor/go/flavor/pkg/logging"
)

// TestAtomicReplaceUnixErrorPath covers the os.Rename failure branch in
// atomicReplace (builder_unix.go:20-22) by attempting to rename a nonexistent source.
func TestAtomicReplaceUnixErrorPath(t *testing.T) {
	t.Parallel()

	logger := logging.NewNullLogger()
	err := atomicReplace("/nonexistent/source.bin", "/tmp/dest.bin", logger)
	if err == nil || !bytes.Contains([]byte(err.Error()), []byte("failed to rename file")) {
		t.Fatalf("atomicReplace() error = %v, want 'failed to rename file'", err)
	}
}
