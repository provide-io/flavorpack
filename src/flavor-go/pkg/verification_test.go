// SPDX-FileCopyrightText: Copyright (c) 2026 provide.io llc. All rights reserved.
// SPDX-License-Identifier: Apache-2.0

package pkg

import (
	"bytes"
	"compress/gzip"
	"crypto/sha256"
	"encoding/json"
	"os"
	"os/exec"
	"path/filepath"
	"testing"

	"github.com/provide-io/flavor/go/flavor/pkg/logging"
	"github.com/provide-io/flavor/go/flavor/pkg/psp/format_2025"
)

func writeValidBundle(t *testing.T) string {
	t.Helper()

	dir := t.TempDir()
	path := filepath.Join(dir, "bundle.pspf")

	metadata := format_2025.Metadata{
		Format:        "pspf",
		FormatVersion: "2025.0",
		Package: format_2025.PackageInfo{
			Name:        "flavorpack",
			Version:     "1.0.0",
			Description: "test bundle",
		},
		Slots: []format_2025.SlotMetadata{},
	}

	metadataJSON, err := json.Marshal(metadata)
	if err != nil {
		t.Fatalf("marshal metadata: %v", err)
	}

	var metadataArchive bytes.Buffer
	gz := gzip.NewWriter(&metadataArchive)
	if _, err := gz.Write(metadataJSON); err != nil {
		t.Fatalf("write gzip: %v", err)
	}
	if err := gz.Close(); err != nil {
		t.Fatalf("close gzip: %v", err)
	}

	metadataBytes := metadataArchive.Bytes()
	index := format_2025.PSPFIndex{
		FormatVersion:   format_2025.PSPFVersion,
		PackageSize:     uint64(len(metadataBytes) + format_2025.MagicTrailerSize),
		MetadataOffset:  0,
		MetadataSize:    uint64(len(metadataBytes)),
		SlotTableOffset: 0,
		SlotTableSize:   0,
		SlotCount:       0,
	}
	index.MetadataChecksum = sha256.Sum256(metadataBytes)
	copy(index.Reserved[len(index.Reserved)-4:], format_2025.PackageEmojiBytes)

	var bundle bytes.Buffer
	bundle.Write(metadataBytes)
	bundle.Write(format_2025.PackageEmojiBytes)
	bundle.Write(index.Pack())
	bundle.Write(format_2025.MagicWandEmojiBytes)

	if err := os.WriteFile(path, bundle.Bytes(), 0o600); err != nil {
		t.Fatalf("write bundle: %v", err)
	}

	return path
}

// TestVerifyBundleWithLoggerDirect calls VerifyBundleWithLogger directly (not via
// subprocess) so that the success-path statements contribute to coverage.
func TestVerifyBundleWithLoggerDirect(t *testing.T) {
	t.Parallel()
	bundlePath := writeValidBundle(t)
	// Must not panic or call os.Exit for a valid bundle.
	VerifyBundleWithLogger(bundlePath, logging.NewNullLogger())
}

func TestVerifyBundle(t *testing.T) {
	bundlePath := writeValidBundle(t)

	t.Run("success", func(t *testing.T) {
		cmd := exec.Command(os.Args[0], "-test.run=TestVerifyBundleHelper", "--", "success", bundlePath)
		cmd.Env = append(os.Environ(),
			"FLAVORPACK_VERIFY_BUNDLE_HELPER=1",
			"FLAVORPACK_VERIFY_BUNDLE_MODE=success",
		)
		out, err := cmd.CombinedOutput()
		if err != nil {
			t.Fatalf("verify bundle success failed: %v\n%s", err, out)
		}
	})

	t.Run("failure", func(t *testing.T) {
		cmd := exec.Command(os.Args[0], "-test.run=TestVerifyBundleHelper", "--", "failure", filepath.Join(t.TempDir(), "missing.pspf"))
		cmd.Env = append(os.Environ(),
			"FLAVORPACK_VERIFY_BUNDLE_HELPER=1",
			"FLAVORPACK_VERIFY_BUNDLE_MODE=failure",
		)
		out, err := cmd.CombinedOutput()
		if err == nil {
			t.Fatalf("expected verify bundle failure")
		}
		if !bytes.Contains(out, []byte("MagicTrailer verification failed")) {
			t.Fatalf("expected failure output to mention magic trailer verification, got:\n%s", out)
		}
	})
}

func TestVerifyBundleHelper(t *testing.T) {
	if os.Getenv("FLAVORPACK_VERIFY_BUNDLE_HELPER") != "1" {
		t.Skip("helper process")
	}

	mode := os.Getenv("FLAVORPACK_VERIFY_BUNDLE_MODE")
	args := os.Args
	if len(args) < 3 {
		t.Fatal("missing helper arguments")
	}
	path := args[len(args)-1]

	switch mode {
	case "success":
		VerifyBundleWithLogger(path, logging.NewNullLogger())
	case "failure":
		VerifyBundle(path)
	default:
		t.Fatalf("unknown helper mode %q", mode)
	}
}
