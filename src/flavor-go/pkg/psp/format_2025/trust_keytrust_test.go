package format_2025

import (
	"os"
	"path/filepath"
	"testing"

	"github.com/hashicorp/go-hclog"
)

// TestRunBundleWithCwdIsKeyTrustedError covers lines 182-184 in execution.go:
// when IsKeyTrusted returns an error (trusted-keys path is a file, not a dir),
// runBundleWithCwd logs a warning and continues.
func TestRunBundleWithCwdIsKeyTrustedError(t *testing.T) {
	cacheRoot := t.TempDir()
	t.Setenv(EnvCacheDir, cacheRoot)
	t.Setenv(EnvValidation, "none")
	t.Setenv(EnvWorkenvCache, "false")

	// Build a bundle with a non-zero public key (uses buildBundleWithFakeSignature).
	bundle := buildBundleWithFakeSignature(t)

	// Make the trusted-keys dir path point to a regular file so IsKeyTrusted fails.
	f, err := os.CreateTemp(t.TempDir(), "trusted-keys-file-*.txt")
	if err != nil {
		t.Fatalf("CreateTemp: %v", err)
	}
	_ = f.Close()
	t.Setenv(EnvTrustedKeysDir, f.Name())

	logger := hclog.NewNullLogger()
	// IsKeyTrusted error is a warning — runBundleWithCwd should continue.
	cmd, err := runBundleWithCwd(bundle, nil, t.TempDir(), logger)
	if err != nil {
		t.Fatalf("runBundleWithCwd() unexpected error = %v", err)
	}
	if cmd == nil {
		t.Fatal("expected non-nil exec.Cmd")
	}
}

// TestRunBundleWithCwdUntrustedKeyWarning covers lines 188-193 in execution.go:
// when IsKeyTrusted returns *false (key exists but not trusted), a security
// warning is printed to stderr and runBundleWithCwd continues.
func TestRunBundleWithCwdUntrustedKeyWarning(t *testing.T) {
	cacheRoot := t.TempDir()
	t.Setenv(EnvCacheDir, cacheRoot)
	t.Setenv(EnvValidation, "none")
	t.Setenv(EnvWorkenvCache, "false")

	// Build a bundle with a non-zero public key.
	bundle := buildBundleWithFakeSignature(t)

	// Create an empty trusted-keys dir (exists, so IsKeyTrusted returns *false for unknown key).
	trustedDir := t.TempDir()
	t.Setenv(EnvTrustedKeysDir, trustedDir)

	logger := hclog.NewNullLogger()
	// The key is not in the trusted store — warning is printed but execution continues.
	cmd, err := runBundleWithCwd(bundle, nil, t.TempDir(), logger)
	if err != nil {
		t.Fatalf("runBundleWithCwd() unexpected error = %v", err)
	}
	if cmd == nil {
		t.Fatal("expected non-nil exec.Cmd")
	}
}

// TestEnforcePolicyUseOsKeychain covers line 374-376 in execution_policy.go:
// when policy.UseOsKeychain is true, EnforcePolicy returns an error.
func TestEnforcePolicyUseOsKeychain(t *testing.T) {
	t.Parallel()

	eff := EffectivePolicy{
		UseOsKeychain: true,
	}
	err := EnforcePolicy(eff, 0, false, false)
	if err == nil {
		t.Fatal("expected error for UseOsKeychain=true, got nil")
	}
}

// TestLoadTrustedKeysSystemDirErrorCoverage covers lines 156-158 in trust.go:
// when the system trusted-keys dir path is a file (not a directory),
// LoadTrustedKeys returns an error when includeSystem=true.
// We use PROGRAMDATA on Windows or a mock approach on unix.
// On unix, GetSystemConfigRoot returns /etc/flavor which we cannot override.
// Instead, test via the user dir being a file (which also covers the error path).
func TestLoadTrustedKeysUserDirFileErrorPath(t *testing.T) {
	// Create a file at the path where trusted-keys dir is expected.
	f, err := os.CreateTemp(t.TempDir(), "trusted-keys-file-*.txt")
	if err != nil {
		t.Fatalf("CreateTemp: %v", err)
	}
	_ = f.Close()

	// Point user dir to the file — loadKeysFromDir fails with non-NotExist error.
	t.Setenv(EnvTrustedKeysDir, f.Name())

	// includeSystem=false: should fail at user dir load.
	_, err = LoadTrustedKeys(false)
	if err == nil {
		t.Fatal("expected error when trusted-keys path is a file, got nil")
	}
}

// TestIsKeyTrustedSystemDirExistsAndKeyNotFound covers line 176-178 in trust.go:
// when includeSystem=true and sysExists=true (the system dir check succeeds),
// IsKeyTrusted returns *false when the key is not found.
// Since we can't override /etc/flavor, we test via the user dir path.
// The key insight: if userExists=true (our dir), load keys, key not found → *false.
func TestIsKeyTrustedUserDirExistsKeyNotFound(t *testing.T) {
	// Create an actual directory with no keys.
	userDir := t.TempDir()
	t.Setenv(EnvTrustedKeysDir, userDir)

	// Call with includeSystem=false — userExists=true (dir exists).
	// LoadTrustedKeys will succeed (empty dir), key not found → *false.
	result, err := IsKeyTrusted("nonexistent-fingerprint-0000000000000000000000000000000000000000", false)
	if err != nil {
		t.Fatalf("IsKeyTrusted() unexpected error = %v", err)
	}
	if result == nil {
		t.Fatal("expected non-nil result (user dir exists), got nil")
	}
	if *result {
		t.Error("expected *result=false for nonexistent fingerprint, got true")
	}
}

// TestRunBundleWithCwdTrustedKeyFound covers lines 186-187 in execution.go:
// when IsKeyTrusted returns *true (key is trusted), keyTrusted is set to true.
// We generate a real Ed25519 key, patch it into the bundle, and add it to the trusted-keys dir.
func TestRunBundleWithCwdTrustedKeyFound(t *testing.T) {
	cacheRoot := t.TempDir()
	t.Setenv(EnvCacheDir, cacheRoot)
	t.Setenv(EnvValidation, "none")
	t.Setenv(EnvWorkenvCache, "false")

	// Generate a real Ed25519 key and get its PEM.
	rawPub, pemBlock := generateTestKeyPEM(t)

	// Build a bundle and patch the public key field with our generated key.
	bundle := buildSingleSlotBundleForTests(t, []byte("data"), []byte("data"), nil, SlotMetadata{
		ID:     "trusted-key-slot",
		Target: "{workenv}",
	}, 0, false)
	patchBundleIndexBytes(t, bundle, func(idxBytes []byte) {
		copy(idxBytes[64:96], rawPub[:32])
	})

	// Install the corresponding public key in the trusted-keys dir.
	trustedDir := t.TempDir()
	t.Setenv(EnvTrustedKeysDir, trustedDir)
	if err := os.WriteFile(trustedDir+"/test.pub", pemBlock, 0o600); err != nil {
		t.Fatalf("WriteFile(trusted): %v", err)
	}

	logger := hclog.NewNullLogger()
	// Key is trusted — runBundleWithCwd should set keyTrusted=true and continue.
	cmd, err := runBundleWithCwd(bundle, nil, t.TempDir(), logger)
	if err != nil {
		t.Fatalf("runBundleWithCwd() unexpected error = %v", err)
	}
	if cmd == nil {
		t.Fatal("expected non-nil exec.Cmd")
	}
}

// TestIsKeyTrustedFound covers the *trusted=true path in IsKeyTrusted.
func TestIsKeyTrustedFound(t *testing.T) {
	userDir := t.TempDir()
	t.Setenv(EnvTrustedKeysDir, userDir)

	// Generate a key and write it to the trusted-keys dir.
	_, pemBlock := generateTestKeyPEM(t)
	keyFile := filepath.Join(userDir, "key.pub")
	if err := os.WriteFile(keyFile, pemBlock, 0o600); err != nil {
		t.Fatalf("WriteFile: %v", err)
	}

	// Load the key to get its fingerprint.
	tk, err := loadKeyFromFile(keyFile)
	if err != nil {
		t.Fatalf("loadKeyFromFile: %v", err)
	}

	result, err := IsKeyTrusted(tk.Fingerprint, false)
	if err != nil {
		t.Fatalf("IsKeyTrusted() error = %v", err)
	}
	if result == nil {
		t.Fatal("expected non-nil result, got nil")
	}
	if !*result {
		t.Error("expected *result=true for trusted key, got false")
	}
}
