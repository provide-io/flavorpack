//
// SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
// SPDX-License-Identifier: Apache-2.0
//

package format_2025

import (
	"encoding/binary"
	"encoding/json"
	"math"
	"os"
	"path/filepath"
	"testing"

	"github.com/provide-io/flavor/go/flavor/pkg/logging"
)

// ---------------------------------------------------------------------------
// EnforcePolicy: cover the RefuseRoot path when user is not privileged
// ---------------------------------------------------------------------------

func TestEnforcePolicyRefuseRootNotPrivileged(t *testing.T) {
	t.Parallel()
	// In a typical CI environment the test user is not root, so RefuseRoot should
	// NOT trigger an error. This exercises the branch where RefuseRoot=true but
	// isPrivilegedUser()=false.
	eff := EffectivePolicy{RefuseRoot: true, Enforcement: NewDefaultEnforcementPolicy()}
	_, err := EnforcePolicy(eff, 0, false, true)
	// If the test runner IS root this will fail — skip in that case.
	if isPrivilegedUser() {
		t.Skip("running as root/Administrator — cannot test non-privileged RefuseRoot path")
	}
	if err != nil {
		t.Fatalf("expected no error when RefuseRoot=true but user is not privileged, got: %v", err)
	}
}

// ---------------------------------------------------------------------------
// Metadata.UnmarshalJSON: policy field is valid JSON string (not an object)
// triggering json.Unmarshal into PackagePolicy failure
// ---------------------------------------------------------------------------

func TestMetadataUnmarshalJSONPolicyIsString(t *testing.T) {
	t.Parallel()
	// "policy" is a JSON string — valid JSON, but PackagePolicy is a struct.
	// json.Unmarshal into PackagePolicy will fail (cannot unmarshal string into struct).
	raw := `{"format":"PSPF/2025","slots":[],"policy":"not-an-object"}`
	var m Metadata
	err := json.Unmarshal([]byte(raw), &m)
	// Expect an error because a JSON string cannot be decoded into PackagePolicy.
	if err == nil {
		t.Fatal("expected error when policy is a JSON string, got nil")
	}
}

// ---------------------------------------------------------------------------
// applyOperatorPolicyJSON: cover enforcement validation error path
// ---------------------------------------------------------------------------

func TestApplyOperatorPolicyJSONInvalidEnforcementMode(t *testing.T) {
	t.Parallel()
	policy := &OperatorPolicy{Enforcement: NewDefaultEnforcementPolicy()}
	data := []byte(`{"version": 1, "enforcement": {"default": "explode"}}`)
	err := applyOperatorPolicyJSON(data, policy)
	if err == nil {
		t.Fatal("expected error for invalid enforcement mode, got nil")
	}
}

// ---------------------------------------------------------------------------
// validatePackageChecksum: cover the non-NotExist read error branch (line 59)
// ---------------------------------------------------------------------------

// TestValidatePackageChecksumReadError covers the branch where os.ReadFile returns
// a non-NotExist error (e.g., permission denied).
func TestValidatePackageChecksumReadError(t *testing.T) {
	t.Parallel()

	logger := logging.NewNullLogger()
	paths := NewWorkenvPaths(t.TempDir(), "/tmp/demo.pspf")

	// Create the instance directory and the checksum file.
	if err := os.MkdirAll(filepath.Dir(paths.ChecksumFile()), 0o755); err != nil {
		t.Fatalf("MkdirAll: %v", err)
	}
	if err := os.WriteFile(paths.ChecksumFile(), []byte("12345678"), 0o000 /* no permissions */); err != nil {
		t.Fatalf("WriteFile: %v", err)
	}
	// Ensure cleanup even if the test fails.
	t.Cleanup(func() {
		_ = os.Chmod(paths.ChecksumFile(), 0o600)
	})

	// os.ReadFile should fail with permission denied — not os.ErrNotExist.
	valid, err := validatePackageChecksum(paths, 0x12345678, logger)
	if err != nil {
		t.Fatalf("validatePackageChecksum() unexpectedly returned error: %v", err)
	}
	if valid {
		t.Fatal("expected invalid (false) when checksum file cannot be read")
	}
}

// ---------------------------------------------------------------------------
// expandDOSStub: trigger updateSectionOffsets failure path inside expansion
// ---------------------------------------------------------------------------

// TestExpandDOSStubSectionOffsetOverflow covers the error path inside expandDOSStub
// where updateSectionOffsets fails because a section's PointerToRawData would overflow
// uint32 after adding the padding.
func TestExpandDOSStubSectionOffsetOverflow(t *testing.T) {
	t.Parallel()

	logger := logging.NewNullLogger()

	// Build a PE at 0x80 (triggers expansion by 0x70 bytes).
	data, layout := buildSyntheticPEForTests(t, 0x80, false)

	// Set the first section's PointerToRawData to MaxUint32 - 1 so that
	// adding 0x70 (the padding) causes overflow.
	firstSectionPtrOffset := layout.sectionTableOffset + 20 // PointerToRawData at section+20
	binary.LittleEndian.PutUint32(data[firstSectionPtrOffset:firstSectionPtrOffset+4], math.MaxUint32-0x10)

	_, err := expandDOSStub(data, logger)
	if err == nil {
		t.Fatal("expected error from expandDOSStub when section pointer overflows uint32, got nil")
	}
}
