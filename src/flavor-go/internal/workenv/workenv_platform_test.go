package workenv

import (
	"os"
	"path/filepath"
	"testing"
)

func TestGetCacheRootDarwin(t *testing.T) {
	old := currentGOOS
	t.Cleanup(func() { currentGOOS = old })
	currentGOOS = "darwin"

	t.Setenv("FLAVOR_CACHE_DIR", "")
	t.Setenv("HOME", "/Users/testuser")
	got := GetCacheRoot()
	if want := filepath.Join("/Users/testuser", "Library", "Caches", "flavor"); got != want {
		t.Fatalf("GetCacheRoot() darwin = %q, want %q", got, want)
	}
}

func TestGetCacheRootDarwinNoHome(t *testing.T) {
	old := currentGOOS
	t.Cleanup(func() { currentGOOS = old })
	currentGOOS = "darwin"

	t.Setenv("FLAVOR_CACHE_DIR", "")
	t.Setenv("HOME", "")
	got := GetCacheRoot()
	if got == "" {
		t.Fatal("expected non-empty fallback path")
	}
	// should fall through to os.TempDir() fallback
}

func TestGetCacheRootLinuxXDG(t *testing.T) {
	old := currentGOOS
	t.Cleanup(func() { currentGOOS = old })
	currentGOOS = "linux"

	t.Setenv("FLAVOR_CACHE_DIR", "")
	t.Setenv("XDG_CACHE_HOME", "/xdg/cache")
	t.Setenv("HOME", "/home/testuser")
	got := GetCacheRoot()
	if want := "/xdg/cache/flavor"; got != want {
		t.Fatalf("GetCacheRoot() linux XDG = %q, want %q", got, want)
	}
}

func TestGetCacheRootLinuxHome(t *testing.T) {
	old := currentGOOS
	t.Cleanup(func() { currentGOOS = old })
	currentGOOS = "linux"

	t.Setenv("FLAVOR_CACHE_DIR", "")
	t.Setenv("XDG_CACHE_HOME", "")
	t.Setenv("HOME", "/home/testuser")
	got := GetCacheRoot()
	if want := "/home/testuser/.cache/flavor"; got != want {
		t.Fatalf("GetCacheRoot() linux HOME = %q, want %q", got, want)
	}
}

func TestGetCacheRootWindows(t *testing.T) {
	old := currentGOOS
	t.Cleanup(func() { currentGOOS = old })
	currentGOOS = "windows"

	t.Setenv("FLAVOR_CACHE_DIR", "")
	t.Setenv("LOCALAPPDATA", "C:\\Users\\test\\AppData\\Local")
	got := GetCacheRoot()
	if want := filepath.Join("C:\\Users\\test\\AppData\\Local", "flavor", "cache"); got != want {
		t.Fatalf("GetCacheRoot() windows = %q, want %q", got, want)
	}
}

func TestGetCacheRootWindowsNoLocalAppData(t *testing.T) {
	old := currentGOOS
	t.Cleanup(func() { currentGOOS = old })
	currentGOOS = "windows"

	t.Setenv("FLAVOR_CACHE_DIR", "")
	t.Setenv("LOCALAPPDATA", "")
	got := GetCacheRoot()
	// Falls through to os.TempDir() fallback
	if got == "" {
		t.Fatal("expected non-empty fallback")
	}
}

func TestGetConfigRootWindows(t *testing.T) {
	old := currentGOOS
	t.Cleanup(func() { currentGOOS = old })
	currentGOOS = "windows"

	t.Setenv("FLAVOR_CONFIG_DIR", "")
	t.Setenv("XDG_CONFIG_HOME", "")
	t.Setenv("APPDATA", "C:\\Users\\test\\AppData\\Roaming")
	got := GetConfigRoot()
	if want := filepath.Join("C:\\Users\\test\\AppData\\Roaming", "flavor"); got != want {
		t.Fatalf("GetConfigRoot() windows = %q, want %q", got, want)
	}
}

func TestGetConfigRootWindowsNoAppData(t *testing.T) {
	old := currentGOOS
	t.Cleanup(func() { currentGOOS = old })
	currentGOOS = "windows"

	t.Setenv("FLAVOR_CONFIG_DIR", "")
	t.Setenv("XDG_CONFIG_HOME", "")
	t.Setenv("APPDATA", "")
	got := GetConfigRoot()
	if got == "" {
		t.Fatal("expected non-empty fallback")
	}
}

func TestGetSystemConfigRootWindows(t *testing.T) {
	old := currentGOOS
	t.Cleanup(func() { currentGOOS = old })
	currentGOOS = "windows"

	t.Setenv("PROGRAMDATA", "C:\\ProgramData")
	got := GetSystemConfigRoot()
	if want := filepath.Join("C:\\ProgramData", "flavor"); got != want {
		t.Fatalf("GetSystemConfigRoot() windows with PROGRAMDATA = %q, want %q", got, want)
	}
}

func TestGetSystemConfigRootWindowsNoPROGRAMDATA(t *testing.T) {
	old := currentGOOS
	t.Cleanup(func() { currentGOOS = old })
	currentGOOS = "windows"

	t.Setenv("PROGRAMDATA", "")
	got := GetSystemConfigRoot()
	if want := filepath.Join("C:\\ProgramData", "flavor"); got != want {
		t.Fatalf("GetSystemConfigRoot() windows fallback = %q, want %q", got, want)
	}
}

func TestGetSystemConfigRootUnix(t *testing.T) {
	old := currentGOOS
	t.Cleanup(func() { currentGOOS = old })
	currentGOOS = "linux"

	got := GetSystemConfigRoot()
	if got != "/etc/flavor" {
		t.Fatalf("GetSystemConfigRoot() unix = %q, want %q", got, "/etc/flavor")
	}
}

func TestCreateWorkenvSubdirFailure(t *testing.T) {
	tmp := t.TempDir()
	// Create a file where a subdir is expected to cause MkdirAll to fail
	blockingFile := filepath.Join(tmp, "blocked")
	if err := os.WriteFile(blockingFile, []byte("x"), 0o600); err != nil {
		t.Fatalf("WriteFile: %v", err)
	}
	err := CreateWorkenv(tmp, []DirectorySpec{
		{Path: "blocked/child", Mode: 0o755},
	})
	if err == nil {
		t.Fatal("expected error when subdir creation is blocked by a file")
	}
}
