package format_2025

import (
	"bytes"
	"os"
	"path/filepath"
	"runtime"
	"testing"

	"github.com/hashicorp/go-hclog"
)

// TestFixShebangsSingleLineNoNewline covers the len(lines) <= 1 false branch
// (a script that starts with "#!" and matches oldPrefix but has no trailing newline).
func TestFixShebangsSingleLineNoNewline(t *testing.T) {
	if runtime.GOOS == "windows" {
		t.Skip("chmod-based unreadable files are not reliably testable on Windows")
	}
	t.Parallel()

	binDir := t.TempDir()
	script := filepath.Join(binDir, "single")

	// Write a shebang-only script with no trailing newline – len(lines) after SplitN == 1.
	if err := os.WriteFile(script, []byte("#!/old/prefix/python"), 0o755); err != nil {
		t.Fatalf("WriteFile: %v", err)
	}

	var logs bytes.Buffer
	logger := hclog.New(&hclog.LoggerOptions{Name: "test", Level: hclog.Debug, Output: &logs})
	if err := fixShebangs(binDir, "/old/prefix", "/new/prefix", logger); err != nil {
		t.Fatalf("fixShebangs() error = %v", err)
	}

	updated, err := os.ReadFile(script)
	if err != nil {
		t.Fatalf("ReadFile: %v", err)
	}
	if !bytes.Contains(updated, []byte("#!/new/prefix/python")) {
		t.Fatalf("expected shebang rewrite in single-line file, got %q", string(updated))
	}
}

// TestFixShebangsWriteFileFailure covers the WriteFile error path (line 132).
// We make the script file read-only so os.WriteFile returns an error.
func TestFixShebangsWriteFileFailure(t *testing.T) {
	if runtime.GOOS == "windows" {
		t.Skip("chmod-based unreadable files are not reliably testable on Windows")
	}

	binDir := t.TempDir()
	script := filepath.Join(binDir, "roScript")

	// Write a valid shebang script first (readable + writable).
	if err := os.WriteFile(script, []byte("#!/old/prefix/python\nprint('ok')\n"), 0o755); err != nil {
		t.Fatalf("WriteFile: %v", err)
	}

	// Make the script read-only so WriteFile in fixShebangs will fail.
	if err := os.Chmod(script, 0o444); err != nil {
		t.Fatalf("Chmod: %v", err)
	}
	t.Cleanup(func() { _ = os.Chmod(script, 0o644) })

	var logs bytes.Buffer
	logger := hclog.New(&hclog.LoggerOptions{Name: "test", Level: hclog.Debug, Output: &logs})

	// fixShebangs should not return an error even if WriteFile fails – it only logs.
	if err := fixShebangs(binDir, "/old/prefix", "/new/prefix", logger); err != nil {
		t.Fatalf("fixShebangs() should not propagate WriteFile error, got: %v", err)
	}

	// The log output should contain the "Failed to fix shebang" message.
	if !bytes.Contains(logs.Bytes(), []byte("Failed to fix shebang")) {
		t.Fatalf("expected 'Failed to fix shebang' in logs, got: %s", logs.String())
	}
}
