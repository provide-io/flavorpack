package format_2025

import (
	"fmt"
	"math"
	"os"
	"path/filepath"
	"strconv"
	"strings"
)

func buildTimestampToInt64(buildTimestamp uint64) (int64, error) {
	ts, err := strconv.ParseInt(strconv.FormatUint(buildTimestamp, 10), 10, 64)
	if err != nil {
		return 0, fmt.Errorf("build timestamp %d overflows int64: %w", buildTimestamp, err)
	}
	return ts, nil
}

func modeFromJSONNumber(modeFloat float64) (os.FileMode, error) {
	if math.IsNaN(modeFloat) || math.IsInf(modeFloat, 0) {
		return 0, fmt.Errorf("invalid file mode %v", modeFloat)
	}
	if modeFloat < 0 || math.Trunc(modeFloat) != modeFloat {
		return 0, fmt.Errorf("file mode must be a non-negative integer, got %v", modeFloat)
	}
	mode, err := strconv.ParseUint(strconv.FormatFloat(modeFloat, 'f', 0, 64), 10, 32)
	if err != nil {
		return 0, fmt.Errorf("invalid file mode %v: %w", modeFloat, err)
	}
	return os.FileMode(mode), nil
}

func safeJoinWithinBase(base string, parts ...string) (string, error) {
	cleanBase := filepath.Clean(base)
	joined := filepath.Join(append([]string{cleanBase}, parts...)...)
	cleanJoined := filepath.Clean(joined)
	rel, err := filepath.Rel(cleanBase, cleanJoined)
	if err != nil {
		return "", err
	}
	if rel == "." {
		return cleanJoined, nil
	}
	if rel == ".." || strings.HasPrefix(rel, ".."+string(os.PathSeparator)) {
		return "", fmt.Errorf("path %q escapes base %q", cleanJoined, cleanBase)
	}
	return cleanJoined, nil
}

func resolveWorkenvTarget(workenvDir, rawPath string) (string, error) {
	cleanBase := filepath.Clean(workenvDir)
	candidate := strings.ReplaceAll(rawPath, "{workenv}", cleanBase)
	if !filepath.IsAbs(candidate) {
		candidate = filepath.Join(cleanBase, candidate)
	}
	cleanCandidate := filepath.Clean(candidate)
	rel, err := filepath.Rel(cleanBase, cleanCandidate)
	if err != nil {
		return "", err
	}
	if rel == "." || (rel != ".." && !strings.HasPrefix(rel, ".."+string(os.PathSeparator))) {
		return cleanCandidate, nil
	}
	return "", fmt.Errorf("path %q escapes work environment %q", rawPath, cleanBase)
}
