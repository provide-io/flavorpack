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
	}
	if !validPlatforms[p] {
		t.Errorf("unexpected platform: %s", p)
	}
}

func TestMergePolicy_RefuseRoot(t *testing.T) {
	pkg := PackagePolicy{RefuseRoot: false}
	op := OperatorPolicy{RefuseRoot: true}
	eff := MergePolicy(pkg, op)
	if !eff.RefuseRoot {
		t.Error("expected RefuseRoot=true when operator sets it")
	}
}

func TestMergePolicy_MaxAgeDays(t *testing.T) {
	pkg := PackagePolicy{}
	pkg.MaxAgeDays = intPtr(365)
	op := OperatorPolicy{}
	op.MaxAgeDays = intPtr(90)
	eff := MergePolicy(pkg, op)
	if eff.MaxAgeDays == nil || *eff.MaxAgeDays != 90 {
		t.Errorf("expected max_age_days=90, got %v", eff.MaxAgeDays)
	}
}

func TestMergePolicy_OperatorFlagsPropagated(t *testing.T) {
	pkg := PackagePolicy{}
	op := OperatorPolicy{RequireTrustedKey: true, UseOsKeychain: true, RequireSBOM: true}
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

func TestMergePolicy_Platforms_Intersection(t *testing.T) {
	pkg := PackagePolicy{Platforms: []string{"linux_amd64", "darwin_arm64"}}
	op := OperatorPolicy{AllowPlatforms: []string{"linux_amd64", "linux_arm64"}}
	eff := MergePolicy(pkg, op)
	if len(eff.Platforms) != 1 || eff.Platforms[0] != "linux_amd64" {
		t.Errorf("expected [linux_amd64], got %v", eff.Platforms)
	}
}

func TestMergePolicy_Platforms_OnlyOperator(t *testing.T) {
	pkg := PackagePolicy{}
	op := OperatorPolicy{AllowPlatforms: []string{"linux_amd64"}}
	eff := MergePolicy(pkg, op)
	if len(eff.Platforms) != 1 || eff.Platforms[0] != "linux_amd64" {
		t.Errorf("expected [linux_amd64], got %v", eff.Platforms)
	}
}

func TestMergePolicy_Platforms_OnlyPackage(t *testing.T) {
	pkg := PackagePolicy{Platforms: []string{"darwin_arm64"}}
	op := OperatorPolicy{}
	eff := MergePolicy(pkg, op)
	if len(eff.Platforms) != 1 || eff.Platforms[0] != "darwin_arm64" {
		t.Errorf("expected [darwin_arm64], got %v", eff.Platforms)
	}
}

func TestEnforcePolicy_Permissive(t *testing.T) {
	eff := EffectivePolicy{}
	if err := EnforcePolicy(eff, 0, false, true); err != nil {
		t.Errorf("expected no error, got: %v", err)
	}
}

func TestEnforcePolicy_UseOsKeychainUnsupported(t *testing.T) {
	eff := EffectivePolicy{UseOsKeychain: true}
	if err := EnforcePolicy(eff, 0, false, true); err == nil {
		t.Fatal("expected use_os_keychain to be rejected")
	}
}

func TestEnforcePolicy_PlatformBlocked(t *testing.T) {
	eff := EffectivePolicy{Platforms: []string{"__nonexistent_platform__"}}
	if err := EnforcePolicy(eff, 0, false, true); err == nil {
		t.Error("expected platform error")
	}
}

func TestEnforcePolicy_SBOMRequired(t *testing.T) {
	eff := EffectivePolicy{RequireSBOM: true}
	if err := EnforcePolicy(eff, 0, false, true); err == nil {
		t.Error("expected SBOM error")
	}
	if err := EnforcePolicy(eff, 0, true, true); err != nil {
		t.Errorf("expected no error when hasSBOM=true, got: %v", err)
	}
}

func TestEnforcePolicy_EnvVarMissing(t *testing.T) {
	eff := EffectivePolicy{RequireEnv: []string{"__FLAVOR_TEST_VAR_NONEXISTENT__"}}
	if err := EnforcePolicy(eff, 0, false, true); err == nil {
		t.Error("expected env var error")
	}
}

func TestEnforcePolicy_EnvVarPresent(t *testing.T) {
	t.Setenv("__FLAVOR_TEST_VAR__", "1")
	eff := EffectivePolicy{RequireEnv: []string{"__FLAVOR_TEST_VAR__"}}
	if err := EnforcePolicy(eff, 0, false, true); err != nil {
		t.Errorf("expected no error, got: %v", err)
	}
}

func TestEnforcePolicy_AgeExceeded(t *testing.T) {
	zero := 0
	eff := EffectivePolicy{MaxAgeDays: &zero}
	// Build timestamp of 1 (ancient) should trigger age check
	if err := EnforcePolicy(eff, 1, false, true); err == nil {
		t.Error("expected age error")
	}
}

func TestEnforcePolicy_RequireTrustedKey_UntrustedKey(t *testing.T) {
	eff := EffectivePolicy{RequireTrustedKey: true}
	if err := EnforcePolicy(eff, 0, false, false); err == nil {
		t.Error("expected error when key is untrusted and require_trusted_key=true")
	}
}

func TestEnforcePolicy_RequireTrustedKey_TrustedKey(t *testing.T) {
	eff := EffectivePolicy{RequireTrustedKey: true}
	if err := EnforcePolicy(eff, 0, false, true); err != nil {
		t.Errorf("expected no error when key is trusted, got: %v", err)
	}
}

func TestEnforcePolicy_RequireTrustedKey_NotRequired(t *testing.T) {
	eff := EffectivePolicy{RequireTrustedKey: false}
	// Even untrusted key should pass when policy doesn't require it
	if err := EnforcePolicy(eff, 0, false, false); err != nil {
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
	content := "[trust]\nrequire_trusted_key = true\n[execution]\nrefuse_root = true\n"
	if err := os.WriteFile(filepath.Join(dir, "policy.toml"), []byte(content), 0600); err != nil {
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
	want := filepath.Join("/tmp/xdg", "flavor", "policy.toml")
	if path != want {
		t.Errorf("unexpected path: %s (want %s)", path, want)
	}
}

func TestGetUserPolicyFile_Home(t *testing.T) {
	t.Setenv(EnvConfigDir, "")
	t.Setenv("XDG_CONFIG_HOME", "")
	t.Setenv("HOME", "/home/user")
	path := getUserPolicyFile()
	want := filepath.Join("/home/user", ".config", "flavor", "policy.toml")
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
	policyDir := filepath.Join(dir, "policy.toml")
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
	policyPath := filepath.Join(dir, "policy.toml")
	if err := os.WriteFile(policyPath, []byte("[broken toml\nnot valid ===\n"), 0o600); err != nil {
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
	systemPath := filepath.Join(dir, "system-policy.toml")
	if err := os.WriteFile(systemPath, []byte("[broken toml\nnot valid ===\n"), 0o600); err != nil {
		t.Fatalf("WriteFile(system policy) error = %v", err)
	}

	oldSystem := getSystemPolicyFileImpl
	oldUser := getUserPolicyFileImpl
	t.Cleanup(func() {
		getSystemPolicyFileImpl = oldSystem
		getUserPolicyFileImpl = oldUser
	})

	getSystemPolicyFileImpl = func() string { return systemPath }
	getUserPolicyFileImpl = func() string { return filepath.Join(dir, "missing-user-policy.toml") }

	_, err := LoadOperatorPolicy()
	if err == nil {
		t.Fatal("expected malformed system policy to fail closed")
	}
}

func TestLoadOperatorPolicyRejectsUnknownUserPolicyKey(t *testing.T) {
	dir := t.TempDir()
	policyPath := filepath.Join(dir, "policy.toml")
	if err := os.WriteFile(policyPath, []byte("[trust]\nrequire_trusted_key = true\nunexpected = true\n"), 0o600); err != nil {
		t.Fatalf("WriteFile(policy) error = %v", err)
	}

	t.Setenv(EnvConfigDir, dir)
	_, err := LoadOperatorPolicy()
	if err == nil {
		t.Fatal("expected unknown user policy key to fail closed")
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
	eff := EffectivePolicy{RequireEnv: []string{"__FLAVOR_TEST_EMPTY__"}}
	if err := EnforcePolicy(eff, 0, false, true); err == nil {
		t.Error("expected empty env var to be treated as absent")
	}
}

func TestEnforcePolicy_AgeCheckSkippedWhenTimestampZero(t *testing.T) {
	zero := 0
	eff := EffectivePolicy{MaxAgeDays: &zero}
	// build_timestamp=0 means no timestamp: check must be skipped
	if err := EnforcePolicy(eff, 0, false, true); err != nil {
		t.Errorf("expected age check to be skipped for timestamp=0, got: %v", err)
	}
}

func TestEnforcePolicy_AgeCheckSkippedWhenMaxAgeDaysNil(t *testing.T) {
	eff := EffectivePolicy{MaxAgeDays: nil}
	// ancient timestamp; check must be skipped
	if err := EnforcePolicy(eff, 1, false, true); err != nil {
		t.Errorf("expected age check to be skipped when max_age_days unset, got: %v", err)
	}
}

func TestEnforcePolicy_AgeErrorMessageIncludesAge(t *testing.T) {
	zero := 0
	eff := EffectivePolicy{MaxAgeDays: &zero}
	err := EnforcePolicy(eff, 1, false, true)
	if err == nil {
		t.Fatal("expected age error")
	}
	if !strings.Contains(err.Error(), "days") {
		t.Errorf("expected 'days' in error, got: %v", err)
	}
}

func TestEnforcePolicy_EnvVarErrorNamesVariable(t *testing.T) {
	eff := EffectivePolicy{RequireEnv: []string{"__FLAVOR_ABSENT_VAR_NAMED__"}}
	err := EnforcePolicy(eff, 0, false, true)
	if err == nil {
		t.Fatal("expected env var error")
	}
	if !strings.Contains(err.Error(), "__FLAVOR_ABSENT_VAR_NAMED__") {
		t.Errorf("expected variable name in error message, got: %v", err)
	}
}

func TestEnforcePolicy_PlatformErrorIncludesCurrentPlatform(t *testing.T) {
	eff := EffectivePolicy{Platforms: []string{"__no_such_platform__"}}
	err := EnforcePolicy(eff, 0, false, true)
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
	}
	if err := EnforcePolicy(eff, recent, true, true); err != nil {
		t.Errorf("expected all checks to pass, got: %v", err)
	}
}

// ---------------------------------------------------------------------------
// merge + enforce integration — platform semantics
// ---------------------------------------------------------------------------

func TestMergeThenEnforce_EmptyIntersectionIsUnrestricted(t *testing.T) {
	// Disjoint platforms → empty intersection → enforce treats [] as unrestricted
	pkg := PackagePolicy{Platforms: []string{"linux_amd64"}}
	op := OperatorPolicy{AllowPlatforms: []string{"darwin_arm64"}}
	eff := MergePolicy(pkg, op)
	if len(eff.Platforms) != 0 {
		t.Fatalf("expected empty intersection, got %v", eff.Platforms)
	}
	// EnforcePolicy with empty platforms must NOT error
	if err := EnforcePolicy(eff, 0, false, true); err != nil {
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
	op := OperatorPolicy{AllowPlatforms: []string{"linux_amd64", "linux_arm64"}}
	eff := MergePolicy(pkg, op)
	if len(eff.Platforms) != 1 || eff.Platforms[0] != "linux_amd64" {
		t.Fatalf("expected [linux_amd64], got %v", eff.Platforms)
	}
	// Any platform not linux_amd64 should be blocked
	// We can't control getCurrentPlatform() here, but we can verify the restriction is present
	if eff.Platforms[0] != "linux_amd64" {
		t.Errorf("intersection should restrict to linux_amd64 only")
	}
}

func intPtr(n int) *int { return &n }

// ---------------------------------------------------------------------------
// applyAttestationPolicySection — exercise via LoadOperatorPolicy + TOML
// ---------------------------------------------------------------------------

func TestLoadOperatorPolicy_UnknownTopLevelSection(t *testing.T) {
	dir := t.TempDir()
	if err := os.WriteFile(filepath.Join(dir, "policy.toml"), []byte("[unknown_section]\nkey = true\n"), 0o600); err != nil {
		t.Fatal(err)
	}
	t.Setenv(EnvConfigDir, dir)
	if _, err := LoadOperatorPolicy(); err == nil {
		t.Fatal("expected error for unknown top-level policy section")
	}
}

func TestLoadOperatorPolicy_AttestationRequireSBOM(t *testing.T) {
	dir := t.TempDir()
	if err := os.WriteFile(filepath.Join(dir, "policy.toml"), []byte("[attestation]\nrequire_sbom = true\n"), 0o600); err != nil {
		t.Fatal(err)
	}
	t.Setenv(EnvConfigDir, dir)
	policy, err := LoadOperatorPolicy()
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if !policy.RequireSBOM {
		t.Error("expected RequireSBOM=true")
	}
}

func TestLoadOperatorPolicy_AttestationUnknownKey(t *testing.T) {
	dir := t.TempDir()
	if err := os.WriteFile(filepath.Join(dir, "policy.toml"), []byte("[attestation]\nunknown_key = true\n"), 0o600); err != nil {
		t.Fatal(err)
	}
	t.Setenv(EnvConfigDir, dir)
	if _, err := LoadOperatorPolicy(); err == nil {
		t.Fatal("expected error for unknown attestation key")
	}
}

// ---------------------------------------------------------------------------
// applyExecutionPolicySection — max_age_days, allow_platforms, unknown key
// ---------------------------------------------------------------------------

func TestLoadOperatorPolicy_ExecutionMaxAgeDays(t *testing.T) {
	dir := t.TempDir()
	if err := os.WriteFile(filepath.Join(dir, "policy.toml"), []byte("[execution]\nmax_age_days = 30\n"), 0o600); err != nil {
		t.Fatal(err)
	}
	t.Setenv(EnvConfigDir, dir)
	policy, err := LoadOperatorPolicy()
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if policy.MaxAgeDays == nil || *policy.MaxAgeDays != 30 {
		t.Errorf("expected max_age_days=30, got %v", policy.MaxAgeDays)
	}
}

func TestLoadOperatorPolicy_ExecutionAllowPlatforms(t *testing.T) {
	dir := t.TempDir()
	if err := os.WriteFile(filepath.Join(dir, "policy.toml"), []byte("[execution]\nallow_platforms = [\"linux_amd64\"]\n"), 0o600); err != nil {
		t.Fatal(err)
	}
	t.Setenv(EnvConfigDir, dir)
	policy, err := LoadOperatorPolicy()
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if len(policy.AllowPlatforms) != 1 || policy.AllowPlatforms[0] != "linux_amd64" {
		t.Errorf("unexpected AllowPlatforms: %v", policy.AllowPlatforms)
	}
}

func TestLoadOperatorPolicy_ExecutionUnknownKey(t *testing.T) {
	dir := t.TempDir()
	if err := os.WriteFile(filepath.Join(dir, "policy.toml"), []byte("[execution]\nunknown_key = true\n"), 0o600); err != nil {
		t.Fatal(err)
	}
	t.Setenv(EnvConfigDir, dir)
	if _, err := LoadOperatorPolicy(); err == nil {
		t.Fatal("expected error for unknown execution key")
	}
}

// ---------------------------------------------------------------------------
// mustStringList — all type branches
// ---------------------------------------------------------------------------

func TestMustStringList_StringSlice(t *testing.T) {
	got, err := mustStringList("f", []string{"a", "b"})
	if err != nil || len(got) != 2 || got[0] != "a" {
		t.Fatalf("mustStringList([]string) = %v %v", got, err)
	}
}

func TestMustStringList_AnySliceNonString(t *testing.T) {
	if _, err := mustStringList("f", []any{"ok", 42}); err == nil {
		t.Fatal("expected error for non-string item in []any")
	}
}

// ---------------------------------------------------------------------------
// applyTrustPolicySection — wrong-type errors
// ---------------------------------------------------------------------------

func TestLoadOperatorPolicy_TrustRequireTrustedKeyWrongType(t *testing.T) {
	dir := t.TempDir()
	if err := os.WriteFile(filepath.Join(dir, "policy.toml"), []byte("[trust]\nrequire_trusted_key = 1\n"), 0o600); err != nil {
		t.Fatal(err)
	}
	t.Setenv(EnvConfigDir, dir)
	if _, err := LoadOperatorPolicy(); err == nil {
		t.Fatal("expected type error for non-boolean require_trusted_key")
	}
}

func TestLoadOperatorPolicy_TrustUseOsKeychainWrongType(t *testing.T) {
	dir := t.TempDir()
	if err := os.WriteFile(filepath.Join(dir, "policy.toml"), []byte("[trust]\nuse_os_keychain = 42\n"), 0o600); err != nil {
		t.Fatal(err)
	}
	t.Setenv(EnvConfigDir, dir)
	if _, err := LoadOperatorPolicy(); err == nil {
		t.Fatal("expected type error for non-boolean use_os_keychain")
	}
}

// ---------------------------------------------------------------------------
// applyXxxPolicySection — mustPolicySection non-table error propagation
// These paths are unreachable via the TOML loader (which always produces
// map[string]any for table keys), so we call the functions directly.
// ---------------------------------------------------------------------------

func TestApplyTrustPolicySectionRejectsNonTable(t *testing.T) {
	if err := applyTrustPolicySection("not-a-table", &OperatorPolicy{}); err == nil {
		t.Fatal("expected error for non-table [trust] input")
	}
}

func TestApplyExecutionPolicySectionRejectsNonTable(t *testing.T) {
	if err := applyExecutionPolicySection("not-a-table", &OperatorPolicy{}); err == nil {
		t.Fatal("expected error for non-table [execution] input")
	}
}

func TestApplyAttestationPolicySectionRejectsNonTable(t *testing.T) {
	if err := applyAttestationPolicySection("not-a-table", &OperatorPolicy{}); err == nil {
		t.Fatal("expected error for non-table [attestation] input")
	}
}

// ---------------------------------------------------------------------------
// mustPolicySection — nil and non-table inputs
// ---------------------------------------------------------------------------

func TestMustPolicySection_NilIsPermitted(t *testing.T) {
	m, err := mustPolicySection("trust", nil)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if m != nil {
		t.Errorf("expected nil map for nil input, got %v", m)
	}
}

func TestMustPolicySection_NonTableReturnsError(t *testing.T) {
	if _, err := mustPolicySection("trust", "not-a-table"); err == nil {
		t.Fatal("expected error for non-table input")
	}
}

// ---------------------------------------------------------------------------
// mustBool — wrong type
// ---------------------------------------------------------------------------

func TestMustBool_InvalidType(t *testing.T) {
	if _, err := mustBool("field", "yes"); err == nil {
		t.Fatal("expected error for string input to mustBool")
	}
}

// ---------------------------------------------------------------------------
// mustInt — all integer type branches including overflow
// ---------------------------------------------------------------------------

// ---------------------------------------------------------------------------
// applyAttestationPolicySection / applyExecutionPolicySection — type-error paths
// ---------------------------------------------------------------------------

func TestLoadOperatorPolicy_AttestationRequireSBOMWrongType(t *testing.T) {
	dir := t.TempDir()
	// TOML integers are not booleans — mustBool should reject this.
	if err := os.WriteFile(filepath.Join(dir, "policy.toml"), []byte("[attestation]\nrequire_sbom = 1\n"), 0o600); err != nil {
		t.Fatal(err)
	}
	t.Setenv(EnvConfigDir, dir)
	if _, err := LoadOperatorPolicy(); err == nil {
		t.Fatal("expected type error for non-boolean require_sbom")
	}
}

func TestLoadOperatorPolicy_ExecutionMaxAgeDaysWrongType(t *testing.T) {
	dir := t.TempDir()
	// TOML string is not an integer — mustInt should reject this.
	if err := os.WriteFile(filepath.Join(dir, "policy.toml"), []byte("[execution]\nmax_age_days = \"thirty\"\n"), 0o600); err != nil {
		t.Fatal(err)
	}
	t.Setenv(EnvConfigDir, dir)
	if _, err := LoadOperatorPolicy(); err == nil {
		t.Fatal("expected type error for non-integer max_age_days")
	}
}

func TestLoadOperatorPolicy_ExecutionAllowPlatformsWrongType(t *testing.T) {
	dir := t.TempDir()
	// TOML integer is not a string list — mustStringList should reject this.
	if err := os.WriteFile(filepath.Join(dir, "policy.toml"), []byte("[execution]\nallow_platforms = 42\n"), 0o600); err != nil {
		t.Fatal(err)
	}
	t.Setenv(EnvConfigDir, dir)
	if _, err := LoadOperatorPolicy(); err == nil {
		t.Fatal("expected type error for non-list allow_platforms")
	}
}

func TestMustInt_AllTypes(t *testing.T) {
	maxInt := int(^uint(0) >> 1)

	cases := []struct {
		name    string
		input   any
		want    int
		wantErr bool
	}{
		{"int", int(7), 7, false},
		{"int8", int8(8), 8, false},
		{"int16", int16(16), 16, false},
		{"int32", int32(32), 32, false},
		{"int64-ok", int64(64), 64, false},
		{"uint-ok", uint(9), 9, false},
		{"uint8", uint8(3), 3, false},
		{"uint16", uint16(5), 5, false},
		{"uint32", uint32(11), 11, false},
		{"uint64-ok", uint64(13), 13, false},
		// uint64(maxInt)+1 reliably overflows on both 32-bit and 64-bit platforms
		// because uint64 is always 64-bit while int is platform-sized.
		{"uint64-overflow", uint64(maxInt) + 1, 0, true},
		{"invalid", "not-int", 0, true},
	}

	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			got, err := mustInt("f", tc.input)
			if tc.wantErr {
				if err == nil {
					t.Fatalf("expected error, got %d", got)
				}
				return
			}
			if err != nil {
				t.Fatalf("unexpected error: %v", err)
			}
			if got != tc.want {
				t.Errorf("got %d, want %d", got, tc.want)
			}
		})
	}
}

// TestLoadOperatorPolicySkipsEmptyPaths covers the `if path == "" { continue }` branch
// in LoadOperatorPolicy by forcing both path factories to return "".
func TestLoadOperatorPolicySkipsEmptyPaths(t *testing.T) {
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
		t.Fatalf("expected no error with empty paths, got: %v", err)
	}
	_ = policy
}
