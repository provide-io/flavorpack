// SPDX-FileCopyrightText: Copyright (c) 2026 provide.io llc. All rights reserved.
// SPDX-License-Identifier: Apache-2.0

package format_2025

import (
	"testing"

	"github.com/provide-io/flavor/go/flavor/pkg/logging"
)

// TestRunBundleWithCwdEnumerateAndExecuteNoMatches covers execution.go:489-491:
// the else branch in enumerate_and_execute when filepath.Glob returns no matches.
// When the pattern finds no files, cmdToRun = command (the fallback path).
func TestRunBundleWithCwdEnumerateAndExecuteNoMatches(t *testing.T) {
	cacheRoot := t.TempDir()
	t.Setenv(EnvCacheDir, cacheRoot)
	t.Setenv(EnvValidation, "none")
	t.Setenv(EnvWorkenvCache, "false")

	// Build a bundle with an enumerate_and_execute setup command that
	// references a path with no matching files (pattern "*.nonexistent").
	// Glob will return empty matches, so cmdToRun = command (else branch).
	bundle := buildMultiSlotBundleForTests(t, []multiSlotBundleSpec{
		{
			meta:         SlotMetadata{ID: "slot", Target: "{workenv}"},
			storedData:   []byte("data"),
			originalData: []byte("data"),
		},
	}, Metadata{
		Format:        "PSPF/2025",
		FormatVersion: "2025.0",
		Package:       PackageInfo{Name: "test", Version: "1.0.0"},
		SetupCommands: []interface{}{
			map[string]interface{}{
				"type":    "enumerate_and_execute",
				"command": "/bin/true",
				"enumerate": map[string]interface{}{
					"path":    "{workenv}",
					"pattern": "*.nonexistent-xyz-pattern",
				},
			},
		},
		Execution: &ExecutionInfo{PrimarySlot: 0, Command: "/bin/true"},
		Build:     &BuildInfo{Tool: "test"},
	})

	logger := logging.NewNullLogger()
	// Should succeed: empty glob matches falls back to running command directly.
	cmd, err := runBundleWithCwd(bundle, nil, t.TempDir(), logger)
	if err != nil {
		t.Fatalf("runBundleWithCwd() error = %v", err)
	}
	if cmd == nil {
		t.Fatal("expected non-nil exec.Cmd")
	}
}

// TestRunBundleWithCwdEnumerateAndExecuteGlobError covers execution.go:481-483:
// when filepath.Glob returns an error due to an invalid pattern (e.g., "[bad").
// The error is logged as a warning but execution continues.
func TestRunBundleWithCwdEnumerateAndExecuteGlobError(t *testing.T) {
	cacheRoot := t.TempDir()
	t.Setenv(EnvCacheDir, cacheRoot)
	t.Setenv(EnvValidation, "none")
	t.Setenv(EnvWorkenvCache, "false")

	// "[bad" is an invalid glob pattern — missing closing bracket causes Glob to error.
	bundle := buildMultiSlotBundleForTests(t, []multiSlotBundleSpec{
		{
			meta:         SlotMetadata{ID: "slot", Target: "{workenv}"},
			storedData:   []byte("data"),
			originalData: []byte("data"),
		},
	}, Metadata{
		Format:        "PSPF/2025",
		FormatVersion: "2025.0",
		Package:       PackageInfo{Name: "test", Version: "1.0.0"},
		SetupCommands: []interface{}{
			map[string]interface{}{
				"type":    "enumerate_and_execute",
				"command": "/bin/true",
				"enumerate": map[string]interface{}{
					"path":    "{workenv}",
					"pattern": "[bad-unclosed-bracket",
				},
			},
		},
		Execution: &ExecutionInfo{PrimarySlot: 0, Command: "/bin/true"},
		Build:     &BuildInfo{Tool: "test"},
	})

	logger := logging.NewNullLogger()
	// Glob error is a warning; execution continues.
	cmd, err := runBundleWithCwd(bundle, nil, t.TempDir(), logger)
	if err != nil {
		t.Fatalf("runBundleWithCwd() error = %v (Glob error should be warned, not fatal)", err)
	}
	if cmd == nil {
		t.Fatal("expected non-nil exec.Cmd")
	}
}
