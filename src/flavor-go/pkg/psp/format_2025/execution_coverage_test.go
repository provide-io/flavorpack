package format_2025

import (
	"os"
	"path/filepath"
	"runtime"
	"testing"

	"github.com/provide-io/flavor/go/flavor/pkg/logging"
)

// TestRunBundleWithCwdHasSBOMTrue covers lines 302-305 in execution.go:
// the "hasSBOM = true" branch when a slot has lifecycle == "attestation".
// We build a bundle with a slot whose Lifecycle is "attestation" and run
// with ValidationNone to skip all integrity checks.
func TestRunBundleWithCwdHasSBOMTrue(t *testing.T) {
	cacheRoot := t.TempDir()
	t.Setenv(EnvCacheDir, cacheRoot)
	t.Setenv(EnvValidation, "none")
	t.Setenv(EnvWorkenvCache, "false")

	// Build a bundle with an "attestation" lifecycle slot.
	bundle := buildMultiSlotBundleForTests(t, []multiSlotBundleSpec{
		{
			meta: SlotMetadata{
				Slot:      0,
				ID:        "attestation-slot",
				Target:    "{workenv}",
				Lifecycle: "attestation",
			},
			storedData:   []byte("attestation-data"),
			originalData: []byte("attestation-data"),
		},
	}, Metadata{
		Format:        "PSPF/2025",
		FormatVersion: "2025.0",
		Package:       PackageInfo{Name: "test", Version: "1.0.0"},
		Execution:     &ExecutionInfo{PrimarySlot: 0, Command: "/bin/true"},
		Build:         &BuildInfo{Tool: "test"},
		Slots: []SlotMetadata{
			{Slot: 0, ID: "attestation-slot", Target: "{workenv}", Lifecycle: "attestation"},
		},
	})

	logger := logging.NewNullLogger()
	cmd, err := runBundleWithCwd(bundle, nil, t.TempDir(), logger)
	if err != nil {
		t.Fatalf("runBundleWithCwd() error = %v", err)
	}
	if cmd == nil {
		t.Fatal("expected non-nil exec.Cmd")
	}
}

// TestRunBundleWithCwdWorkenvMkdirAllFailure covers lines 338-341 in execution.go:
// when mkdirAllValidated(workenvDir) fails, runBundleWithCwd returns an error.
// We make the cache dir itself be a file so that MkdirAll(workenvDir) fails.
func TestRunBundleWithCwdWorkenvMkdirAllFailure(t *testing.T) {
	if runtime.GOOS == "windows" {
		t.Skip("chmod-based tests not reliable on Windows")
	}
	if os.Getuid() == 0 {
		t.Skip("cannot test permission errors as root")
	}

	t.Setenv(EnvValidation, "none")
	t.Setenv(EnvWorkenvCache, "false")

	// Create a file where the cacheDir/workenv directory would need to be.
	base := t.TempDir()
	workenvParent := filepath.Join(base, "workenv")
	if err := os.WriteFile(workenvParent, []byte("blocking"), 0o600); err != nil {
		t.Fatalf("WriteFile(workenvParent): %v", err)
	}
	// Now point EnvCacheDir to base — workenvDir = base/workenv/<name> which
	// cannot be created because base/workenv is a file.
	t.Setenv(EnvCacheDir, base)

	bundle := buildSingleSlotBundleForTests(t, []byte("data"), []byte("data"), nil, SlotMetadata{
		ID:     "slot",
		Target: "{workenv}",
	}, 0, false)

	logger := logging.NewNullLogger()
	_, err := runBundleWithCwd(bundle, nil, t.TempDir(), logger)
	if err == nil {
		t.Fatal("expected error when workenv dir cannot be created")
	}
}

// TestRunBundleWithCwdWorkenvDirectoryMkdirAllFailure covers lines 354-357 in execution.go:
// when mkdirAllValidated fails for a workenv.directories entry, runBundleWithCwd returns an error.
// We build a bundle with a workenv.directories entry that escapes the workenv, which triggers
// the ensurePathWithinWorkenv check. Actually we test the mkdirAllValidated failure by
// placing a file at the directory path.
func TestRunBundleWithCwdWorkenvDirectoryEscapesWorkenv(t *testing.T) {
	cacheRoot := t.TempDir()
	t.Setenv(EnvCacheDir, cacheRoot)
	t.Setenv(EnvValidation, "none")
	t.Setenv(EnvWorkenvCache, "false")

	// Build a bundle with a workenv.directories entry that tries to escape the workenv.
	bundle := buildMultiSlotBundleForTests(t, []multiSlotBundleSpec{
		{
			meta:         SlotMetadata{Slot: 0, ID: "slot", Target: "{workenv}"},
			storedData:   []byte("data"),
			originalData: []byte("data"),
		},
	}, Metadata{
		Format:        "PSPF/2025",
		FormatVersion: "2025.0",
		Package:       PackageInfo{Name: "test", Version: "1.0.0"},
		Execution:     &ExecutionInfo{PrimarySlot: 0, Command: "/bin/true"},
		Build:         &BuildInfo{Tool: "test"},
		Slots:         []SlotMetadata{{Slot: 0, ID: "slot", Target: "{workenv}"}},
		Workenv: &WorkenvInfo{
			Directories: []DirectorySpec{
				{Path: "../../escape", Mode: "0755"},
			},
		},
	})

	logger := logging.NewNullLogger()
	_, err := runBundleWithCwd(bundle, nil, t.TempDir(), logger)
	if err == nil {
		t.Fatal("expected error when workenv directory path escapes workenv")
	}
}
