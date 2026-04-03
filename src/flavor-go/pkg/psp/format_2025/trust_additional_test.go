//
// SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
// SPDX-License-Identifier: Apache-2.0
//

package format_2025

import (
	"os"
	"path/filepath"
	"testing"
)

// TestLoadKeysFromDirReadDirError covers the non-NotExist error path in loadKeysFromDir.
// We create a file at the path where a directory is expected — ReadDir will fail
// with an error that is NOT os.ErrNotExist.
func TestLoadKeysFromDirReadDirError(t *testing.T) {
	t.Parallel()

	// Create a file (not a directory) at the path that will be passed to loadKeysFromDir.
	f, err := os.CreateTemp(t.TempDir(), "not-a-dir-*.txt")
	if err != nil {
		t.Fatalf("CreateTemp: %v", err)
	}
	_ = f.Close()

	// Try to read it as a directory — os.ReadDir on a file returns a non-NotExist error.
	keys := make(map[string]TrustedKey)
	found, err := loadKeysFromDir(f.Name(), keys)
	if err == nil {
		t.Fatal("expected error when ReadDir is called on a file, got nil")
	}
	if !found {
		t.Fatal("expected found=true for non-NotExist ReadDir error")
	}
	_ = found
}

// TestLoadTrustedKeysErrorPropagation covers the error-return path in LoadTrustedKeys.
// We create a file at the trusted-keys path so loadKeysFromDir fails (ReadDir on a file).
func TestLoadTrustedKeysErrorPropagation(t *testing.T) {
	// NOTE: t.Parallel() is intentionally omitted — t.Setenv cannot be used with Parallel.

	// Create a regular file at the path that would normally be the trusted-keys dir.
	f, err := os.CreateTemp(t.TempDir(), "trusted-keys-file-*.txt")
	if err != nil {
		t.Fatalf("CreateTemp: %v", err)
	}
	_ = f.Close()

	// Point FLAVOR_TRUSTED_KEYS_DIR to the file — LoadTrustedKeys will call
	// loadKeysFromDir on a file, which fails with a non-NotExist error.
	t.Setenv(EnvTrustedKeysDir, f.Name())

	_, err = LoadTrustedKeys(false)
	if err == nil {
		t.Fatal("expected error from LoadTrustedKeys when trusted-keys path is a file, got nil")
	}
}

// TestIsKeyTrustedWithSystemDirPresent covers the path where includeSystem=true and
// the user trusted-keys directory exists, so userExists=true. The system dir
// (/etc/flavor/trusted-keys on Linux) typically doesn't exist in test environment.
func TestIsKeyTrustedWithSystemDirPresent(t *testing.T) {
	// NOTE: t.Parallel() is intentionally omitted — t.Setenv cannot be used with Parallel.
	// Create an actual directory for the user trusted-keys dir.
	userDir := t.TempDir()
	t.Setenv(EnvTrustedKeysDir, userDir)

	// Write a key to the user dir so the store is meaningful.
	_, pemBlock := generateTestKeyPEM(t)
	if err := os.WriteFile(filepath.Join(userDir, "key.pub"), pemBlock, 0o600); err != nil {
		t.Fatalf("WriteFile: %v", err)
	}

	// includeSystem=true with a user dir that exists — covers the sysExists branch
	// regardless of whether /etc/flavor/trusted-keys exists.
	result, err := IsKeyTrusted("deadbeef000000000000000000000000deadbeef000000000000000000000000", true)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	// The fingerprint is not in the store — result should be non-nil (false), not nil.
	if result == nil {
		t.Fatal("expected non-nil result (store exists), got nil")
	}
	if *result {
		t.Error("expected false (key not in store), got true")
	}
}

// TestLoadKeysFromDirSkipsSubdirectory covers the `entry.IsDir()` continue branch.
func TestLoadKeysFromDirSkipsSubdirectory(t *testing.T) {
	t.Parallel()

	dir := t.TempDir()
	// Create a subdirectory inside the trusted-keys dir.
	subdir := filepath.Join(dir, "subdir.pub")
	if err := os.MkdirAll(subdir, 0o700); err != nil {
		t.Fatalf("MkdirAll: %v", err)
	}

	// Write a valid .pub file to ensure the key loop runs.
	_, pemBlock := generateTestKeyPEM(t)
	if err := os.WriteFile(filepath.Join(dir, "valid.pub"), pemBlock, 0o600); err != nil {
		t.Fatalf("WriteFile: %v", err)
	}

	keys := make(map[string]TrustedKey)
	found, err := loadKeysFromDir(dir, keys)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if !found {
		t.Fatal("expected found=true")
	}
	// The subdir.pub directory entry should be skipped (IsDir=true, so no keys loaded from it).
	// The valid.pub file should be loaded.
	if len(keys) != 1 {
		t.Errorf("expected 1 key (subdir skipped), got %d", len(keys))
	}
}

// TestLoadKeyFromFileComputeFingerprintEdge exercises loadKeyFromFile with a valid
// Ed25519 key where ComputeKeyFingerprint would succeed. This is already covered by
// TestLoadTrustedKeys_ValidKey, but we add a direct test without the Name comment line
// to exercise the extractNameFromPEM empty-result path.
func TestLoadKeyFromFileNoNameComment(t *testing.T) {
	t.Parallel()

	_, pemBlock := generateTestKeyPEM(t)
	// Write PEM without any "# Name:" comment.
	f := filepath.Join(t.TempDir(), "noname.pub")
	if err := os.WriteFile(f, pemBlock, 0o600); err != nil {
		t.Fatalf("WriteFile: %v", err)
	}

	tk, err := loadKeyFromFile(f)
	if err != nil {
		t.Fatalf("loadKeyFromFile() error = %v", err)
	}
	if tk.Name != "" {
		t.Errorf("expected empty name for key without Name comment, got %q", tk.Name)
	}
	if tk.Fingerprint == "" {
		t.Error("expected non-empty fingerprint")
	}
}

// TestIsKeyTrustedUserDirErrorPropagation covers the LoadTrustedKeys error propagation
// path inside IsKeyTrusted — when the user dir exists but loadKeysFromDir fails.
func TestIsKeyTrustedUserDirErrorPropagation(t *testing.T) {
	// NOTE: t.Parallel() intentionally omitted — t.Setenv cannot be used with Parallel.
	// Create a file at the path where trusted-keys dir is expected (not a directory).
	f, err := os.CreateTemp(t.TempDir(), "trusted-keys-as-file-*.txt")
	if err != nil {
		t.Fatalf("CreateTemp: %v", err)
	}
	_ = f.Close()

	// Set FLAVOR_TRUSTED_KEYS_DIR to the file path.
	// os.Stat(userDir) will succeed (file exists), so userExists=true.
	// Then LoadTrustedKeys → loadKeysFromDir will fail (ReadDir on a file).
	t.Setenv(EnvTrustedKeysDir, f.Name())

	result, err := IsKeyTrusted("anyfingerprint", false)
	if err == nil {
		t.Fatal("expected error when trusted-keys path is a file, got nil")
	}
	if result != nil {
		t.Error("expected nil result on error")
	}
}
