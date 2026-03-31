package format_2025

import (
	"os"
	"path/filepath"
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
	if err := EnforcePolicy(eff, 0, false); err != nil {
		t.Errorf("expected no error, got: %v", err)
	}
}

func TestEnforcePolicy_PlatformBlocked(t *testing.T) {
	eff := EffectivePolicy{Platforms: []string{"__nonexistent_platform__"}}
	if err := EnforcePolicy(eff, 0, false); err == nil {
		t.Error("expected platform error")
	}
}

func TestEnforcePolicy_SBOMRequired(t *testing.T) {
	eff := EffectivePolicy{RequireSBOM: true}
	if err := EnforcePolicy(eff, 0, false); err == nil {
		t.Error("expected SBOM error")
	}
	if err := EnforcePolicy(eff, 0, true); err != nil {
		t.Errorf("expected no error when hasSBOM=true, got: %v", err)
	}
}

func TestEnforcePolicy_EnvVarMissing(t *testing.T) {
	eff := EffectivePolicy{RequireEnv: []string{"__FLAVOR_TEST_VAR_NONEXISTENT__"}}
	if err := EnforcePolicy(eff, 0, false); err == nil {
		t.Error("expected env var error")
	}
}

func TestEnforcePolicy_EnvVarPresent(t *testing.T) {
	t.Setenv("__FLAVOR_TEST_VAR__", "1")
	eff := EffectivePolicy{RequireEnv: []string{"__FLAVOR_TEST_VAR__"}}
	if err := EnforcePolicy(eff, 0, false); err != nil {
		t.Errorf("expected no error, got: %v", err)
	}
}

func TestEnforcePolicy_AgeExceeded(t *testing.T) {
	zero := 0
	eff := EffectivePolicy{MaxAgeDays: &zero}
	// Build timestamp of 1 (ancient) should trigger age check
	if err := EnforcePolicy(eff, 1, false); err == nil {
		t.Error("expected age error")
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
	t.Setenv("FLAVOR_CONFIG_DIR", dir)
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
	t.Setenv("FLAVOR_CONFIG_DIR", dir)
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
	t.Setenv("FLAVOR_CONFIG_DIR", "")
	t.Setenv("XDG_CONFIG_HOME", "/tmp/xdg")
	t.Setenv("HOME", "")
	path := getUserPolicyFile()
	if path != "/tmp/xdg/flavor/policy.toml" {
		t.Errorf("unexpected path: %s", path)
	}
}

func TestGetUserPolicyFile_Home(t *testing.T) {
	t.Setenv("FLAVOR_CONFIG_DIR", "")
	t.Setenv("XDG_CONFIG_HOME", "")
	t.Setenv("HOME", "/home/user")
	path := getUserPolicyFile()
	if path != "/home/user/.config/flavor/policy.toml" {
		t.Errorf("unexpected path: %s", path)
	}
}

func TestGetUserPolicyFile_NoEnv(t *testing.T) {
	t.Setenv("FLAVOR_CONFIG_DIR", "")
	t.Setenv("XDG_CONFIG_HOME", "")
	t.Setenv("HOME", "")
	// Should return "" or some default — just confirm no panic
	_ = getUserPolicyFile()
}

func intPtr(n int) *int { return &n }
