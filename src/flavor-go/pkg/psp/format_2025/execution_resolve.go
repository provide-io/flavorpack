package format_2025

import (
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"runtime"
	"strings"

	"github.com/hashicorp/go-hclog"
)

// resolveExecutable resolves an executable path for cross-platform compatibility
//
// On Unix systems, it handles absolute paths like /usr/bin/python3 by extracting
// the basename and looking it up in PATH.
//
// On Windows, it additionally provides fallbacks for common Unix command names:
// - python3 -> python.exe
// - sh -> bash.exe
//
// This ensures that packages with Unix-style command paths work on Windows.
func resolveExecutable(executable string, logger hclog.Logger) string {
	// Extract basename from Unix absolute paths
	// /usr/bin/python3 -> python3
	execName := executable
	if strings.HasPrefix(executable, "/") {
		execName = filepath.Base(executable)
		logger.Debug("🔍 Extracted basename from Unix path", "original", executable, "basename", execName)
	}

	// Try to resolve via PATH using exec.LookPath
	if resolved, err := exec.LookPath(execName); err == nil {
		logger.Debug("✅ Resolved executable via PATH", "input", executable, "resolved", resolved)
		return resolved
	}

	// On Windows, try common Unix command fallbacks
	if runtime.GOOS == "windows" {
		var fallback string
		switch execName {
		case "python3", "python3.exe":
			// Try python.exe as fallback
			fallback = "python.exe"
		case "sh", "sh.exe":
			// Try bash.exe as fallback
			fallback = "bash.exe"
		}

		if fallback != "" {
			if resolved, err := exec.LookPath(fallback); err == nil {
				logger.Debug("✅ Resolved executable via Windows fallback",
					"input", executable,
					"fallback", fallback,
					"resolved", resolved)
				return resolved
			}
		}
	}

	// If we can't resolve, return the basename (not the full invalid Unix path)
	// This gives the best chance for exec.Command to find it
	if execName != executable {
		logger.Debug("⚠️ Could not resolve executable, using basename",
			"input", executable,
			"basename", execName)
		return execName
	}

	logger.Debug("⚠️ Could not resolve executable in PATH, using as-is", "executable", executable)
	return executable
}

// lookPathInEnv searches for a binary in the PATH extracted from the given environment
// slice. This is used to resolve a binary name to an absolute path using a custom
// environment (e.g., cmd.Env that includes workenv/bin) rather than the current
// process environment that exec.LookPath uses.
func lookPathInEnv(file string, env []string) (string, error) {
	pathVal := ""
	for _, e := range env {
		if strings.HasPrefix(e, "PATH=") {
			pathVal = strings.TrimPrefix(e, "PATH=")
			break
		}
	}
	if pathVal == "" {
		return "", fmt.Errorf("PATH not found in environment")
	}

	for _, dir := range filepath.SplitList(pathVal) {
		if dir == "" {
			dir = "."
		}
		candidate := filepath.Join(dir, file)
		if fi, err := os.Stat(candidate); err == nil && !fi.IsDir() {
			return candidate, nil
		}
	}
	return "", fmt.Errorf("executable %q not found in PATH", file)
}
