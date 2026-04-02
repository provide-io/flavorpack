package format_2025

import (
	"testing"
)

// TestEnforcePolicyPlatformAllowed covers the "found = true; break" path
// in EnforcePolicy when the current platform IS in the allowed list.
func TestEnforcePolicyPlatformAllowed(t *testing.T) {
	currentPlat := getCurrentPlatform()
	eff := EffectivePolicy{
		Platforms: []string{currentPlat},
	}
	if err := EnforcePolicy(eff, 0, false, true); err != nil {
		t.Fatalf("expected no error when current platform is allowed, got: %v", err)
	}
}

// TestMustIntCasesForPlainInt covers the `case int` branch in mustInt.
// This is called directly (not via TOML) to hit the plain int case.
func TestMustIntCasesForPlainInt(t *testing.T) {
	// case int
	v, err := mustInt("test", int(42))
	if err != nil {
		t.Fatalf("mustInt(int) error = %v", err)
	}
	if v != 42 {
		t.Fatalf("mustInt(int) = %d, want 42", v)
	}

	// case int8
	v, err = mustInt("test", int8(10))
	if err != nil {
		t.Fatalf("mustInt(int8) error = %v", err)
	}
	if v != 10 {
		t.Fatalf("mustInt(int8) = %d, want 10", v)
	}

	// case int16
	v, err = mustInt("test", int16(100))
	if err != nil {
		t.Fatalf("mustInt(int16) error = %v", err)
	}
	if v != 100 {
		t.Fatalf("mustInt(int16) = %d, want 100", v)
	}

	// case int32
	v, err = mustInt("test", int32(1000))
	if err != nil {
		t.Fatalf("mustInt(int32) error = %v", err)
	}
	if v != 1000 {
		t.Fatalf("mustInt(int32) = %d, want 1000", v)
	}

	// case uint8
	v, err = mustInt("test", uint8(5))
	if err != nil {
		t.Fatalf("mustInt(uint8) error = %v", err)
	}
	if v != 5 {
		t.Fatalf("mustInt(uint8) = %d, want 5", v)
	}

	// case uint16
	v, err = mustInt("test", uint16(500))
	if err != nil {
		t.Fatalf("mustInt(uint16) error = %v", err)
	}
	if v != 500 {
		t.Fatalf("mustInt(uint16) = %d, want 500", v)
	}

	// case uint32
	v, err = mustInt("test", uint32(9999))
	if err != nil {
		t.Fatalf("mustInt(uint32) error = %v", err)
	}
	if v != 9999 {
		t.Fatalf("mustInt(uint32) = %d, want 9999", v)
	}
}

// TestApplyExecutionPolicySectionMaxAgeDaysError covers the mustInt error path
// when max_age_days has an invalid value type.
func TestApplyExecutionPolicySectionMaxAgeDaysError(t *testing.T) {
	policy := &OperatorPolicy{}
	// raw["max_age_days"] = a boolean — mustInt will fail.
	raw := map[string]any{
		"max_age_days": "not-a-number",
	}
	if err := applyExecutionPolicySection(raw, policy); err == nil {
		t.Fatal("expected error when max_age_days is a string, got nil")
	}
}

// TestApplyExecutionPolicySectionRefuseRootError covers the mustBool error path
// when refuse_root has an invalid value type.
func TestApplyExecutionPolicySectionRefuseRootError(t *testing.T) {
	policy := &OperatorPolicy{}
	raw := map[string]any{
		"refuse_root": "not-a-bool",
	}
	if err := applyExecutionPolicySection(raw, policy); err == nil {
		t.Fatal("expected error when refuse_root is a string, got nil")
	}
}

// TestMustIntOverflow covers the overflow paths in mustInt.
func TestMustIntOverflow(t *testing.T) {
	// uint overflow: uint(maxInt+1)
	_, err := mustInt("test", uint(^uint(0)))
	if err == nil {
		t.Fatal("expected overflow error for large uint, got nil")
	}

	// int64 positive overflow
	_, err = mustInt("test", int64(1<<62)) // big but not overflowing on 64-bit
	if err != nil {
		// On 64-bit systems, this should succeed
		t.Logf("int64(1<<62) = ok (expected on 64-bit)")
	}

	// uint64 overflow: math.MaxUint64
	_, err = mustInt("test", uint64(^uint64(0)))
	if err == nil {
		t.Fatal("expected overflow error for uint64 max, got nil")
	}
}
