// SPDX-FileCopyrightText: Copyright (c) 2026 provide.io llc. All rights reserved.
// SPDX-License-Identifier: Apache-2.0

package format_2025

import (
	"strings"
	"testing"

	"github.com/provide-io/flavor/go/flavor/pkg/logging"
)

// TestRunBundleWithCwdReadMetadataFailure covers execution.go:273-276:
// when reader.ReadMetadata() fails (bundle has valid index but non-gzip metadata),
// runBundleWithCwd returns an error wrapping the metadata read failure.
func TestRunBundleWithCwdReadMetadataFailure(t *testing.T) {
	cacheRoot := t.TempDir()
	t.Setenv(EnvCacheDir, cacheRoot)
	t.Setenv(EnvValidation, "none")
	t.Setenv(EnvWorkenvCache, "false")

	// Build a bundle with a valid index but non-gzip metadata (raw JSON),
	// which causes ReadMetadata to fail at gzip.NewReader.
	bundle := buildBundleWithBadMetadata(t)

	logger := logging.NewNullLogger()
	_, err := runBundleWithCwd(bundle, nil, t.TempDir(), logger)
	if err == nil {
		t.Fatal("expected error from runBundleWithCwd when ReadMetadata fails, got nil")
	}
	if !strings.Contains(err.Error(), "failed to read metadata") {
		t.Fatalf("expected 'failed to read metadata' in error, got: %v", err)
	}
}
