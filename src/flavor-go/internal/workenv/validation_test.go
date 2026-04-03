package workenv

import (
	"encoding/json"
	"os"
	"path/filepath"
	"testing"
	"time"
)

func writeCompleteMarker(t *testing.T, dir string, marker ValidationMarker) {
	t.Helper()

	data, err := json.Marshal(marker)
	if err != nil {
		t.Fatalf("marshal marker: %v", err)
	}

	if err := os.WriteFile(filepath.Join(dir, ".extraction.complete"), data, 0o600); err != nil {
		t.Fatalf("write marker: %v", err)
	}
}

func prepareValidWorkenv(t *testing.T) string {
	t.Helper()

	dir := t.TempDir()
	for _, subdir := range []string{"bin", "lib"} {
		if err := os.Mkdir(filepath.Join(dir, subdir), 0o755); err != nil {
			t.Fatalf("mkdir %s: %v", subdir, err)
		}
	}

	writeCompleteMarker(t, dir, ValidationMarker{
		Timestamp:   time.Now(),
		PackageName: "flavorpack",
		Version:     "1.0.0",
		Checksum:    "abc123",
	})

	return dir
}

func TestIsValid(t *testing.T) {
	t.Run("valid marker and directories", func(t *testing.T) {
		dir := prepareValidWorkenv(t)

		if !IsValid(dir, "flavorpack", "1.0.0", "abc123") {
			t.Fatal("expected workenv to be valid")
		}
	})

	t.Run("rejects checksum mismatch", func(t *testing.T) {
		dir := prepareValidWorkenv(t)

		if IsValid(dir, "flavorpack", "1.0.0", "wrong") {
			t.Fatal("expected checksum mismatch to invalidate workenv")
		}
	})

	t.Run("rejects stale marker", func(t *testing.T) {
		dir := t.TempDir()
		for _, subdir := range []string{"bin", "lib"} {
			if err := os.Mkdir(filepath.Join(dir, subdir), 0o755); err != nil {
				t.Fatalf("mkdir %s: %v", subdir, err)
			}
		}

		writeCompleteMarker(t, dir, ValidationMarker{
			Timestamp:   time.Now().Add(-31 * 24 * time.Hour),
			PackageName: "flavorpack",
			Version:     "1.0.0",
			Checksum:    "abc123",
		})

		if IsValid(dir, "flavorpack", "1.0.0", "abc123") {
			t.Fatal("expected stale workenv to be invalid")
		}
	})

	t.Run("rejects malformed marker", func(t *testing.T) {
		dir := t.TempDir()
		for _, subdir := range []string{"bin", "lib"} {
			if err := os.Mkdir(filepath.Join(dir, subdir), 0o755); err != nil {
				t.Fatalf("mkdir %s: %v", subdir, err)
			}
		}
		if err := os.WriteFile(filepath.Join(dir, ".extraction.complete"), []byte("{"), 0o600); err != nil {
			t.Fatalf("write malformed marker: %v", err)
		}

		if IsValid(dir, "flavorpack", "1.0.0", "abc123") {
			t.Fatal("expected malformed marker to invalidate workenv")
		}
	})

	t.Run("rejects name mismatch", func(t *testing.T) {
		dir := prepareValidWorkenv(t)
		if IsValid(dir, "other-name", "1.0.0", "abc123") {
			t.Fatal("expected name mismatch to invalidate workenv")
		}
	})

	t.Run("rejects file where directory expected", func(t *testing.T) {
		dir := t.TempDir()
		// Write "bin" as a FILE instead of a directory.
		if err := os.WriteFile(filepath.Join(dir, "bin"), []byte("not a dir"), 0o600); err != nil {
			t.Fatalf("WriteFile(bin) error = %v", err)
		}
		if err := os.Mkdir(filepath.Join(dir, "lib"), 0o755); err != nil {
			t.Fatalf("Mkdir(lib) error = %v", err)
		}
		writeCompleteMarker(t, dir, ValidationMarker{
			Timestamp:   time.Now(),
			PackageName: "flavorpack",
			Version:     "1.0.0",
			Checksum:    "abc123",
		})
		if IsValid(dir, "flavorpack", "1.0.0", "abc123") {
			t.Fatal("expected file-as-directory to invalidate workenv")
		}
	})

	t.Run("rejects missing directory", func(t *testing.T) {
		dir := t.TempDir()
		writeCompleteMarker(t, dir, ValidationMarker{
			Timestamp:   time.Now(),
			PackageName: "flavorpack",
			Version:     "1.0.0",
			Checksum:    "abc123",
		})

		if IsValid(dir, "flavorpack", "1.0.0", "abc123") {
			t.Fatal("expected missing directories to invalidate workenv")
		}
	})
}

func TestMarkCompleteMarkIncompleteAndClean(t *testing.T) {
	dir := t.TempDir()
	for _, subdir := range []string{"bin", "lib"} {
		if err := os.Mkdir(filepath.Join(dir, subdir), 0o755); err != nil {
			t.Fatalf("mkdir %s: %v", subdir, err)
		}
	}

	if err := MarkComplete(dir, "flavorpack", "1.0.0", "abc123"); err != nil {
		t.Fatalf("mark complete: %v", err)
	}

	if !IsValid(dir, "flavorpack", "1.0.0", "abc123") {
		t.Fatal("expected freshly marked workenv to be valid")
	}

	if err := MarkIncomplete(dir, "failed extraction"); err != nil {
		t.Fatalf("mark incomplete: %v", err)
	}

	if _, err := os.Stat(filepath.Join(dir, ".extraction.complete")); !os.IsNotExist(err) {
		t.Fatalf("expected complete marker removed, got err=%v", err)
	}
	if _, err := os.Stat(filepath.Join(dir, ".extraction.incomplete")); err != nil {
		t.Fatalf("expected incomplete marker to exist: %v", err)
	}

	if err := os.WriteFile(filepath.Join(dir, ".extraction.lock"), []byte("locked"), 0o600); err != nil {
		t.Fatalf("write lock: %v", err)
	}
	if err := Clean(dir); err != nil {
		t.Fatalf("clean: %v", err)
	}

	for _, marker := range []string{".extraction.complete", ".extraction.incomplete", ".extraction.lock"} {
		if _, err := os.Stat(filepath.Join(dir, marker)); !os.IsNotExist(err) {
			t.Fatalf("expected %s removed, got err=%v", marker, err)
		}
	}
}
