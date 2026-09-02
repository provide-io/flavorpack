package format_2025

import (
	"log/slog"
	"os"
	"testing"

	"github.com/provide-io/flavor/go/flavor/pkg/logging"
)

// A launch that could not take the extraction lock must not release it.
//
// ReleaseLock removes the lock file unconditionally -- it takes no owner and
// checks none -- so releasing a lock this process never held deletes whichever
// process's lock is there at the time. Two launches of the same package then
// extract into one work environment concurrently.
//
// The window is real: WaitForExtraction returns as soon as the lock file
// disappears, and another process can take the lock between that moment and
// this one returning.
func TestLockIsNotReleasedByAProcessThatNeverAcquiredIt(t *testing.T) {
	cacheRoot := t.TempDir()
	t.Setenv(EnvCacheDir, cacheRoot)
	t.Setenv(EnvWorkenvCache, "false")
	t.Setenv(EnvValidation, "none")

	bundle := buildMultiSlotBundleForTests(t, []multiSlotBundleSpec{
		{
			meta:       SlotMetadata{ID: "main", Target: "{workenv}"},
			storedData: []byte("hello"),
		},
	}, Metadata{
		Execution: &ExecutionInfo{Command: "/bin/true"},
		Build:     &BuildInfo{Tool: "test"},
	})

	// This process never gets the lock.
	oldAcquire := tryAcquireLockFn
	t.Cleanup(func() { tryAcquireLockFn = oldAcquire })
	tryAcquireLockFn = func(_ *WorkenvPaths, _ *slog.Logger) (bool, error) {
		return false, nil
	}

	// The holder finishes, so waiting succeeds.
	oldWait := waitForExtractionFn
	t.Cleanup(func() { waitForExtractionFn = oldWait })
	var lockPath string
	waitForExtractionFn = func(paths *WorkenvPaths, _ int, _ *slog.Logger) error {
		// Stand in for the next process taking the lock the instant the
		// previous holder drops it.
		lockPath = paths.LockFile()
		if err := os.MkdirAll(paths.Extract(), 0o755); err != nil {
			t.Fatalf("MkdirAll(extract): %v", err)
		}
		if err := os.WriteFile(lockPath, []byte("4242\n"), 0o600); err != nil {
			t.Fatalf("WriteFile(lock): %v", err)
		}
		return nil
	}

	// The work environment another process produced checks out.
	oldRecheck := checkWorkenvValidityAfterWaitFn
	t.Cleanup(func() { checkWorkenvValidityAfterWaitFn = oldRecheck })
	checkWorkenvValidityAfterWaitFn = func(_ *WorkenvPaths, _ *PSPFIndex, _ *Metadata, _ *slog.Logger) (bool, error) {
		return true, nil
	}

	logger := logging.NewNullLogger()
	if _, err := runBundleWithCwd(bundle, nil, t.TempDir(), logger); err != nil {
		t.Fatalf("runBundleWithCwd() error = %v", err)
	}

	if lockPath == "" {
		t.Fatal("test did not reach the wait path; the lock was never contended")
	}
	if _, err := os.Stat(lockPath); os.IsNotExist(err) {
		t.Fatal("the other process's extraction lock was removed by a launch that never acquired it")
	}
}
