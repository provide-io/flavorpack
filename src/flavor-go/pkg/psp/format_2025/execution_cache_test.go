// SPDX-FileCopyrightText: Copyright (c) 2026 provide.io llc. All rights reserved.
// SPDX-License-Identifier: Apache-2.0

package format_2025

import (
	"encoding/json"
	"os"
	"path/filepath"
	"strings"
	"testing"

	"github.com/provide-io/flavor/go/flavor/pkg/logging"
)

func TestValidatePackageChecksumAndSavePackageChecksum(t *testing.T) {
	logger := logging.NewNullLogger()
	paths := NewWorkenvPaths(t.TempDir(), "/tmp/demo.pspf")

	if err := savePackageChecksum(paths, 0x12345678, logger); err != nil {
		t.Fatalf("savePackageChecksum() error = %v", err)
	}

	data, err := os.ReadFile(paths.ChecksumFile())
	if err != nil {
		t.Fatalf("ReadFile() error = %v", err)
	}
	if got := strings.TrimSpace(string(data)); got != "12345678" {
		t.Fatalf("unexpected checksum file contents %q", got)
	}

	valid, err := validatePackageChecksum(paths, 0x12345678, logger)
	if err != nil {
		t.Fatalf("validatePackageChecksum() error = %v", err)
	}
	if !valid {
		t.Fatal("expected matching checksum to validate")
	}

	t.Setenv(EnvValidation, "strict")
	if err := os.WriteFile(paths.ChecksumFile(), []byte("00000000"), 0o600); err != nil {
		t.Fatalf("WriteFile() error = %v", err)
	}
	if valid, err := validatePackageChecksum(paths, 0x12345678, logger); err == nil || valid {
		t.Fatalf("expected strict mismatch error, got valid=%v err=%v", valid, err)
	}
}

func TestSaveIndexMetadataAndCheckWorkenvValidity(t *testing.T) {
	t.Parallel()

	logger := logging.NewNullLogger()
	cacheDir := t.TempDir()
	paths := NewWorkenvPaths(cacheDir, "/tmp/demo.pspf")

	if err := os.MkdirAll(paths.Workenv(), 0o755); err != nil {
		t.Fatalf("MkdirAll(workenv) error = %v", err)
	}
	if err := os.MkdirAll(filepath.Dir(paths.CompleteFile()), 0o755); err != nil {
		t.Fatalf("MkdirAll(complete) error = %v", err)
	}
	if err := os.WriteFile(filepath.Join(paths.Workenv(), "payload.txt"), []byte("payload"), 0o600); err != nil {
		t.Fatalf("WriteFile(workenv payload) error = %v", err)
	}

	index := &PSPFIndex{
		FormatVersion:   PSPFVersion,
		PackageSize:     4096,
		LauncherSize:    1024,
		MetadataOffset:  1024,
		MetadataSize:    256,
		SlotTableOffset: 2048,
		SlotTableSize:   64,
		SlotCount:       1,
		IndexChecksum:   0xabcdef01,
	}

	if err := saveIndexMetadata(paths, index, logger); err != nil {
		t.Fatalf("saveIndexMetadata() error = %v", err)
	}

	raw, err := os.ReadFile(paths.IndexMetadataFile())
	if err != nil {
		t.Fatalf("ReadFile(index metadata) error = %v", err)
	}
	if !json.Valid(raw) || !strings.Contains(string(raw), "\"index_checksum\"") {
		t.Fatalf("unexpected index metadata JSON: %s", string(raw))
	}

	if err := os.WriteFile(paths.CompleteFile(), []byte("done"), 0o600); err != nil {
		t.Fatalf("WriteFile(complete) error = %v", err)
	}
	if err := os.WriteFile(paths.ChecksumFile(), []byte("abcdef01"), 0o600); err != nil {
		t.Fatalf("WriteFile(checksum) error = %v", err)
	}

	valid, err := checkWorkenvValidity(paths, index, nil, logger)
	if err != nil {
		t.Fatalf("checkWorkenvValidity() error = %v", err)
	}
	if !valid {
		t.Fatal("expected workenv validity check to pass")
	}
}
