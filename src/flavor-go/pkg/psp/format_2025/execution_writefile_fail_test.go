// SPDX-FileCopyrightText: Copyright (c) 2026 provide.io llc. All rights reserved.
// SPDX-License-Identifier: Apache-2.0

package format_2025

import (
	"archive/tar"
	"bytes"
	"runtime"
	"strings"
	"testing"

	"github.com/provide-io/flavor/go/flavor/pkg/logging"
)

// TestRunBundleWriteFileValidatedFails covers execution.go:519-522:
// when writeFileValidated returns an error because the parent path component
// of the target write_file path is a regular file (not a directory).
//
// Strategy:
//  1. Build a tar-based slot that extracts a regular file named "blocked" into workenv.
//  2. Bundle's SetupCommands contains write_file targeting "{workenv}/blocked/output.txt".
//  3. After extraction, workenv/blocked is a regular file, so os.WriteFile on
//     workenv/blocked/output.txt fails with "not a directory".
func TestRunBundleWriteFileValidatedFails(t *testing.T) {
	if runtime.GOOS == "windows" {
		t.Skip("file-as-directory blocking not reliable on Windows")
	}

	t.Setenv(EnvCacheDir, t.TempDir())
	t.Setenv(EnvValidation, "none")
	t.Setenv(EnvWorkenvCache, "false")

	// Build a tar that contains a regular file named "blocked".
	// When extracted to {workenv}, it becomes workenv/blocked (a regular file).
	var buf bytes.Buffer
	tw := tar.NewWriter(&buf)
	content := []byte("i am a blocker file")
	if err := tw.WriteHeader(&tar.Header{
		Typeflag: tar.TypeReg,
		Name:     "blocked",
		Mode:     0o644,
		Size:     int64(len(content)),
	}); err != nil {
		t.Fatalf("WriteHeader: %v", err)
	}
	if _, err := tw.Write(content); err != nil {
		t.Fatalf("tar.Write: %v", err)
	}
	if err := tw.Close(); err != nil {
		t.Fatalf("tar.Close: %v", err)
	}
	tarData := buf.Bytes()

	bundle := buildMultiSlotBundleForTests(t, []multiSlotBundleSpec{
		{
			meta:         SlotMetadata{ID: "tar-slot", Target: "{workenv}"},
			storedData:   tarData,
			originalData: tarData,
			operations:   []uint8{OP_TAR},
		},
	}, Metadata{
		Format:        "PSPF/2025",
		FormatVersion: "2025.0",
		Package:       PackageInfo{Name: "write-fail-test", Version: "1.0.0"},
		SetupCommands: []interface{}{
			map[string]interface{}{
				"type":    "write_file",
				"path":    "{workenv}/blocked/output.txt",
				"content": "hello",
			},
		},
		Execution: &ExecutionInfo{PrimarySlot: 0, Command: "/bin/true"},
		Build:     &BuildInfo{Tool: "test"},
	})

	logger := logging.NewNullLogger()
	_, err := runBundleWithCwd(bundle, nil, t.TempDir(), logger)
	if err == nil {
		t.Fatal("expected error when write_file target parent is a regular file, got nil")
	}
	if !strings.Contains(err.Error(), "failed to write file") {
		t.Logf("note: got error %v (expected 'failed to write file' in message)", err)
	}
}
