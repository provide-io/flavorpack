package format_2025

import (
	"os"
	"path/filepath"
	"strconv"
	"testing"
	"time"

	"github.com/hashicorp/go-hclog"
)

func TestLockLifecycleAndCleanup(t *testing.T) {
	logger := hclog.NewNullLogger()
	paths := NewWorkenvPaths(t.TempDir(), "/tmp/demo.pspf")

	t.Run("acquire release and stale lock handling", func(t *testing.T) {
		if acquired, err := TryAcquireLock(paths, logger); err != nil {
			t.Fatalf("TryAcquireLock() error = %v", err)
		} else if !acquired {
			t.Fatal("expected lock acquisition to succeed")
		}
		if !IsLockAcquired() {
			t.Fatal("expected lock state to be acquired")
		}
		if _, err := os.Stat(paths.LockFile()); err != nil {
			t.Fatalf("expected lock file to exist: %v", err)
		}
		ReleaseLock(paths, logger)
		if IsLockAcquired() {
			t.Fatal("expected lock state to be released")
		}
		if _, err := os.Stat(paths.LockFile()); !os.IsNotExist(err) {
			t.Fatalf("expected lock file to be removed, got err=%v", err)
		}

		if err := os.MkdirAll(filepath.Dir(paths.LockFile()), 0o700); err != nil {
			t.Fatalf("MkdirAll(lock dir) error = %v", err)
		}
		stalePID := 99999999
		if err := os.WriteFile(paths.LockFile(), []byte(strconv.Itoa(stalePID)), 0o600); err != nil {
			t.Fatalf("WriteFile(stale lock) error = %v", err)
		}
		if acquired, err := TryAcquireLock(paths, logger); err != nil {
			t.Fatalf("TryAcquireLock() stale error = %v", err)
		} else if !acquired {
			t.Fatal("expected stale lock to be replaced")
		}
		ReleaseLock(paths, logger)

		if err := os.MkdirAll(filepath.Dir(paths.LockFile()), 0o700); err != nil {
			t.Fatalf("MkdirAll(active lock dir) error = %v", err)
		}
		if err := os.WriteFile(paths.LockFile(), []byte(strconv.Itoa(os.Getpid())), 0o600); err != nil {
			t.Fatalf("WriteFile(active lock) error = %v", err)
		}
		if acquired, err := TryAcquireLock(paths, logger); err != nil {
			t.Fatalf("TryAcquireLock() active error = %v", err)
		} else if acquired {
			t.Fatal("expected active-process lock to be rejected")
		}
		_ = os.Remove(paths.LockFile())
	})

	t.Run("wait for extraction", func(t *testing.T) {
		if err := os.MkdirAll(filepath.Dir(paths.LockFile()), 0o700); err != nil {
			t.Fatalf("MkdirAll(wait lock dir) error = %v", err)
		}
		if err := os.WriteFile(paths.LockFile(), []byte("12345"), 0o600); err != nil {
			t.Fatalf("WriteFile(wait lock) error = %v", err)
		}

		go func() {
			time.Sleep(50 * time.Millisecond)
			_ = os.Remove(paths.LockFile())
		}()

		if err := WaitForExtraction(paths, 1, logger); err != nil {
			t.Fatalf("WaitForExtraction() error = %v", err)
		}

		if err := os.WriteFile(paths.LockFile(), []byte("12345"), 0o600); err != nil {
			t.Fatalf("WriteFile(timeout lock) error = %v", err)
		}
		if err := WaitForExtraction(paths, 0, logger); err == nil {
			t.Fatal("expected timeout from WaitForExtraction")
		}
		_ = os.Remove(paths.LockFile())
	})

	t.Run("extraction markers and stale cleanup", func(t *testing.T) {
		if err := MarkExtractionComplete(paths, logger); err != nil {
			t.Fatalf("MarkExtractionComplete() error = %v", err)
		}
		if !IsExtractionComplete(paths) {
			t.Fatal("expected extraction completion marker")
		}

		MarkExtractionIncomplete(paths, logger)
		if IsExtractionComplete(paths) {
			t.Fatal("expected extraction completion marker to be removed")
		}

		staleDir := filepath.Join(paths.Tmp(), "99999999")
		if err := os.MkdirAll(staleDir, 0o700); err != nil {
			t.Fatalf("MkdirAll(staleDir) error = %v", err)
		}
		if err := CleanupStaleExtractions(paths, logger); err != nil {
			t.Fatalf("CleanupStaleExtractions() error = %v", err)
		}
		if _, err := os.Stat(staleDir); !os.IsNotExist(err) {
			t.Fatalf("expected stale extraction dir to be removed, got err=%v", err)
		}
	})
}
