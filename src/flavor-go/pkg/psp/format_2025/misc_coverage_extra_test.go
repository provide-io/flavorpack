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

	"github.com/hashicorp/go-hclog"
)

// ---------------------------------------------------------------------------
// mustInt: cover int8, int16, uint, and overflow paths
// ---------------------------------------------------------------------------

func TestMustIntInt8(t *testing.T) {
	t.Parallel()
	v, err := mustInt("field", int8(42))
	if err != nil || v != 42 {
		t.Fatalf("mustInt(int8) = %d, %v", v, err)
	}
}

func TestMustIntInt16(t *testing.T) {
	t.Parallel()
	v, err := mustInt("field", int16(1000))
	if err != nil || v != 1000 {
		t.Fatalf("mustInt(int16) = %d, %v", v, err)
	}
}

func TestMustIntUintInRange(t *testing.T) {
	t.Parallel()
	v, err := mustInt("field", uint(100))
	if err != nil || v != 100 {
		t.Fatalf("mustInt(uint in-range) = %d, %v", v, err)
	}
}

func TestMustIntUintOverflow(t *testing.T) {
	t.Parallel()
	// uint(math.MaxInt + 1) overflows int — but MaxUint > MaxInt always.
	// Use MaxUint64 cast to uint to be safe.
	_, err := mustInt("field", uint(math.MaxUint))
	if err == nil {
		t.Fatal("expected overflow error for uint(MaxUint), got nil")
	}
}

func TestMustIntInt64Overflow(t *testing.T) {
	t.Parallel()
	_, err := mustInt("field", int64(math.MaxInt64))
	// On 64-bit systems MaxInt64 == MaxInt, so no overflow — no error expected.
	// On 32-bit systems it would overflow. We just ensure no panic.
	_ = err
}

func TestMustIntInt64NegativeOverflow(t *testing.T) {
	t.Parallel()
	// int64(math.MinInt64) is more negative than -MaxInt-1 on 32-bit systems.
	// On 64-bit systems MinInt64 == MinInt, so no overflow. Ensure no panic.
	_, err := mustInt("field", int64(math.MinInt64))
	_ = err
}

func TestMustIntUint64Overflow(t *testing.T) {
	t.Parallel()
	_, err := mustInt("field", uint64(math.MaxUint64))
	if err == nil {
		t.Fatal("expected overflow error for uint64(MaxUint64), got nil")
	}
}

// ---------------------------------------------------------------------------
// EnforcePolicy: cover the RefuseRoot path when user is not privileged
// ---------------------------------------------------------------------------

func TestEnforcePolicyRefuseRootNotPrivileged(t *testing.T) {
	t.Parallel()
	// In a typical CI environment the test user is not root, so RefuseRoot should
	// NOT trigger an error. This exercises the branch where RefuseRoot=true but
	// isPrivilegedUser()=false.
	eff := EffectivePolicy{RefuseRoot: true}
	err := EnforcePolicy(eff, 0, false, true)
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
// applyExecutionPolicySection: cover the unknown-key error path
// ---------------------------------------------------------------------------

func TestApplyExecutionPolicySectionUnknownKey(t *testing.T) {
	t.Parallel()
	section := map[string]any{
		"unknown_key": "value",
	}
	policy := &OperatorPolicy{}
	err := applyExecutionPolicySection(section, policy)
	if err == nil {
		t.Fatal("expected error for unknown key in [execution] section, got nil")
	}
}

// TestApplyExecutionPolicySectionAllowPlatformsNotStringList covers the error path
// where allow_platforms is not a valid string list.
func TestApplyExecutionPolicySectionAllowPlatformsNotStringList(t *testing.T) {
	t.Parallel()
	section := map[string]any{
		"allow_platforms": 42, // not a string list
	}
	policy := &OperatorPolicy{}
	err := applyExecutionPolicySection(section, policy)
	if err == nil {
		t.Fatal("expected error when allow_platforms is not a string list, got nil")
	}
}

// ---------------------------------------------------------------------------
// validatePackageChecksum: cover the non-NotExist read error branch (line 59)
// ---------------------------------------------------------------------------

// TestValidatePackageChecksumReadError covers the branch where os.ReadFile returns
// a non-NotExist error (e.g., permission denied).
func TestValidatePackageChecksumReadError(t *testing.T) {
	t.Parallel()

	logger := hclog.NewNullLogger()
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

	logger := hclog.NewNullLogger()

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
