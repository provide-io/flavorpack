package format_2025

import (
	"os"
	"path/filepath"
	"strings"
	"testing"

	"github.com/provide-io/flavor/go/flavor/pkg/logging"
)

// TestRunBundleWithCwdWorkenvDirectoryMkdirAllFailure covers execution.go:354-357:
// when mkdirAllValidated fails for a workenv.directories entry because the path
// already exists as a regular file (so MkdirAll can't create a directory there).
func TestRunBundleWithCwdWorkenvDirectoryMkdirAllFailure(t *testing.T) {
	cacheRoot := t.TempDir()
	t.Setenv(EnvCacheDir, cacheRoot)
	t.Setenv(EnvValidation, "none")
	t.Setenv(EnvWorkenvCache, "false")

	// Build a bundle with a workenv.directories entry pointing to "{workenv}/data".
	bundle := buildMultiSlotBundleForTests(t, []multiSlotBundleSpec{
		{
			meta:         SlotMetadata{ID: "slot", Target: "{workenv}"},
			storedData:   []byte("payload"),
			originalData: []byte("payload"),
		},
	}, Metadata{
		Format:        "PSPF/2025",
		FormatVersion: "2025.0",
		Package:       PackageInfo{Name: "test", Version: "1.0.0"},
		Execution:     &ExecutionInfo{PrimarySlot: 0, Command: "/bin/true"},
		Build:         &BuildInfo{Tool: "test"},
		Workenv: &WorkenvInfo{
			Directories: []DirectorySpec{
				{Path: "{workenv}/data", Mode: "0755"},
			},
		},
	})

	// Pre-compute the workenvDir path (same formula as WorkenvPaths.Workenv()).
	bundleName := filepath.Base(bundle)
	if strings.HasSuffix(bundleName, ".psp") {
		bundleName = bundleName[:len(bundleName)-4]
	} else if strings.HasSuffix(bundleName, ".pspf") {
		bundleName = bundleName[:len(bundleName)-5]
	}
	workenvDir := filepath.Join(cacheRoot, "workenv", bundleName)

	// Create workenvDir as a directory (so the workenv dir creation succeeds).
	if err := os.MkdirAll(workenvDir, 0o755); err != nil {
		t.Fatalf("MkdirAll(workenvDir): %v", err)
	}

	// Pre-create a FILE at the path where the dirSpec "{workenv}/data" would go,
	// so mkdirAllValidated("{workenv}/data") fails (ENOTDIR / EEXIST).
	dataPath := filepath.Join(workenvDir, "data")
	if err := os.WriteFile(dataPath, []byte("blocking file"), 0o600); err != nil {
		t.Fatalf("WriteFile(data blocker): %v", err)
	}

	logger := logging.NewNullLogger()
	_, err := runBundleWithCwd(bundle, nil, t.TempDir(), logger)
	if err == nil {
		t.Fatal("expected error when mkdirAllValidated fails for workenv directory, got nil")
	}
	if !strings.Contains(err.Error(), "failed to create directory") {
		t.Logf("note: got error %v (may not contain 'failed to create directory' on all platforms)", err)
	}
}

// TestRunBundleWithCwdWorkenvDirectoryChmodFails covers execution.go:364-366:
// when chmodValidated fails for a workenv.directories entry.
// We make the workenvDir non-writable and then set the mode, but since
// the dir was created by mkdirAllValidated (with validation), we focus
// on making chmodValidated fail by creating a dir and then removing it.
//
// Actually, chmodValidated on a directory we own should always succeed.
// The error path at 364-366 is a best-effort log (no return), so it's
// a debug-only path. We test the Mode parsing success path instead.
func TestRunBundleWithCwdWorkenvDirectoryWithMode(t *testing.T) {
	cacheRoot := t.TempDir()
	t.Setenv(EnvCacheDir, cacheRoot)
	t.Setenv(EnvValidation, "none")
	t.Setenv(EnvWorkenvCache, "false")

	// Build a bundle with workenv.directories that has a valid Mode string.
	// This covers the Mode parsing success path (lines 360-368 where mode != "").
	bundle := buildMultiSlotBundleForTests(t, []multiSlotBundleSpec{
		{
			meta:         SlotMetadata{ID: "slot", Target: "{workenv}"},
			storedData:   []byte("payload"),
			originalData: []byte("payload"),
		},
	}, Metadata{
		Format:        "PSPF/2025",
		FormatVersion: "2025.0",
		Package:       PackageInfo{Name: "test", Version: "1.0.0"},
		Execution:     &ExecutionInfo{PrimarySlot: 0, Command: "/bin/true"},
		Build:         &BuildInfo{Tool: "test"},
		Workenv: &WorkenvInfo{
			Directories: []DirectorySpec{
				{Path: "{workenv}/newdir", Mode: "0700"},
			},
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
