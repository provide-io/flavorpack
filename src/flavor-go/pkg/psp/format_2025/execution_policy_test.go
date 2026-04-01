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

func TestParseMinimalTOML_MaxAgeDays(t *testing.T) {
	content := "[execution]\nmax_age_days = 90\n"
	policy := OperatorPolicy{}
	parseMinimalTOML([]byte(content), &policy)
	if policy.MaxAgeDays == nil || *policy.MaxAgeDays != 90 {
		t.Errorf("expected max_age_days=90, got %v", policy.MaxAgeDays)
	}
}

func TestParseMinimalTOML_RequireSBOM(t *testing.T) {
	content := "[attestation]\nrequire_sbom = true\n"
	policy := OperatorPolicy{}
	parseMinimalTOML([]byte(content), &policy)
	if !policy.RequireSBOM {
		t.Error("expected require_sbom=true")
	}
}

func TestParseMinimalTOML_IgnoresComments(t *testing.T) {
	content := "# comment\n[trust]\n# another comment\nrequire_trusted_key = true\n"
	policy := OperatorPolicy{}
	parseMinimalTOML([]byte(content), &policy)
	if !policy.RequireTrustedKey {
		t.Error("expected require_trusted_key=true after ignoring comments")
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

func TestParseMinimalTOML_InlineComment(t *testing.T) {
	content := "[execution]\nrefuse_root = true # disable if needed\n"
	policy := OperatorPolicy{}
	parseMinimalTOML([]byte(content), &policy)
	if !policy.RefuseRoot {
		t.Error("expected refuse_root=true after stripping inline comment")
	}
}

func TestParseMinimalTOML_AllowPlatforms(t *testing.T) {
	content := "[execution]\nallow_platforms = [\"linux_amd64\", \"linux_arm64\"]\n"
	policy := OperatorPolicy{}
	parseMinimalTOML([]byte(content), &policy)
	if len(policy.AllowPlatforms) != 2 {
		t.Errorf("expected 2 platforms, got %d: %v", len(policy.AllowPlatforms), policy.AllowPlatforms)
	}
	if policy.AllowPlatforms[0] != "linux_amd64" {
		t.Errorf("expected linux_amd64, got %s", policy.AllowPlatforms[0])
	}
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

func TestParseMinimalTOMLParsesExtendedFieldsAndListFallback(t *testing.T) {
	content := "[trust]\nuse_os_keychain = true\n[execution]\nmax_age_days = not-a-number\nallow_platforms = ['linux_amd64', \"linux_arm64\"]\n[attestation]\nrequire_sbom = true\n"
	policy := OperatorPolicy{}
	parseMinimalTOML([]byte(content), &policy)

	if !policy.UseOsKeychain {
		t.Fatal("expected use_os_keychain=true")
	}
	if policy.MaxAgeDays != nil {
		t.Fatalf("expected invalid max_age_days to be ignored, got %v", policy.MaxAgeDays)
	}
	if !policy.RequireSBOM {
		t.Fatal("expected require_sbom=true")
	}
	if len(policy.AllowPlatforms) != 2 || policy.AllowPlatforms[0] != "linux_amd64" || policy.AllowPlatforms[1] != "linux_arm64" {
		t.Fatalf("unexpected allow_platforms: %v", policy.AllowPlatforms)
	}
	if got := parseTOMLStringList("not-a-list"); got != nil {
		t.Fatalf("parseTOMLStringList() = %v, want nil for invalid input", got)
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

func intPtr(n int) *int { return &n }
