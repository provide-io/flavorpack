package format_2025

import (
	"bytes"
	"os"
	"path/filepath"
	"runtime"
	"testing"

	"github.com/provide-io/flavor/go/flavor/pkg/logging"
	"log/slog"
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
	// Windows does not support Unix-style permission bits; skip mode check.
	if runtime.GOOS != "windows" {
		if info.Mode().Perm() != 0o740 {
			t.Fatalf("expected copied mode 0740, got %o", info.Mode().Perm())
		}
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
	logger := logging.NewBufferLogger(&logs, slog.LevelDebug)
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
	logger := logging.NewNullLogger()

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

func TestCopyHelpersReturnErrorsForMissingInputs(t *testing.T) {
	t.Parallel()

	root := t.TempDir()
	missingFile := filepath.Join(root, "missing.txt")
	destFile := filepath.Join(root, "dest.txt")
	if err := copyFile(missingFile, destFile); err == nil {
		t.Fatal("expected copyFile() to fail for missing source")
	}

	missingDir := filepath.Join(root, "missing-dir")
	destDir := filepath.Join(root, "dest-dir")
	if err := copyDirAll(missingDir, destDir); err == nil {
		t.Fatal("expected copyDirAll() to fail for missing source directory")
	}
}

func TestFixShebangsSkipsMissingBinDir(t *testing.T) {
	t.Parallel()

	logger := logging.NewNullLogger()
	if err := fixShebangs(filepath.Join(t.TempDir(), "missing-bin"), "/old", "/new", logger); err != nil {
		t.Fatalf("fixShebangs() error = %v", err)
	}
}

func TestFixShebangsSkipsSubdirectories(t *testing.T) {
	t.Parallel()

	binDir := t.TempDir()
	// Create a subdirectory inside binDir — covers the entry.IsDir() continue branch.
	if err := os.Mkdir(filepath.Join(binDir, "subdir"), 0o755); err != nil {
		t.Fatalf("Mkdir() error = %v", err)
	}
	logger := logging.NewNullLogger()
	if err := fixShebangs(binDir, "/old", "/new", logger); err != nil {
		t.Fatalf("fixShebangs() error = %v", err)
	}
}

func TestCopyHelpersRejectBadDestinationTargets(t *testing.T) {
	t.Parallel()

	root := t.TempDir()
	srcFile := filepath.Join(root, "source.txt")
	if err := os.WriteFile(srcFile, []byte("payload"), 0o640); err != nil {
		t.Fatalf("failed to write source file: %v", err)
	}

	destDir := filepath.Join(root, "dest-dir")
	if err := os.MkdirAll(destDir, 0o755); err != nil {
		t.Fatalf("failed to create destination dir: %v", err)
	}
	if err := copyFile(srcFile, destDir); err == nil {
		t.Fatal("expected copyFile() to fail when destination is a directory")
	}

	srcDir := filepath.Join(root, "source-dir")
	mustMkdirAllPSP(t, srcDir)
	if err := os.WriteFile(filepath.Join(srcDir, "nested.txt"), []byte("nested"), 0o644); err != nil {
		t.Fatalf("failed to write source tree: %v", err)
	}
	blockingFile := filepath.Join(root, "blocking-file")
	if err := os.WriteFile(blockingFile, []byte("occupied"), 0o644); err != nil {
		t.Fatalf("failed to write blocking file: %v", err)
	}
	if err := copyDirAll(srcDir, filepath.Join(blockingFile, "child")); err == nil {
		t.Fatal("expected copyDirAll() to fail when destination parent is a file")
	}
}
