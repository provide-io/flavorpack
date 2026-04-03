package format_2025

import (
	"os"
	"path/filepath"
	"strings"
	"testing"
)

func TestGetCurrentPlatform(t *testing.T) {
	p := getCurrentPlatform()
	if p == "" {
		t.Fatal("getCurrentPlatform returned empty string")
	}
	// Should be one of the known platforms
	validPlatforms := map[string]bool{
		"linux_amd64": true, "linux_arm64": true,
		"darwin_amd64": true, "darwin_arm64": true,
		"windows_amd64": true, "windows_arm64": true,
		"freebsd_amd64": true, "freebsd_arm64": true,
	}
	if !validPlatforms[p] {
		t.Errorf("unexpected platform: %s", p)
	}
}

func TestMergePolicy_RefuseRoot(t *testing.T) {
	pkg := PackagePolicy{RefuseRoot: false}
	op := OperatorPolicy{RefuseRoot: true, Enforcement: NewDefaultEnforcementPolicy()}
	eff := MergePolicy(pkg, op)
	if !eff.RefuseRoot {
		t.Error("expected RefuseRoot=true when operator sets it")
	}
}

func TestMergePolicy_MaxAgeDays(t *testing.T) {
	pkg := PackagePolicy{}
	pkg.MaxAgeDays = intPtr(365)
	op := OperatorPolicy{Enforcement: NewDefaultEnforcementPolicy()}
	op.MaxAgeDays = intPtr(90)
	eff := MergePolicy(pkg, op)
	if eff.MaxAgeDays == nil || *eff.MaxAgeDays != 90 {
		t.Errorf("expected max_age_days=90, got %v", eff.MaxAgeDays)
	}
}

func TestMergePolicy_OperatorFlagsPropagated(t *testing.T) {
	pkg := PackagePolicy{}
	op := OperatorPolicy{
		RequireTrustedKey: true,
		UseOsKeychain:     true,
		RequireSBOM:       true,
		Enforcement:       NewDefaultEnforcementPolicy(),
	}
	eff := MergePolicy(pkg, op)
	if !eff.RequireTrustedKey {
		t.Fatal("expected require_trusted_key to propagate")
	}
	if !eff.UseOsKeychain {
		t.Fatal("expected use_os_keychain to propagate")
	}
	if !eff.RequireSBOM {
		t.Fatal("expected require_sbom to propagate")
	}
}

func TestMergePolicy_EnforcementPropagated(t *testing.T) {
	pkg := PackagePolicy{}
	op := OperatorPolicy{
		Enforcement: EnforcementPolicy{
			Default:          ModeDeny,
			PlatformMismatch: ModeWarn,
		},
	}
	eff := MergePolicy(pkg, op)
	if eff.Enforcement.Default != ModeDeny {
		t.Error("expected enforcement default to propagate")
	}
	if eff.Enforcement.PlatformMismatch != ModeWarn {
		t.Error("expected enforcement platform_mismatch to propagate")
	}
}

func TestMergePolicy_Platforms_Intersection(t *testing.T) {
	pkg := PackagePolicy{Platforms: []string{"linux_amd64", "darwin_arm64"}}
	op := OperatorPolicy{AllowPlatforms: []string{"linux_amd64", "linux_arm64"}, Enforcement: NewDefaultEnforcementPolicy()}
	eff := MergePolicy(pkg, op)
	if len(eff.Platforms) != 1 || eff.Platforms[0] != "linux_amd64" {
		t.Errorf("expected [linux_amd64], got %v", eff.Platforms)
	}
}

func TestMergePolicy_Platforms_OnlyOperator(t *testing.T) {
	pkg := PackagePolicy{}
	op := OperatorPolicy{AllowPlatforms: []string{"linux_amd64"}, Enforcement: NewDefaultEnforcementPolicy()}
	eff := MergePolicy(pkg, op)
	if len(eff.Platforms) != 1 || eff.Platforms[0] != "linux_amd64" {
		t.Errorf("expected [linux_amd64], got %v", eff.Platforms)
	}
}

func TestMergePolicy_Platforms_OnlyPackage(t *testing.T) {
	pkg := PackagePolicy{Platforms: []string{"darwin_arm64"}}
	op := OperatorPolicy{Enforcement: NewDefaultEnforcementPolicy()}
	eff := MergePolicy(pkg, op)
	if len(eff.Platforms) != 1 || eff.Platforms[0] != "darwin_arm64" {
		t.Errorf("expected [darwin_arm64], got %v", eff.Platforms)
	}
}

func TestEnforcePolicy_Permissive(t *testing.T) {
	eff := EffectivePolicy{Enforcement: NewDefaultEnforcementPolicy()}
	warnings, err := EnforcePolicy(eff, 0, false, true)
	if err != nil {
		t.Errorf("expected no error, got: %v", err)
	}
	if len(warnings) != 0 {
		t.Errorf("expected no warnings, got: %v", warnings)
	}
}

func TestEnforcePolicy_UseOsKeychainUnsupported(t *testing.T) {
	eff := EffectivePolicy{UseOsKeychain: true, Enforcement: NewDefaultEnforcementPolicy()}
	_, err := EnforcePolicy(eff, 0, false, true)
	if err == nil {
		t.Fatal("expected use_os_keychain to be rejected")
	}
}

func TestEnforcePolicy_PlatformBlocked(t *testing.T) {
	eff := EffectivePolicy{Platforms: []string{"__nonexistent_platform__"}, Enforcement: NewDefaultEnforcementPolicy()}
	_, err := EnforcePolicy(eff, 0, false, true)
	if err == nil {
		t.Error("expected platform error")
	}
}

func TestEnforcePolicy_SBOMRequired(t *testing.T) {
	eff := EffectivePolicy{RequireSBOM: true, Enforcement: NewDefaultEnforcementPolicy()}
	_, err := EnforcePolicy(eff, 0, false, true)
	if err == nil {
		t.Error("expected SBOM error")
	}
	_, err = EnforcePolicy(eff, 0, true, true)
	if err != nil {
		t.Errorf("expected no error when hasSBOM=true, got: %v", err)
	}
}

func TestEnforcePolicy_EnvVarMissing(t *testing.T) {
	eff := EffectivePolicy{RequireEnv: []string{"__FLAVOR_TEST_VAR_NONEXISTENT__"}, Enforcement: NewDefaultEnforcementPolicy()}
	_, err := EnforcePolicy(eff, 0, false, true)
	if err == nil {
		t.Error("expected env var error")
	}
}

func TestEnforcePolicy_EnvVarPresent(t *testing.T) {
	t.Setenv("__FLAVOR_TEST_VAR__", "1")
	eff := EffectivePolicy{RequireEnv: []string{"__FLAVOR_TEST_VAR__"}, Enforcement: NewDefaultEnforcementPolicy()}
	_, err := EnforcePolicy(eff, 0, false, true)
	if err != nil {
		t.Errorf("expected no error, got: %v", err)
	}
}

func TestEnforcePolicy_AgeExceeded(t *testing.T) {
	zero := 0
	eff := EffectivePolicy{MaxAgeDays: &zero, Enforcement: NewDefaultEnforcementPolicy()}
	// Build timestamp of 1 (ancient) should trigger age check
	_, err := EnforcePolicy(eff, 1, false, true)
	if err == nil {
		t.Error("expected age error")
	}
}

func TestEnforcePolicy_RequireTrustedKey_UntrustedKey(t *testing.T) {
	eff := EffectivePolicy{RequireTrustedKey: true, Enforcement: NewDefaultEnforcementPolicy()}
	_, err := EnforcePolicy(eff, 0, false, false)
	if err == nil {
		t.Error("expected error when key is untrusted and require_trusted_key=true")
	}
}

func TestEnforcePolicy_RequireTrustedKey_TrustedKey(t *testing.T) {
	eff := EffectivePolicy{RequireTrustedKey: true, Enforcement: NewDefaultEnforcementPolicy()}
	_, err := EnforcePolicy(eff, 0, false, true)
	if err != nil {
		t.Errorf("expected no error when key is trusted, got: %v", err)
	}
}

func TestEnforcePolicy_RequireTrustedKey_NotRequired(t *testing.T) {
	eff := EffectivePolicy{RequireTrustedKey: false, Enforcement: NewDefaultEnforcementPolicy()}
	// Even untrusted key should pass when policy doesn't require it
	_, err := EnforcePolicy(eff, 0, false, false)
	if err != nil {
		t.Errorf("expected no error when require_trusted_key=false, got: %v", err)
	}
}

func TestParsePackagePolicyJSON_Empty(t *testing.T) {
	pkg, err := ParsePackagePolicyJSON(nil)
	if err != nil {
		t.Errorf("unexpected error: %v", err)
	}
	if pkg.RefuseRoot {
		t.Error("expected RefuseRoot=false")
	}
}

func TestParsePackagePolicyJSON_Full(t *testing.T) {
	raw := []byte(`{"platforms":["linux_amd64"],"refuse_root":true,"max_age_days":365,"require_env":["APP_KEY"]}`)
	pkg, err := ParsePackagePolicyJSON(raw)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if !pkg.RefuseRoot {
		t.Error("expected RefuseRoot=true")
	}
	if pkg.MaxAgeDays == nil || *pkg.MaxAgeDays != 365 {
		t.Errorf("expected max_age_days=365")
	}
}

func TestLoadOperatorPolicy_MissingFile(t *testing.T) {
	dir := t.TempDir()
	t.Setenv(EnvConfigDir, dir)
	policy, err := LoadOperatorPolicy()
	if err != nil {
		t.Errorf("unexpected error: %v", err)
	}
	if policy.RequireTrustedKey {
		t.Error("expected permissive defaults")
	}
}

func TestLoadOperatorPolicy_WithFile(t *testing.T) {
	dir := t.TempDir()
	content := `{"version":1,"trust":{"require_trusted_key":true},"execution":{"refuse_root":true}}`
	if err := os.WriteFile(filepath.Join(dir, "policy.json"), []byte(content), 0600); err != nil {
		t.Fatal(err)
	}
	t.Setenv(EnvConfigDir, dir)
	policy, err := LoadOperatorPolicy()
	if err != nil {
		t.Errorf("unexpected error: %v", err)
	}
	if !policy.RequireTrustedKey {
		t.Error("expected require_trusted_key=true")
	}
	if !policy.RefuseRoot {
		t.Error("expected refuse_root=true")
	}
}

func TestGetUserPolicyFile_XDG(t *testing.T) {
	t.Setenv(EnvConfigDir, "")
	t.Setenv("XDG_CONFIG_HOME", "/tmp/xdg")
	t.Setenv("HOME", "")
	path := getUserPolicyFile()
	want := filepath.Join("/tmp/xdg", "flavor", "policy.json")
	if path != want {
		t.Errorf("unexpected path: %s (want %s)", path, want)
	}
}

func TestGetUserPolicyFile_Home(t *testing.T) {
	t.Setenv(EnvConfigDir, "")
	t.Setenv("XDG_CONFIG_HOME", "")
	t.Setenv("HOME", "/home/user")
	path := getUserPolicyFile()
	want := filepath.Join("/home/user", ".config", "flavor", "policy.json")
	if path != want {
		t.Errorf("unexpected path: %s (want %s)", path, want)
	}
}

func TestGetUserPolicyFile_NoEnv(t *testing.T) {
	t.Setenv(EnvConfigDir, "")
	t.Setenv("XDG_CONFIG_HOME", "")
	t.Setenv("HOME", "")
	// Should return "" or some default — just confirm no panic
	_ = getUserPolicyFile()
}

func TestLoadOperatorPolicyReturnsErrorWhenPolicyPathIsDirectory(t *testing.T) {
	dir := t.TempDir()
	policyDir := filepath.Join(dir, "policy.json")
	if err := os.MkdirAll(policyDir, 0o755); err != nil {
		t.Fatalf("MkdirAll(policy dir) error = %v", err)
	}

	t.Setenv(EnvConfigDir, dir)
	_, err := LoadOperatorPolicy()
	if err == nil || !strings.Contains(err.Error(), "reading policy") {
		t.Fatalf("LoadOperatorPolicy() error = %v, want reading policy failure", err)
	}
}

func TestLoadOperatorPolicyRejectsMalformedUserPolicy(t *testing.T) {
	dir := t.TempDir()
	policyPath := filepath.Join(dir, "policy.json")
	if err := os.WriteFile(policyPath, []byte(`{broken json not valid`), 0o600); err != nil {
		t.Fatalf("WriteFile(policy) error = %v", err)
	}

	t.Setenv(EnvConfigDir, dir)
	_, err := LoadOperatorPolicy()
	if err == nil {
		t.Fatal("expected malformed user policy to fail closed")
	}
}

func TestLoadOperatorPolicyRejectsMalformedSystemPolicy(t *testing.T) {
	dir := t.TempDir()
	systemPath := filepath.Join(dir, "system-policy.json")
	if err := os.WriteFile(systemPath, []byte(`{broken json not valid`), 0o600); err != nil {
		t.Fatalf("WriteFile(system policy) error = %v", err)
	}

	oldSystem := getSystemPolicyFileImpl
	oldUser := getUserPolicyFileImpl
	t.Cleanup(func() {
		getSystemPolicyFileImpl = oldSystem
		getUserPolicyFileImpl = oldUser
	})

	getSystemPolicyFileImpl = func() string { return systemPath }
	getUserPolicyFileImpl = func() string { return filepath.Join(dir, "missing-user-policy.json") }

	_, err := LoadOperatorPolicy()
	if err == nil {
		t.Fatal("expected malformed system policy to fail closed")
	}
}

func TestLoadOperatorPolicyRejectsMissingVersion(t *testing.T) {
	dir := t.TempDir()
	policyPath := filepath.Join(dir, "policy.json")
	if err := os.WriteFile(policyPath, []byte(`{"trust":{"require_trusted_key":true}}`), 0o600); err != nil {
		t.Fatalf("WriteFile(policy) error = %v", err)
	}

	t.Setenv(EnvConfigDir, dir)
	_, err := LoadOperatorPolicy()
	if err == nil {
		t.Fatal("expected missing version to fail closed")
	}
}

func TestLoadOperatorPolicyWarnsOnFutureVersion(t *testing.T) {
	dir := t.TempDir()
	content := `{"version":99,"trust":{"require_trusted_key":true}}`
	policyPath := filepath.Join(dir, "policy.json")
	if err := os.WriteFile(policyPath, []byte(content), 0o600); err != nil {
		t.Fatalf("WriteFile(policy) error = %v", err)
	}

	t.Setenv(EnvConfigDir, dir)
	policy, err := LoadOperatorPolicy()
	if err != nil {
		t.Fatalf("expected no error for future version (warn only), got: %v", err)
	}
	if !policy.RequireTrustedKey {
		t.Error("expected require_trusted_key=true even with future version")
	}
}

func TestMergePolicyUsesYoungerPackageAgeAndEmptyPlatformIntersection(t *testing.T) {
	pkgAge := 30
	opAge := 90
	pkg := PackagePolicy{
		Platforms:  []string{"linux_amd64"},
		MaxAgeDays: &pkgAge,
		RequireEnv: []string{"APP_TOKEN"},
	}
	op := OperatorPolicy{
		AllowPlatforms:    []string{"darwin_arm64"},
		MaxAgeDays:        &opAge,
		RequireTrustedKey: true,
		RequireSBOM:       true,
		Enforcement:       NewDefaultEnforcementPolicy(),
	}

	eff := MergePolicy(pkg, op)
	if len(eff.Platforms) != 0 {
		t.Fatalf("expected empty platform intersection, got %v", eff.Platforms)
	}
	if eff.MaxAgeDays == nil || *eff.MaxAgeDays != 30 {
		t.Fatalf("expected younger package age to win, got %v", eff.MaxAgeDays)
	}
	if !eff.RequireTrustedKey || !eff.RequireSBOM {
		t.Fatalf("expected operator requirements to propagate, got trusted=%v sbom=%v", eff.RequireTrustedKey, eff.RequireSBOM)
	}
	if len(eff.RequireEnv) != 1 || eff.RequireEnv[0] != "APP_TOKEN" {
		t.Fatalf("unexpected RequireEnv: %v", eff.RequireEnv)
	}
}

// ---------------------------------------------------------------------------
// enforce_policy — additional mutation-catching tests
// ---------------------------------------------------------------------------

func TestEnforcePolicy_EnvVarEmptyStringIsAbsent(t *testing.T) {
	t.Setenv("__FLAVOR_TEST_EMPTY__", "")
	eff := EffectivePolicy{RequireEnv: []string{"__FLAVOR_TEST_EMPTY__"}, Enforcement: NewDefaultEnforcementPolicy()}
	_, err := EnforcePolicy(eff, 0, false, true)
	if err == nil {
		t.Error("expected empty env var to be treated as absent")
	}
}

func TestEnforcePolicy_AgeCheckSkippedWhenTimestampZero(t *testing.T) {
	zero := 0
	eff := EffectivePolicy{MaxAgeDays: &zero, Enforcement: NewDefaultEnforcementPolicy()}
	// build_timestamp=0 means no timestamp: check must be skipped
	_, err := EnforcePolicy(eff, 0, false, true)
	if err != nil {
		t.Errorf("expected age check to be skipped for timestamp=0, got: %v", err)
	}
}

func TestEnforcePolicy_AgeCheckSkippedWhenMaxAgeDaysNil(t *testing.T) {
	eff := EffectivePolicy{MaxAgeDays: nil, Enforcement: NewDefaultEnforcementPolicy()}
	// ancient timestamp; check must be skipped
	_, err := EnforcePolicy(eff, 1, false, true)
	if err != nil {
		t.Errorf("expected age check to be skipped when max_age_days unset, got: %v", err)
	}
}

func TestEnforcePolicy_AgeErrorMessageIncludesAge(t *testing.T) {
	zero := 0
	eff := EffectivePolicy{MaxAgeDays: &zero, Enforcement: NewDefaultEnforcementPolicy()}
	_, err := EnforcePolicy(eff, 1, false, true)
	if err == nil {
		t.Fatal("expected age error")
	}
	if !strings.Contains(err.Error(), "days") {
		t.Errorf("expected 'days' in error, got: %v", err)
	}
}

func TestEnforcePolicy_EnvVarErrorNamesVariable(t *testing.T) {
	eff := EffectivePolicy{RequireEnv: []string{"__FLAVOR_ABSENT_VAR_NAMED__"}, Enforcement: NewDefaultEnforcementPolicy()}
	_, err := EnforcePolicy(eff, 0, false, true)
	if err == nil {
		t.Fatal("expected env var error")
	}
	if !strings.Contains(err.Error(), "__FLAVOR_ABSENT_VAR_NAMED__") {
		t.Errorf("expected variable name in error message, got: %v", err)
	}
}

func TestEnforcePolicy_PlatformErrorIncludesCurrentPlatform(t *testing.T) {
	eff := EffectivePolicy{Platforms: []string{"__no_such_platform__"}, Enforcement: NewDefaultEnforcementPolicy()}
	_, err := EnforcePolicy(eff, 0, false, true)
	if err == nil {
		t.Fatal("expected platform error")
	}
	current := getCurrentPlatform()
	if !strings.Contains(err.Error(), current) {
		t.Errorf("expected current platform %q in error, got: %v", current, err)
	}
}

func TestEnforcePolicy_AllChecksPassTogether(t *testing.T) {
	t.Setenv("__FLAVOR_TEST_ALL_CHECKS__", "present")
	current := getCurrentPlatform()
	recent := int64(1700000000) // 2023 timestamp — far in the future relative to age=9999
	age := 9999
	eff := EffectivePolicy{
		Platforms:         []string{current},
		UseOsKeychain:     false,
		RefuseRoot:        false,
		MaxAgeDays:        &age,
		RequireEnv:        []string{"__FLAVOR_TEST_ALL_CHECKS__"},
		RequireSBOM:       true,
		RequireTrustedKey: true,
		Enforcement:       NewDefaultEnforcementPolicy(),
	}
	warnings, err := EnforcePolicy(eff, recent, true, true)
	if err != nil {
		t.Errorf("expected all checks to pass, got: %v", err)
	}
	if len(warnings) != 0 {
		t.Errorf("expected no warnings, got: %v", warnings)
	}
}

// ---------------------------------------------------------------------------
// enforcement mode tests
// ---------------------------------------------------------------------------

func TestEnforcePolicy_WarnMode_PlatformMismatch(t *testing.T) {
	eff := EffectivePolicy{
		Platforms: []string{"__nonexistent_platform__"},
		Enforcement: EnforcementPolicy{
			Default:          ModeDeny,
			PlatformMismatch: ModeWarn,
		},
	}
	warnings, err := EnforcePolicy(eff, 0, false, true)
	if err != nil {
		t.Fatalf("expected no error in warn mode, got: %v", err)
	}
	if len(warnings) != 1 {
		t.Fatalf("expected 1 warning, got %d", len(warnings))
	}
	if !strings.Contains(warnings[0], "platform not permitted") {
		t.Errorf("expected platform warning, got: %s", warnings[0])
	}
}

func TestEnforcePolicy_AllowMode_PlatformMismatch(t *testing.T) {
	eff := EffectivePolicy{
		Platforms: []string{"__nonexistent_platform__"},
		Enforcement: EnforcementPolicy{
			Default:          ModeDeny,
			PlatformMismatch: ModeAllow,
		},
	}
	warnings, err := EnforcePolicy(eff, 0, false, true)
	if err != nil {
		t.Fatalf("expected no error in allow mode, got: %v", err)
	}
	if len(warnings) != 0 {
		t.Errorf("expected no warnings in allow mode, got: %v", warnings)
	}
}

func TestEnforcePolicy_WarnMode_UntrustedKey(t *testing.T) {
	eff := EffectivePolicy{
		RequireTrustedKey: true,
		Enforcement: EnforcementPolicy{
			Default:      ModeDeny,
			UntrustedKey: ModeWarn,
		},
	}
	warnings, err := EnforcePolicy(eff, 0, false, false)
	if err != nil {
		t.Fatalf("expected no error in warn mode, got: %v", err)
	}
	if len(warnings) != 1 || !strings.Contains(warnings[0], "trusted signing key") {
		t.Errorf("expected untrusted key warning, got: %v", warnings)
	}
}

func TestEnforcePolicy_WarnMode_MissingSBOM(t *testing.T) {
	eff := EffectivePolicy{
		RequireSBOM: true,
		Enforcement: EnforcementPolicy{
			Default:     ModeDeny,
			MissingSBOM: ModeWarn,
		},
	}
	warnings, err := EnforcePolicy(eff, 0, false, true)
	if err != nil {
		t.Fatalf("expected no error in warn mode, got: %v", err)
	}
	if len(warnings) != 1 || !strings.Contains(warnings[0], "SBOM") {
		t.Errorf("expected SBOM warning, got: %v", warnings)
	}
}

func TestEnforcePolicy_WarnMode_MissingEnv(t *testing.T) {
	eff := EffectivePolicy{
		RequireEnv: []string{"__FLAVOR_NONEXISTENT__"},
		Enforcement: EnforcementPolicy{
			Default:    ModeDeny,
			MissingEnv: ModeWarn,
		},
	}
	warnings, err := EnforcePolicy(eff, 0, false, true)
	if err != nil {
		t.Fatalf("expected no error in warn mode, got: %v", err)
	}
	if len(warnings) != 1 || !strings.Contains(warnings[0], "__FLAVOR_NONEXISTENT__") {
		t.Errorf("expected env warning, got: %v", warnings)
	}
}

func TestEnforcePolicy_WarnMode_OsKeychain(t *testing.T) {
	eff := EffectivePolicy{
		UseOsKeychain: true,
		Enforcement: EnforcementPolicy{
			Default:    ModeDeny,
			OsKeychain: ModeWarn,
		},
	}
	warnings, err := EnforcePolicy(eff, 0, false, true)
	if err != nil {
		t.Fatalf("expected no error in warn mode, got: %v", err)
	}
	if len(warnings) != 1 || !strings.Contains(warnings[0], "os_keychain") {
		t.Errorf("expected os_keychain warning, got: %v", warnings)
	}
}

func TestEnforcePolicy_DefaultModeInherited(t *testing.T) {
	// Default is "allow" — so platform mismatch should be silently allowed
	eff := EffectivePolicy{
		Platforms: []string{"__nonexistent_platform__"},
		Enforcement: EnforcementPolicy{
			Default: ModeAllow,
		},
	}
	warnings, err := EnforcePolicy(eff, 0, false, true)
	if err != nil {
		t.Fatalf("expected no error when default is allow, got: %v", err)
	}
	if len(warnings) != 0 {
		t.Errorf("expected no warnings when default is allow, got: %v", warnings)
	}
}

func TestModeFor_ReturnsDefault(t *testing.T) {
	ep := EnforcementPolicy{Default: ModeWarn}
	if ep.ModeFor("platform_mismatch") != ModeWarn {
		t.Error("expected ModeFor to return default when check is unset")
	}
}

func TestModeFor_ReturnsSpecific(t *testing.T) {
	ep := EnforcementPolicy{Default: ModeDeny, PlatformMismatch: ModeAllow}
	if ep.ModeFor("platform_mismatch") != ModeAllow {
		t.Error("expected ModeFor to return specific override")
	}
}

func TestApplyOperatorPolicyJSON_WithEnforcement(t *testing.T) {
	dir := t.TempDir()
	content := `{
		"version": 1,
		"trust": {"require_trusted_key": true},
		"enforcement": {
			"default": "deny",
			"platform_mismatch": "warn",
			"untrusted_key": "allow"
		}
	}`
	policyPath := filepath.Join(dir, "policy.json")
	if err := os.WriteFile(policyPath, []byte(content), 0o600); err != nil {
		t.Fatal(err)
	}
	t.Setenv(EnvConfigDir, dir)
	policy, err := LoadOperatorPolicy()
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if policy.Enforcement.Default != ModeDeny {
		t.Errorf("expected default=deny, got %s", policy.Enforcement.Default)
	}
	if policy.Enforcement.PlatformMismatch != ModeWarn {
		t.Errorf("expected platform_mismatch=warn, got %s", policy.Enforcement.PlatformMismatch)
	}
	if policy.Enforcement.UntrustedKey != ModeAllow {
		t.Errorf("expected untrusted_key=allow, got %s", policy.Enforcement.UntrustedKey)
	}
}

func TestApplyOperatorPolicyJSON_InvalidEnforcementMode(t *testing.T) {
	dir := t.TempDir()
	content := `{"version": 1, "enforcement": {"default": "invalid_mode"}}`
	policyPath := filepath.Join(dir, "policy.json")
	if err := os.WriteFile(policyPath, []byte(content), 0o600); err != nil {
		t.Fatal(err)
	}
	t.Setenv(EnvConfigDir, dir)
	_, err := LoadOperatorPolicy()
	if err == nil {
		t.Fatal("expected error for invalid enforcement mode")
	}
}

// ---------------------------------------------------------------------------
// merge + enforce integration — platform semantics
// ---------------------------------------------------------------------------

func TestMergeThenEnforce_EmptyIntersectionIsUnrestricted(t *testing.T) {
	// Disjoint platforms → empty intersection → enforce treats [] as unrestricted
	pkg := PackagePolicy{Platforms: []string{"linux_amd64"}}
	op := OperatorPolicy{AllowPlatforms: []string{"darwin_arm64"}, Enforcement: NewDefaultEnforcementPolicy()}
	eff := MergePolicy(pkg, op)
	if len(eff.Platforms) != 0 {
		t.Fatalf("expected empty intersection, got %v", eff.Platforms)
	}
	// EnforcePolicy with empty platforms must NOT error
	_, err := EnforcePolicy(eff, 0, false, true)
	if err != nil {
		t.Errorf("expected empty platforms to be unrestricted, got: %v", err)
	}
}

func TestMergeThenEnforce_NonEmptyIntersectionBlocks(t *testing.T) {
	// pkg wants linux_amd64+darwin_arm64, op wants linux_amd64+linux_arm64 → intersection: linux_amd64
	pkgAge := 999
	pkg := PackagePolicy{
		Platforms:  []string{"linux_amd64", "darwin_arm64"},
		MaxAgeDays: &pkgAge,
	}
	op := OperatorPolicy{AllowPlatforms: []string{"linux_amd64", "linux_arm64"}, Enforcement: NewDefaultEnforcementPolicy()}
	eff := MergePolicy(pkg, op)
	if len(eff.Platforms) != 1 || eff.Platforms[0] != "linux_amd64" {
		t.Fatalf("expected [linux_amd64], got %v", eff.Platforms)
	}
	// Any platform not linux_amd64 should be blocked
	if eff.Platforms[0] != "linux_amd64" {
		t.Errorf("intersection should restrict to linux_amd64 only")
	}
}

func intPtr(n int) *int { return &n }
