// Package workenv manages work environments for package execution
package workenv

import (
	"crypto/sha256"
	"encoding/hex"
	"fmt"
	"os"
	"path/filepath"
	"runtime"

	"github.com/provide-io/flavor/go/flavor/pkg/envvars"
)

// GetWorkenvPath returns the workenv path for a package
func GetWorkenvPath(packageName, version, checksum string) string {
	// Use checksum for uniqueness if available
	var identifier string
	if checksum != "" {
		// Use first 8 chars of checksum
		if len(checksum) >= 8 {
			identifier = checksum[:8]
		} else {
			identifier = checksum
		}
	} else {
		// Fall back to hash of name+version
		h := sha256.New()
		h.Write([]byte(packageName + "-" + version))
		hash := hex.EncodeToString(h.Sum(nil))
		identifier = hash[:8]
	}

	return filepath.Join(GetCacheRoot(), identifier)
}

// GetCacheRoot returns the root cache directory
func GetCacheRoot() string {
	// Check environment variable first
	if cacheDir := os.Getenv(envvars.EnvCacheDir); cacheDir != "" {
		return cacheDir
	}

	// Use platform-specific defaults
	switch runtime.GOOS {
	case "darwin":
		if home := os.Getenv("HOME"); home != "" {
			return filepath.Join(home, "Library", "Caches", "flavor")
		}
	case "linux", "freebsd":
		if xdgCache := os.Getenv("XDG_CACHE_HOME"); xdgCache != "" {
			return filepath.Join(xdgCache, "flavor")
		}
		if home := os.Getenv("HOME"); home != "" {
			return filepath.Join(home, ".cache", "flavor")
		}
	case "windows":
		if localAppData := os.Getenv("LOCALAPPDATA"); localAppData != "" {
			return filepath.Join(localAppData, "flavor", "cache")
		}
	}

	// Fallback to temp directory
	return filepath.Join(os.TempDir(), "flavor", "cache")
}

// GetConfigRoot returns the user-level config root directory.
// Priority: FLAVOR_CONFIG_DIR env → XDG_CONFIG_HOME/flavor → ~/.config/flavor
// (Windows: %APPDATA%\flavor if no XDG_CONFIG_HOME)
func GetConfigRoot() string {
	if configDir := os.Getenv(envvars.EnvConfigDir); configDir != "" {
		return configDir
	}
	if xdgConfig := os.Getenv("XDG_CONFIG_HOME"); xdgConfig != "" {
		return filepath.Join(xdgConfig, "flavor")
	}
	switch runtime.GOOS {
	case "windows":
		if appData := os.Getenv("APPDATA"); appData != "" {
			return filepath.Join(appData, "flavor")
		}
	default:
		if home := os.Getenv("HOME"); home != "" {
			return filepath.Join(home, ".config", "flavor")
		}
	}
	return filepath.Join(os.TempDir(), "flavor", "config")
}

// GetSystemConfigRoot returns the system-wide config root directory.
// Linux/macOS: /etc/flavor
// Windows:     %PROGRAMDATA%\flavor
func GetSystemConfigRoot() string {
	if runtime.GOOS == "windows" {
		if programData := os.Getenv("PROGRAMDATA"); programData != "" {
			return filepath.Join(programData, "flavor")
		}
		return filepath.Join("C:\\ProgramData", "flavor")
	}
	return "/etc/flavor"
}

// CreateWorkenv creates a workenv directory with proper structure
func CreateWorkenv(path string, dirs []DirectorySpec) error {
	// Create main workenv directory
	if err := os.MkdirAll(path, 0755); err != nil {
		return fmt.Errorf("failed to create workenv: %w", err)
	}

	// Create subdirectories
	for _, dir := range dirs {
		dirPath := filepath.Join(path, dir.Path)
		mode := dir.Mode
		if mode == 0 {
			mode = 0755
		}

		if err := os.MkdirAll(dirPath, os.FileMode(mode)); err != nil {
			return fmt.Errorf("failed to create directory %s: %w", dir.Path, err)
		}
	}

	return nil
}

// DirectorySpec specifies a directory to create
type DirectorySpec struct {
	Path string
	Mode uint32
}
