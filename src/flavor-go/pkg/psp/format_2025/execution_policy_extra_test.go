package format_2025

import (
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
