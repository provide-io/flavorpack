package workenv

import (
	"crypto/sha256"
	"encoding/hex"
	"os"
	"path/filepath"
	"runtime"
	"testing"

	"github.com/provide-io/flavor/go/flavor/pkg/envvars"
)

func TestGetWorkenvPath(t *testing.T) {
	t.Setenv(envvars.EnvCacheDir, "/tmp/flavor-cache")

	if got, want := GetWorkenvPath("demo", "1.0.0", "abcdef123456"), filepath.Join("/tmp/flavor-cache", "abcdef12"); got != want {
		t.Fatalf("GetWorkenvPath checksum prefix mismatch: got %q want %q", got, want)
	}

	if got, want := GetWorkenvPath("demo", "1.0.0", "abc"), filepath.Join("/tmp/flavor-cache", "abc"); got != want {
		t.Fatalf("GetWorkenvPath short checksum mismatch: got %q want %q", got, want)
	}

	hash := sha256.Sum256([]byte("demo-1.0.0"))
	want := filepath.Join("/tmp/flavor-cache", hex.EncodeToString(hash[:])[:8])
	if got := GetWorkenvPath("demo", "1.0.0", ""); got != want {
		t.Fatalf("GetWorkenvPath hash fallback mismatch: got %q want %q", got, want)
	}
}

func TestGetCacheRoot(t *testing.T) {
	t.Setenv(envvars.EnvCacheDir, "/tmp/flavor-cache")
	t.Setenv("XDG_CACHE_HOME", "/tmp/xdg-cache")
	t.Setenv("HOME", "/tmp/home")

	if got, want := GetCacheRoot(), "/tmp/flavor-cache"; got != want {
		t.Fatalf("GetCacheRoot env override mismatch: got %q want %q", got, want)
	}

	t.Setenv(envvars.EnvCacheDir, "")
	if runtime.GOOS == "linux" {
		if got, want := GetCacheRoot(), filepath.Join("/tmp/xdg-cache", "flavor"); got != want {
			t.Fatalf("GetCacheRoot xdg mismatch: got %q want %q", got, want)
		}
	} else if runtime.GOOS == "windows" {
		// On Windows, LOCALAPPDATA may be set; clear it to test fallback to TempDir.
		t.Setenv("LOCALAPPDATA", "")
		if got, want := GetCacheRoot(), filepath.Join(os.TempDir(), "flavor", "cache"); got != want {
			t.Fatalf("GetCacheRoot windows fallback mismatch: got %q want %q", got, want)
		}
	} else {
		if got, want := GetCacheRoot(), filepath.Join("/tmp/home", "Library", "Caches", "flavor"); got != want {
			t.Fatalf("GetCacheRoot home mismatch: got %q want %q", got, want)
		}
	}

	t.Setenv("XDG_CACHE_HOME", "")
	if runtime.GOOS == "linux" {
		if got, want := GetCacheRoot(), filepath.Join("/tmp/home", ".cache", "flavor"); got != want {
			t.Fatalf("GetCacheRoot home mismatch: got %q want %q", got, want)
		}
	} else if runtime.GOOS == "windows" {
		// LOCALAPPDATA already cleared above; fallback is TempDir.
		if got, want := GetCacheRoot(), filepath.Join(os.TempDir(), "flavor", "cache"); got != want {
			t.Fatalf("GetCacheRoot windows fallback mismatch: got %q want %q", got, want)
		}
	} else {
		if got, want := GetCacheRoot(), filepath.Join("/tmp/home", "Library", "Caches", "flavor"); got != want {
			t.Fatalf("GetCacheRoot home mismatch: got %q want %q", got, want)
		}
	}

	t.Setenv("HOME", "")
	if got, want := GetCacheRoot(), filepath.Join(os.TempDir(), "flavor", "cache"); got != want {
		t.Fatalf("GetCacheRoot temp fallback mismatch: got %q want %q", got, want)
	}
}

func TestGetConfigAndSystemRoots(t *testing.T) {
	t.Setenv(envvars.EnvConfigDir, "/tmp/flavor-config")
	t.Setenv("XDG_CONFIG_HOME", "/tmp/xdg-config")
	t.Setenv("HOME", "/tmp/home")

	if got, want := GetConfigRoot(), "/tmp/flavor-config"; got != want {
		t.Fatalf("GetConfigRoot env override mismatch: got %q want %q", got, want)
	}

	t.Setenv(envvars.EnvConfigDir, "")
	if got, want := GetConfigRoot(), filepath.Join("/tmp/xdg-config", "flavor"); got != want {
		t.Fatalf("GetConfigRoot xdg mismatch: got %q want %q", got, want)
	}

	t.Setenv("XDG_CONFIG_HOME", "")
	if runtime.GOOS == "windows" {
		t.Setenv("APPDATA", "/tmp/appdata")
		if got, want := GetConfigRoot(), filepath.Join("/tmp/appdata", "flavor"); got != want {
			t.Fatalf("GetConfigRoot appdata mismatch: got %q want %q", got, want)
		}
	} else {
		if got, want := GetConfigRoot(), filepath.Join("/tmp/home", ".config", "flavor"); got != want {
			t.Fatalf("GetConfigRoot home mismatch: got %q want %q", got, want)
		}
	}

	t.Setenv("HOME", "")
	t.Setenv("APPDATA", "")
	if got, want := GetConfigRoot(), filepath.Join(os.TempDir(), "flavor", "config"); got != want {
		t.Fatalf("GetConfigRoot temp fallback mismatch: got %q want %q", got, want)
	}

	if runtime.GOOS == "windows" {
		t.Setenv("PROGRAMDATA", "/tmp/programdata")
		if got, want := GetSystemConfigRoot(), filepath.Join("/tmp/programdata", "flavor"); got != want {
			t.Fatalf("GetSystemConfigRoot programdata mismatch: got %q want %q", got, want)
		}
	} else {
		if got, want := GetSystemConfigRoot(), "/etc/flavor"; got != want {
			t.Fatalf("GetSystemConfigRoot mismatch: got %q want %q", got, want)
		}
	}
}

func TestCreateWorkenv(t *testing.T) {
	dir := t.TempDir()

	err := CreateWorkenv(dir, []DirectorySpec{
		{Path: "bin"},
		{Path: filepath.Join("nested", "secure"), Mode: 0o700},
	})
	if err != nil {
		t.Fatalf("CreateWorkenv: %v", err)
	}

	for _, subdir := range []string{"bin", filepath.Join("nested", "secure")} {
		info, err := os.Stat(filepath.Join(dir, subdir))
		if err != nil {
			t.Fatalf("stat %s: %v", subdir, err)
		}
		if !info.IsDir() {
			t.Fatalf("expected %s to be a directory", subdir)
		}
	}
}
