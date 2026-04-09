//go:build !windows
// +build !windows

package format_2025

import (
	"os"
	"path/filepath"
	"testing"

	"github.com/provide-io/flavor/go/flavor/pkg/logging"
)

func TestAtomicReplaceUnix(t *testing.T) {
	t.Parallel()

	dir := t.TempDir()
	source := filepath.Join(dir, "source.bin")
	dest := filepath.Join(dir, "dest.bin")

	if err := os.WriteFile(source, []byte("new"), 0o600); err != nil {
		t.Fatalf("WriteFile(source) error = %v", err)
	}
	if err := os.WriteFile(dest, []byte("old"), 0o600); err != nil {
		t.Fatalf("WriteFile(dest) error = %v", err)
	}

	if err := atomicReplace(source, dest, logging.NewNullLogger()); err != nil {
		t.Fatalf("atomicReplace() error = %v", err)
	}

	got, err := os.ReadFile(dest)
	if err != nil {
		t.Fatalf("ReadFile(dest) error = %v", err)
	}
	if string(got) != "new" {
		t.Fatalf("dest contents = %q, want %q", string(got), "new")
	}
	if _, err := os.Stat(source); !os.IsNotExist(err) {
		t.Fatalf("expected source to be removed, err=%v", err)
	}
}
