package format_2025

import (
	"fmt"
	"math"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
)

func uint64ToInt64Checked(value uint64, field string) (int64, error) {
	if value > math.MaxInt64 {
		return 0, fmt.Errorf("%s overflows int64: %d", field, value)
	}
	return int64(value), nil
}

func int64ToUint32Checked(value int64, field string) (uint32, error) {
	if value < 0 || value > math.MaxUint32 {
		return 0, fmt.Errorf("%s out of uint32 range: %d", field, value)
	}
	return uint32(value), nil
}

func intToUint64Checked(value int, field string) (uint64, error) {
	if value < 0 {
		return 0, fmt.Errorf("%s must be non-negative: %d", field, value)
	}
	return uint64(value), nil
}

func float64ToFileModeChecked(value float64, field string) (os.FileMode, error) {
	if math.IsNaN(value) || math.IsInf(value, 0) {
		return 0, fmt.Errorf("%s must be a finite integer, got %v", field, value)
	}
	if value < 0 || value > math.MaxUint32 || math.Trunc(value) != value {
		return 0, fmt.Errorf("%s out of uint32 range: %v", field, value)
	}
	return os.FileMode(uint32(value)), nil
}

func sanitizeHeaderMode(value int64, fallback os.FileMode) os.FileMode {
	mode, err := int64ToUint32Checked(value, "tar header mode")
	if err != nil {
		return fallback
	}
	return os.FileMode(mode)
}

func ensurePathUnderBase(base, candidate string) (string, error) {
	cleanBase := filepath.Clean(base)
	cleanCandidate := filepath.Clean(candidate)
	if !strings.HasPrefix(cleanCandidate, cleanBase+string(os.PathSeparator)) && cleanCandidate != cleanBase {
		return "", fmt.Errorf("path %q escapes base %q", candidate, base)
	}
	return cleanCandidate, nil
}

func joinUnderBase(base, relative string) (string, error) {
	return ensurePathUnderBase(base, filepath.Join(base, relative))
}

func removePath(path string) error {
	// #nosec G304,G703 -- callers pass validated workenv paths
	err := os.Remove(path)
	if err != nil && !os.IsNotExist(err) {
		return err
	}
	return nil
}

func removeAllPath(path string) error {
	// #nosec G304,G703 -- callers pass validated workenv paths
	err := os.RemoveAll(path)
	if err != nil && !os.IsNotExist(err) {
		return err
	}
	return nil
}

func mkdirAllValidated(path string, perm os.FileMode) error {
	// #nosec G301,G302,G304,G703 -- callers validate or derive paths from workenv roots
	return os.MkdirAll(path, perm)
}

func openFileValidated(path string, flag int, perm os.FileMode) (*os.File, error) {
	// #nosec G304,G703 -- callers validate or derive paths from workenv roots
	return os.OpenFile(path, flag, perm)
}

func statValidated(path string) (os.FileInfo, error) {
	// #nosec G304,G703 -- callers validate or derive paths from workenv roots
	return os.Stat(path)
}

func readFileValidated(path string) ([]byte, error) {
	// #nosec G304,G703 -- callers validate or derive paths from workenv roots
	return os.ReadFile(path)
}

func writeFileValidated(path string, data []byte, perm os.FileMode) error {
	// #nosec G304,G306,G703 -- callers validate or derive paths from workenv roots
	return os.WriteFile(path, data, perm)
}

func chmodValidated(path string, perm os.FileMode) error {
	// #nosec G304,G302,G703 -- callers validate or derive paths from workenv roots
	return os.Chmod(path, perm)
}

func execCommandValidated(name string, arg ...string) *exec.Cmd {
	// #nosec G204,G702 -- package-defined commands are intentionally executed directly without a shell
	return exec.Command(name, arg...)
}
