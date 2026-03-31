package format_2025

import (
	"bytes"
	"math"
	"os"
	"path/filepath"
	"runtime"
	"testing"
)

func TestUint64ToInt64Checked(t *testing.T) {
	t.Parallel()

	got, err := uint64ToInt64Checked(42, "test field")
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if got != 42 {
		t.Fatalf("got %d, want 42", got)
	}

	if _, err := uint64ToInt64Checked(math.MaxUint64, "test field"); err == nil {
		t.Fatal("expected overflow error")
	}
}

func TestInt64ToUint32Checked(t *testing.T) {
	t.Parallel()

	got, err := int64ToUint32Checked(0o700, "mode")
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if got != 0o700 {
		t.Fatalf("got %o, want 0700", got)
	}

	for _, value := range []int64{-1, math.MaxInt64} {
		if _, err := int64ToUint32Checked(value, "mode"); err == nil {
			t.Fatalf("expected range error for %d", value)
		}
	}
}

func TestIntToUint64Checked(t *testing.T) {
	t.Parallel()

	got, err := intToUint64Checked(42, "slot index")
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if got != 42 {
		t.Fatalf("got %d, want 42", got)
	}

	if _, err := intToUint64Checked(-1, "slot index"); err == nil {
		t.Fatal("expected negative value error")
	}
}

func TestJoinUnderBase(t *testing.T) {
	t.Parallel()

	base := t.TempDir()
	joined, err := joinUnderBase(base, filepath.Join("nested", "file.txt"))
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	want := filepath.Join(base, "nested", "file.txt")
	if joined != want {
		t.Fatalf("got %q, want %q", joined, want)
	}

	if _, err := joinUnderBase(base, filepath.Join("..", "escape")); err == nil {
		t.Fatal("expected path escape error")
	}
}

func TestRemoveHelpersIgnoreMissing(t *testing.T) {
	t.Parallel()

	if err := removePath(filepath.Join(t.TempDir(), "missing")); err != nil {
		t.Fatalf("removePath should ignore missing paths: %v", err)
	}
	if err := removeAllPath(filepath.Join(t.TempDir(), "missing")); err != nil {
		t.Fatalf("removeAllPath should ignore missing paths: %v", err)
	}
}

func TestSanitizeHeaderModeFallsBack(t *testing.T) {
	t.Parallel()

	if got := sanitizeHeaderMode(-1, os.FileMode(FilePerms)); got != os.FileMode(FilePerms) {
		t.Fatalf("got %v, want fallback", got)
	}
	if got := sanitizeHeaderMode(0o755, os.FileMode(FilePerms)); got != 0o755 {
		t.Fatalf("got %v, want 0755", got)
	}
}

func TestValidatedFileHelpers(t *testing.T) {
	t.Parallel()

	dir := t.TempDir()
	path := filepath.Join(dir, "file.txt")
	nestedDir := filepath.Join(dir, "nested", "path")

	if err := mkdirAllValidated(nestedDir, os.FileMode(DirPerms)); err != nil {
		t.Fatalf("mkdirAllValidated() error = %v", err)
	}

	if err := writeFileValidated(path, []byte("payload"), os.FileMode(FilePerms)); err != nil {
		t.Fatalf("writeFileValidated() error = %v", err)
	}

	file, err := openFileValidated(path, os.O_RDONLY, 0)
	if err != nil {
		t.Fatalf("openFileValidated() error = %v", err)
	}
	if err := file.Close(); err != nil {
		t.Fatalf("Close() error = %v", err)
	}

	data, err := readFileValidated(path)
	if err != nil {
		t.Fatalf("readFileValidated() error = %v", err)
	}
	if !bytes.Equal(data, []byte("payload")) {
		t.Fatalf("unexpected file contents %q", string(data))
	}

	info, err := statValidated(path)
	if err != nil {
		t.Fatalf("statValidated() error = %v", err)
	}
	// Windows does not support Unix-style permission bits; skip mode check.
	if runtime.GOOS != "windows" {
		if info.Mode().Perm() != os.FileMode(FilePerms) {
			t.Fatalf("unexpected mode %v", info.Mode().Perm())
		}
	}
	if _, err := os.Stat(nestedDir); err != nil {
		t.Fatalf("expected nested dir to exist: %v", err)
	}
}
