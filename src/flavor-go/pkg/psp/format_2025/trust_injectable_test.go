package format_2025

import (
	"os"
	"path/filepath"
	"testing"
)

// TestLoadTrustedKeysSystemDirErrorViaInjectable covers the missing error-return
// path in LoadTrustedKeys (trust.go:157-159) when the system trusted-keys directory
// path is a file (not a directory), causing loadKeysFromDir to fail.
//
// This test uses the getSystemConfigRootFn injectable to point the system config
// root at a temp directory where we can create a file at the expected path.
func TestLoadTrustedKeysSystemDirErrorViaInjectable(t *testing.T) {
	// Cannot use t.Parallel() — t.Setenv is not parallel-safe.

	// Create a temp dir to use as the "system config root".
	sysRoot := t.TempDir()

	// Create a regular FILE at sysRoot/trusted-keys — loadKeysFromDir will fail
	// when it tries to read this as a directory.
	trustedKeysFile := filepath.Join(sysRoot, "trusted-keys")
	if err := os.WriteFile(trustedKeysFile, []byte("not a directory"), 0o600); err != nil {
		t.Fatalf("WriteFile(trusted-keys-as-file): %v", err)
	}

	// Point user trusted-keys dir to a non-existent path (returns nil from loadKeysFromDir).
	t.Setenv(EnvTrustedKeysDir, filepath.Join(t.TempDir(), "nonexistent"))

	// Override the system config root to use our temp directory.
	old := getSystemConfigRootFn
	getSystemConfigRootFn = func() string { return sysRoot }
	t.Cleanup(func() { getSystemConfigRootFn = old })

	// LoadTrustedKeys with includeSystem=true should fail because the system
	// trusted-keys path is a file (not a directory).
	_, err := LoadTrustedKeys(true)
	if err == nil {
		t.Fatal("expected error from LoadTrustedKeys when system trusted-keys path is a file, got nil")
	}
}

// TestIsKeyTrustedSystemDirExistsViaInjectable covers the sysExists=true path
// in IsKeyTrusted (trust.go:176-178) when the system trusted-keys directory exists.
func TestIsKeyTrustedSystemDirExistsViaInjectable(t *testing.T) {
	// Cannot use t.Parallel() — t.Setenv is not parallel-safe.

	// Create a real directory to serve as the system trusted-keys dir.
	sysRoot := t.TempDir()
	sysTrustedKeysDir := filepath.Join(sysRoot, "trusted-keys")
	if err := os.MkdirAll(sysTrustedKeysDir, 0o700); err != nil {
		t.Fatalf("MkdirAll(sysTrustedKeysDir): %v", err)
	}

	// Point user trusted-keys dir to a non-existent path so userExists=false.
	t.Setenv(EnvTrustedKeysDir, filepath.Join(t.TempDir(), "nonexistent-user-keys"))

	// Override the system config root.
	old := getSystemConfigRootFn
	getSystemConfigRootFn = func() string { return sysRoot }
	t.Cleanup(func() { getSystemConfigRootFn = old })

	// With includeSystem=true, sysExists becomes true. The store exists (sysExists=true),
	// so IsKeyTrusted should return *bool (not nil) with false (key not found).
	result, err := IsKeyTrusted("deadbeef000000000000000000000000deadbeef000000000000000000000000", true)
	if err != nil {
		t.Fatalf("IsKeyTrusted() unexpected error = %v", err)
	}
	if result == nil {
		t.Fatal("expected non-nil result (sysExists=true), got nil")
	}
	if *result {
		t.Error("expected *result=false for unknown fingerprint, got true")
	}
}
