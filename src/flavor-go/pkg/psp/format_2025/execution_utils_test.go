package format_2025

import (
	"bytes"
	"os"
	"path/filepath"
	"testing"

	"github.com/hashicorp/go-hclog"
)

func TestCopyFilePreservesContentAndMode(t *testing.T) {
	root := t.TempDir()
	src := filepath.Join(root, "source.txt")
	dst := filepath.Join(root, "dest.txt")

	if err := os.WriteFile(src, []byte("hello"), 0o740); err != nil {
		t.Fatalf("failed to write source file: %v", err)
	}

	if err := copyFile(src, dst); err != nil {
		t.Fatalf("copyFile returned error: %v", err)
	}

	data, err := os.ReadFile(dst)
	if err != nil {
		t.Fatalf("failed to read copied file: %v", err)
	}
	if string(data) != "hello" {
		t.Fatalf("unexpected copied content %q", string(data))
	}

	info, err := os.Stat(dst)
	if err != nil {
		t.Fatalf("failed to stat copied file: %v", err)
	}
	if info.Mode().Perm() != 0o740 {
		t.Fatalf("expected copied mode 0740, got %o", info.Mode().Perm())
	}
}

func TestCopyDirAllRecursivelyCopiesTree(t *testing.T) {
	root := t.TempDir()
	src := filepath.Join(root, "src")
	dst := filepath.Join(root, "dst")
	mustMkdirAllPSP(t, filepath.Join(src, "nested"))
	if err := os.WriteFile(filepath.Join(src, "nested", "file.txt"), []byte("payload"), 0o644); err != nil {
		t.Fatalf("failed to write source tree: %v", err)
	}

	if err := copyDirAll(src, dst); err != nil {
		t.Fatalf("copyDirAll returned error: %v", err)
	}

	data, err := os.ReadFile(filepath.Join(dst, "nested", "file.txt"))
	if err != nil {
		t.Fatalf("failed to read copied tree: %v", err)
	}
	if string(data) != "payload" {
		t.Fatalf("unexpected copied tree content %q", string(data))
	}
}

func TestFixShebangsRewritesMatchingScriptsOnly(t *testing.T) {
	root := t.TempDir()
	binDir := filepath.Join(root, "bin")
	mustMkdirAllPSP(t, binDir)

	script := filepath.Join(binDir, "tool")
	plain := filepath.Join(binDir, "README")
	if err := os.WriteFile(script, []byte("#!/old/prefix/python\nprint('ok')\n"), 0o755); err != nil {
		t.Fatalf("failed to write script: %v", err)
	}
	if err := os.WriteFile(plain, []byte("plain file\n"), 0o644); err != nil {
		t.Fatalf("failed to write plain file: %v", err)
	}

	var logs bytes.Buffer
	logger := hclog.New(&hclog.LoggerOptions{Name: "test", Level: hclog.Debug, Output: &logs})
	if err := fixShebangs(binDir, "/old/prefix", "/new/prefix", logger); err != nil {
		t.Fatalf("fixShebangs returned error: %v", err)
	}

	updated, err := os.ReadFile(script)
	if err != nil {
		t.Fatalf("failed to read updated script: %v", err)
	}
	if !bytes.Contains(updated, []byte("#!/new/prefix/python")) {
		t.Fatalf("expected shebang rewrite, got %q", string(updated))
	}

	plainData, err := os.ReadFile(plain)
	if err != nil {
		t.Fatalf("failed to read plain file: %v", err)
	}
	if string(plainData) != "plain file\n" {
		t.Fatalf("plain file should not be modified, got %q", string(plainData))
	}
}

func TestCleanupLifecycleSlotsRemovesInitSlots(t *testing.T) {
	workenvDir := t.TempDir()
	initPath := filepath.Join(workenvDir, "init-slot")
	keepPath := filepath.Join(workenvDir, "app-slot")
	mustMkdirAllPSP(t, initPath)
	mustMkdirAllPSP(t, keepPath)

	metadata := &Metadata{
		Slots: []SlotMetadata{
			{Slot: 0, ID: "init-slot", Lifecycle: "init"},
			{Slot: 1, ID: "app-slot", Lifecycle: "runtime"},
		},
	}
	slotPaths := map[int]string{
		0: initPath,
		1: keepPath,
	}
	logger := hclog.NewNullLogger()

	cleanupLifecycleSlots(workenvDir, metadata, slotPaths, logger)

	if _, err := os.Stat(initPath); !os.IsNotExist(err) {
		t.Fatalf("expected init lifecycle path to be removed, got err=%v", err)
	}
	if _, ok := slotPaths[0]; ok {
		t.Fatalf("expected init slot to be removed from slot paths")
	}
	if _, err := os.Stat(keepPath); err != nil {
		t.Fatalf("expected runtime lifecycle path to remain: %v", err)
	}
	if _, ok := slotPaths[1]; !ok {
		t.Fatalf("expected runtime slot to remain in slot paths")
	}
}
