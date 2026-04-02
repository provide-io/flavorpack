package main

import (
	"errors"
	"runtime/debug"
	"strings"
	"testing"
	"time"
)

// TestGetBuilderTimestampExecutableFails covers the time.Now() fallback path
// (main.go:46) in getBuilderTimestamp when os.Executable returns an error.
func TestGetBuilderTimestampExecutableFails(t *testing.T) {
	t.Parallel()

	old := osExecutableFn
	t.Cleanup(func() { osExecutableFn = old })
	osExecutableFn = func() (string, error) {
		return "", errors.New("executable path unavailable")
	}

	before := time.Now()
	ts := getBuilderTimestamp()
	after := time.Now()

	if ts == "" {
		t.Fatal("expected non-empty timestamp from time.Now() fallback, got empty string")
	}

	// Verify it's a parseable RFC3339 timestamp.
	parsed, err := time.Parse(time.RFC3339, ts)
	if err != nil {
		t.Fatalf("getBuilderTimestamp() returned non-RFC3339 value %q: %v", ts, err)
	}

	// Verify the timestamp is in the plausible range.
	if parsed.Before(before.Add(-time.Second)) || parsed.After(after.Add(time.Second)) {
		t.Fatalf("timestamp %q out of expected range [%v, %v]", ts, before, after)
	}

	_ = strings.Contains(ts, "T") // just ensure it looks like an RFC3339 value
}

// TestGetBuilderTimestampVcsTime covers main.go:36-39 (vcs.time branch).
// We inject readBuildInfoFn to return a fake BuildInfo with a vcs.time setting.
func TestGetBuilderTimestampVcsTime(t *testing.T) {
	t.Parallel()

	fakeTime := "2024-01-15T12:00:00Z"
	old := readBuildInfoFn
	t.Cleanup(func() { readBuildInfoFn = old })
	readBuildInfoFn = func() (*debug.BuildInfo, bool) {
		return &debug.BuildInfo{
			Settings: []debug.BuildSetting{
				{Key: "vcs.time", Value: fakeTime},
			},
		}, true
	}

	ts := getBuilderTimestamp()
	if ts != fakeTime {
		t.Fatalf("expected vcs.time %q, got %q", fakeTime, ts)
	}
}

// TestGetBuilderTimestampVcsTimeParseFails covers the path where vcs.time exists
// but is not valid RFC3339 (falls through to the binary mtime / time.Now() path).
func TestGetBuilderTimestampVcsTimeInvalid(t *testing.T) {
	t.Parallel()

	old := readBuildInfoFn
	t.Cleanup(func() { readBuildInfoFn = old })
	readBuildInfoFn = func() (*debug.BuildInfo, bool) {
		return &debug.BuildInfo{
			Settings: []debug.BuildSetting{
				{Key: "vcs.time", Value: "not-a-timestamp"},
			},
		}, true
	}

	// Should fall through to time.Now() fallback (since osExecutableFn may or may not succeed).
	ts := getBuilderTimestamp()
	if ts == "" {
		t.Fatal("expected non-empty timestamp even when vcs.time is invalid")
	}
	if _, err := time.Parse(time.RFC3339, ts); err != nil {
		t.Fatalf("expected RFC3339 timestamp, got %q: %v", ts, err)
	}
}
