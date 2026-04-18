// SPDX-FileCopyrightText: Copyright (c) 2026 provide.io llc. All rights reserved.
// SPDX-License-Identifier: Apache-2.0

package format_2025

import "testing"

func TestPSPFIndexUnpackWrongSize(t *testing.T) {
	t.Parallel()

	var idx PSPFIndex
	// Pass fewer bytes than IndexSize — should return an error
	if err := idx.Unpack(make([]byte, 10)); err == nil {
		t.Fatal("expected Unpack to return error for wrong-size data")
	}
}

func TestPSPFIndexPackUnpackRoundTrip(t *testing.T) {
	t.Parallel()

	original := PSPFIndex{
		FormatVersion: PSPFVersion,
		PackageSize:   4096,
		LauncherSize:  1024,
		SlotCount:     2,
		IndexChecksum: 0xdeadbeef,
		Capabilities:  CapabilitySigned | CapabilityCompressedIndex,
	}

	packed := original.Pack()
	if len(packed) != IndexSize {
		t.Fatalf("Pack() returned %d bytes, want %d", len(packed), IndexSize)
	}

	var restored PSPFIndex
	if err := restored.Unpack(packed); err != nil {
		t.Fatalf("Unpack() error = %v", err)
	}

	if restored.FormatVersion != original.FormatVersion {
		t.Errorf("FormatVersion: got %d, want %d", restored.FormatVersion, original.FormatVersion)
	}
	if restored.PackageSize != original.PackageSize {
		t.Errorf("PackageSize: got %d, want %d", restored.PackageSize, original.PackageSize)
	}
	if restored.IndexChecksum != original.IndexChecksum {
		t.Errorf("IndexChecksum: got %x, want %x", restored.IndexChecksum, original.IndexChecksum)
	}
	if restored.Capabilities != original.Capabilities {
		t.Errorf("Capabilities: got %x, want %x", restored.Capabilities, original.Capabilities)
	}
}
