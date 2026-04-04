package format_2025

import (
	"os"
	"testing"

	"github.com/hashicorp/go-hclog"
)

// TestRunBundleWithCwdMetadataExecutionNil covers lines 282-284:
// when metadata.Execution is nil, the else branch logs a debug warning.
// We build a bundle that has no Execution field in metadata.
func TestRunBundleWithCwdMetadataExecutionNil(t *testing.T) {
	cacheRoot := t.TempDir()
	t.Setenv(EnvCacheDir, cacheRoot)
	t.Setenv(EnvValidation, "none")
	t.Setenv(EnvWorkenvCache, "false")

	// Build a bundle with Execution == nil in metadata.
	metadata := Metadata{
		Format:        "PSPF/2025",
		FormatVersion: "2025.0",
		Package:       PackageInfo{Name: "demo", Version: "1.0.0"},
		Execution:     nil, // No execution config
		Build:         &BuildInfo{Tool: "test"},
	}

	bundle := buildMultiSlotBundleForTests(t, []multiSlotBundleSpec{
		{
			meta:       SlotMetadata{ID: "slot", Target: "{workenv}"},
			storedData: []byte("data"),
		},
	}, metadata)

	logger := hclog.NewNullLogger()
	cmd, err := runBundleWithCwd(bundle, nil, t.TempDir(), logger)
	if err != nil {
		t.Fatalf("runBundleWithCwd() error = %v", err)
	}
	if cmd == nil {
		t.Fatal("expected non-nil exec.Cmd")
	}
}

// TestRunBundleWithCwdLoadOperatorPolicyError covers lines 288-290:
// when LoadOperatorPolicy returns an error, runBundleWithCwd returns that error.
// We inject getSystemPolicyFileImpl to point to a file with invalid JSON.
func TestRunBundleWithCwdLoadOperatorPolicyError(t *testing.T) {
	cacheRoot := t.TempDir()
	t.Setenv(EnvCacheDir, cacheRoot)
	t.Setenv(EnvValidation, "none")
	t.Setenv(EnvWorkenvCache, "false")

	// Create an invalid policy file (invalid JSON).
	policyFile := t.TempDir() + "/policy.json"
	if err := os.WriteFile(policyFile, []byte(`{invalid json`), 0o600); err != nil {
		t.Fatalf("WriteFile(policy): %v", err)
	}

	// Inject the system policy file to point to our invalid file.
	oldSystem := getSystemPolicyFileImpl
	t.Cleanup(func() { getSystemPolicyFileImpl = oldSystem })
	getSystemPolicyFileImpl = func() string { return policyFile }

	bundle := buildSingleSlotBundleForTests(t, []byte("data"), []byte("data"), nil, SlotMetadata{
		ID:     "slot",
		Target: "{workenv}",
	}, 0, false)

	logger := hclog.NewNullLogger()
	_, err := runBundleWithCwd(bundle, nil, t.TempDir(), logger)
	if err == nil {
		t.Fatal("expected error when LoadOperatorPolicy fails due to invalid JSON")
	}
}

// TestRunBundleWithCwdValidationNoneCompletesSuccessfully covers lines 202-205:
// ValidationNone skips all integrity verification and continues.
func TestRunBundleWithCwdValidationNoneCompletesSuccessfully(t *testing.T) {
	cacheRoot := t.TempDir()
	t.Setenv(EnvCacheDir, cacheRoot)
	t.Setenv(EnvValidation, "none")
	t.Setenv(EnvWorkenvCache, "false")

	bundle := buildSingleSlotBundleForTests(t, []byte("data"), []byte("data"), nil, SlotMetadata{
		ID:     "slot",
		Target: "{workenv}",
	}, 0, false)

	logger := hclog.NewNullLogger()
	cmd, err := runBundleWithCwd(bundle, nil, t.TempDir(), logger)
	if err != nil {
		t.Fatalf("runBundleWithCwd() error = %v", err)
	}
	if cmd == nil {
		t.Fatal("expected non-nil exec.Cmd")
	}
}
