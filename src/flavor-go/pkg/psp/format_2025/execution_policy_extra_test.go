// SPDX-FileCopyrightText: Copyright (c) 2026 provide.io llc. All rights reserved.
// SPDX-License-Identifier: Apache-2.0

package format_2025

import (
	"os"
	"path/filepath"
	"runtime"
	"testing"
)

// TestEnforcePolicyPlatformAllowed covers the "found = true; break" path
// in EnforcePolicy when the current platform IS in the allowed list.
func TestEnforcePolicyPlatformAllowed(t *testing.T) {
	currentPlat := getCurrentPlatform()
	eff := EffectivePolicy{
		Platforms:   []string{currentPlat},
		Enforcement: NewDefaultEnforcementPolicy(),
	}
	_, err := EnforcePolicy(eff, 0, false, true)
	if err != nil {
		t.Fatalf("expected no error when current platform is allowed, got: %v", err)
	}
}

// TestApplyOperatorPolicyJSON_AllSections covers parsing a fully populated JSON policy.
func TestApplyOperatorPolicyJSON_AllSections(t *testing.T) {
	policy := OperatorPolicy{Enforcement: NewDefaultEnforcementPolicy()}
	data := []byte(`{
		"version": 1,
		"trust": {"require_trusted_key": true, "use_os_keychain": true},
		"execution": {"refuse_root": true, "max_age_days": 90, "allow_platforms": ["linux_amd64"]},
		"attestation": {"require_sbom": true},
		"enforcement": {"default": "warn", "platform_mismatch": "allow"}
	}`)
	if err := applyOperatorPolicyJSON(data, &policy); err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if !policy.RequireTrustedKey {
		t.Error("expected RequireTrustedKey=true")
	}
	if !policy.UseOsKeychain {
		t.Error("expected UseOsKeychain=true")
	}
	if !policy.RefuseRoot {
		t.Error("expected RefuseRoot=true")
	}
	if policy.MaxAgeDays == nil || *policy.MaxAgeDays != 90 {
		t.Errorf("expected MaxAgeDays=90, got %v", policy.MaxAgeDays)
	}
	if len(policy.AllowPlatforms) != 1 || policy.AllowPlatforms[0] != "linux_amd64" {
		t.Errorf("expected AllowPlatforms=[linux_amd64], got %v", policy.AllowPlatforms)
	}
	if !policy.RequireSBOM {
		t.Error("expected RequireSBOM=true")
	}
	if policy.Enforcement.Default != ModeWarn {
		t.Errorf("expected enforcement default=warn, got %s", policy.Enforcement.Default)
	}
	if policy.Enforcement.PlatformMismatch != ModeAllow {
		t.Errorf("expected enforcement platform_mismatch=allow, got %s", policy.Enforcement.PlatformMismatch)
	}
}

// TestApplyOperatorPolicyJSON_InvalidJSON covers the json.Unmarshal error path.
func TestApplyOperatorPolicyJSON_InvalidJSON(t *testing.T) {
	policy := OperatorPolicy{Enforcement: NewDefaultEnforcementPolicy()}
	if err := applyOperatorPolicyJSON([]byte(`{broken`), &policy); err == nil {
		t.Fatal("expected error for invalid JSON")
	}
}

// TestApplyOperatorPolicyJSON_MissingVersion covers the version=0 error path.
func TestApplyOperatorPolicyJSON_MissingVersion(t *testing.T) {
	policy := OperatorPolicy{Enforcement: NewDefaultEnforcementPolicy()}
	if err := applyOperatorPolicyJSON([]byte(`{"trust":{}}`), &policy); err == nil {
		t.Fatal("expected error for missing version")
	}
}

// TestApplyOperatorPolicyJSON_EmptySections covers the case where sections are present but empty.
func TestApplyOperatorPolicyJSON_EmptySections(t *testing.T) {
	policy := OperatorPolicy{Enforcement: NewDefaultEnforcementPolicy()}
	data := []byte(`{"version": 1, "trust": {}, "execution": {}, "attestation": {}}`)
	if err := applyOperatorPolicyJSON(data, &policy); err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
}

// TestApplyEnforcement_UnknownModeTreatedAsDeny covers the default switch case
// in applyEnforcement where an unrecognised mode is treated as deny for safety.
func TestApplyEnforcement_UnknownModeTreatedAsDeny(t *testing.T) {
	var warnings []string
	err := applyEnforcement(EnforcementMode("bogus"), "should be denied", &warnings)
	if err == nil {
		t.Fatal("expected unknown enforcement mode to be treated as deny")
	}
	if len(warnings) != 0 {
		t.Errorf("expected no warnings for unknown mode, got: %v", warnings)
	}
}

// TestLoadOperatorPolicy_SystemPolicyReadError covers the non-IsNotExist error
// path in LoadOperatorPolicy for the *system* policy file (e.g. path is a directory).
func TestLoadOperatorPolicy_SystemPolicyReadError(t *testing.T) {
	dir := t.TempDir()
	// Create a directory where a file is expected — os.ReadFile on a directory
	// returns an error that is NOT os.IsNotExist.
	dirAsFile := dir // the temp dir itself IS a directory

	oldSystem := getSystemPolicyFileImpl
	oldUser := getUserPolicyFileImpl
	t.Cleanup(func() {
		getSystemPolicyFileImpl = oldSystem
		getUserPolicyFileImpl = oldUser
	})

	getSystemPolicyFileImpl = func() string { return dirAsFile }
	getUserPolicyFileImpl = func() string { return "" } // skip user policy

	_, err := LoadOperatorPolicy()
	if err == nil {
		t.Fatal("expected read error when system policy path is a directory")
	}
}

// TestLoadOperatorPolicy_EmptyPathSkipped covers the path=="" continue branch
// in LoadOperatorPolicy.
func TestLoadOperatorPolicy_EmptyPathSkipped(t *testing.T) {
	oldSystem := getSystemPolicyFileImpl
	oldUser := getUserPolicyFileImpl
	t.Cleanup(func() {
		getSystemPolicyFileImpl = oldSystem
		getUserPolicyFileImpl = oldUser
	})

	getSystemPolicyFileImpl = func() string { return "" }
	getUserPolicyFileImpl = func() string { return "" }

	policy, err := LoadOperatorPolicy()
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	// Should return defaults
	if policy.Enforcement.Default != ModeDeny {
		t.Errorf("expected default enforcement=deny, got %s", policy.Enforcement.Default)
	}
}

// TestEnforcementModeFor_AllChecks covers the ModeFor switch for each check name.
func TestEnforcementModeFor_AllChecks(t *testing.T) {
	ep := EnforcementPolicy{
		Default:          ModeDeny,
		PlatformMismatch: ModeWarn,
		UntrustedKey:     ModeAllow,
		ExpiredPackage:   ModeWarn,
		MissingEnv:       ModeAllow,
		MissingSBOM:      ModeWarn,
		RootExecution:    ModeAllow,
		OsKeychain:       ModeWarn,
	}

	checks := map[string]EnforcementMode{
		"platform_mismatch": ModeWarn,
		"untrusted_key":     ModeAllow,
		"expired_package":   ModeWarn,
		"missing_env":       ModeAllow,
		"missing_sbom":      ModeWarn,
		"root_execution":    ModeAllow,
		"os_keychain":       ModeWarn,
		"unknown_check":     ModeDeny, // falls through to default
	}

	for check, want := range checks {
		got := ep.ModeFor(check)
		if got != want {
			t.Errorf("ModeFor(%q) = %s, want %s", check, got, want)
		}
	}
}

// ---------------------------------------------------------------------------
// getSystemPolicyFile — cross-platform coverage via policyGOOS override
// ---------------------------------------------------------------------------

func TestGetSystemPolicyFile_Windows(t *testing.T) {
	old := policyGOOS
	t.Cleanup(func() { policyGOOS = old })
	policyGOOS = "windows"

	t.Setenv("PROGRAMDATA", "/tmp/pd")
	got := getSystemPolicyFile()
	want := filepath.Join("/tmp/pd", "flavor", "policy.json")
	if got != want {
		t.Errorf("getSystemPolicyFile() windows with PROGRAMDATA = %q, want %q", got, want)
	}
}

func TestGetSystemPolicyFile_WindowsNoPROGRAMDATA(t *testing.T) {
	old := policyGOOS
	t.Cleanup(func() { policyGOOS = old })
	policyGOOS = "windows"

	t.Setenv("PROGRAMDATA", "")
	got := getSystemPolicyFile()
	want := filepath.Join("C:\\ProgramData", "flavor", "policy.json")
	if got != want {
		t.Errorf("getSystemPolicyFile() windows fallback = %q, want %q", got, want)
	}
}

func TestGetSystemPolicyFile_Unix(t *testing.T) {
	old := policyGOOS
	t.Cleanup(func() { policyGOOS = old })
	policyGOOS = "linux"

	got := getSystemPolicyFile()
	if got != "/etc/flavor/policy.json" {
		t.Errorf("getSystemPolicyFile() unix = %q, want /etc/flavor/policy.json", got)
	}
}

// ---------------------------------------------------------------------------
// getCurrentPlatform — cross-platform coverage via policyGOOS/policyGOARCH
// ---------------------------------------------------------------------------

func TestGetCurrentPlatform_AllOS(t *testing.T) {
	oldOS := policyGOOS
	oldArch := policyGOARCH
	t.Cleanup(func() {
		policyGOOS = oldOS
		policyGOARCH = oldArch
	})

	cases := []struct {
		goos, goarch, want string
	}{
		{"linux", "amd64", "linux_amd64"},
		{"linux", "arm64", "linux_arm64"},
		{"darwin", "amd64", "darwin_amd64"},
		{"darwin", "arm64", "darwin_arm64"},
		{"freebsd", "amd64", "freebsd_amd64"},
		{"freebsd", "arm64", "freebsd_arm64"},
		{"windows", "amd64", "windows_amd64"},
		{"windows", "arm64", "windows_arm64"},
	}

	for _, tc := range cases {
		policyGOOS = tc.goos
		policyGOARCH = tc.goarch
		got := getCurrentPlatform()
		if got != tc.want {
			t.Errorf("getCurrentPlatform() with GOOS=%s GOARCH=%s = %q, want %q", tc.goos, tc.goarch, got, tc.want)
		}
	}
}

func TestGetCurrentPlatform_RealOS(t *testing.T) {
	// Ensure policyGOOS/policyGOARCH match runtime constants
	old := policyGOOS
	oldArch := policyGOARCH
	t.Cleanup(func() {
		policyGOOS = old
		policyGOARCH = oldArch
	})
	policyGOOS = runtime.GOOS
	policyGOARCH = runtime.GOARCH

	p := getCurrentPlatform()
	if p == "" {
		t.Fatal("getCurrentPlatform() returned empty string")
	}
	_ = os.Getenv // suppress unused import
}
