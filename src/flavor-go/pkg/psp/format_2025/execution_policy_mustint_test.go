// SPDX-FileCopyrightText: Copyright (c) 2026 provide.io llc. All rights reserved.
// SPDX-License-Identifier: Apache-2.0

package format_2025

import (
	"testing"
)

// TestApplyOperatorPolicyJSON_VersionZero covers the version=0 error path
// in applyOperatorPolicyJSON (version field present but zero).
func TestApplyOperatorPolicyJSON_VersionZero(t *testing.T) {
	policy := &OperatorPolicy{Enforcement: NewDefaultEnforcementPolicy()}
	// version is explicitly 0 (treated as missing)
	data := []byte(`{"version": 0, "trust": {"require_trusted_key": true}}`)
	err := applyOperatorPolicyJSON(data, policy)
	if err == nil {
		t.Fatal("expected error for version=0, got nil")
	}
}

// TestApplyOperatorPolicyJSON_FutureVersion covers the version>1 warning path.
func TestApplyOperatorPolicyJSON_FutureVersion(t *testing.T) {
	policy := &OperatorPolicy{Enforcement: NewDefaultEnforcementPolicy()}
	data := []byte(`{"version": 99, "trust": {"require_trusted_key": true}}`)
	err := applyOperatorPolicyJSON(data, policy)
	if err != nil {
		t.Fatalf("expected no error for future version (warn only), got: %v", err)
	}
	if !policy.RequireTrustedKey {
		t.Error("expected require_trusted_key=true even with future version")
	}
}

// TestApplyOperatorPolicyJSON_AllEnforcementFields covers setting every enforcement field.
func TestApplyOperatorPolicyJSON_AllEnforcementFields(t *testing.T) {
	policy := &OperatorPolicy{Enforcement: NewDefaultEnforcementPolicy()}
	data := []byte(`{
		"version": 1,
		"enforcement": {
			"default": "warn",
			"platform_mismatch": "allow",
			"untrusted_key": "deny",
			"expired_package": "warn",
			"missing_env": "allow",
			"missing_sbom": "deny",
			"root_execution": "warn",
			"os_keychain": "allow"
		}
	}`)
	err := applyOperatorPolicyJSON(data, policy)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if policy.Enforcement.Default != ModeWarn {
		t.Errorf("default = %s, want warn", policy.Enforcement.Default)
	}
	if policy.Enforcement.PlatformMismatch != ModeAllow {
		t.Errorf("platform_mismatch = %s, want allow", policy.Enforcement.PlatformMismatch)
	}
	if policy.Enforcement.UntrustedKey != ModeDeny {
		t.Errorf("untrusted_key = %s, want deny", policy.Enforcement.UntrustedKey)
	}
	if policy.Enforcement.ExpiredPackage != ModeWarn {
		t.Errorf("expired_package = %s, want warn", policy.Enforcement.ExpiredPackage)
	}
	if policy.Enforcement.MissingEnv != ModeAllow {
		t.Errorf("missing_env = %s, want allow", policy.Enforcement.MissingEnv)
	}
	if policy.Enforcement.MissingSBOM != ModeDeny {
		t.Errorf("missing_sbom = %s, want deny", policy.Enforcement.MissingSBOM)
	}
	if policy.Enforcement.RootExecution != ModeWarn {
		t.Errorf("root_execution = %s, want warn", policy.Enforcement.RootExecution)
	}
	if policy.Enforcement.OsKeychain != ModeAllow {
		t.Errorf("os_keychain = %s, want allow", policy.Enforcement.OsKeychain)
	}
}
