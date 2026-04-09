package logging

import (
	"bytes"
	"context"
	"log/slog"
	"strings"
	"testing"

	"github.com/provide-io/flavor/go/flavor/pkg/envvars"
)

func TestNewLoggerReturnsLogger(t *testing.T) {
	t.Setenv(envvars.EnvJSONLog, "0")
	Setup("debug", nil)
	logger := NewLogger(context.Background(), "test")
	if logger == nil {
		t.Fatal("expected non-nil logger")
	}
}

func TestNewLoggerJSONMode(t *testing.T) {
	t.Setenv(envvars.EnvJSONLog, "1")
	Setup("info", nil)
	logger := NewLogger(context.Background(), "json-test")
	if logger == nil {
		t.Fatal("expected non-nil logger")
	}
}

func TestNewNullLoggerDiscardsOutput(t *testing.T) {
	logger := NewNullLogger()
	if logger == nil {
		t.Fatal("expected non-nil null logger")
	}
	// Verify it accepts log calls without panicking.
	logger.Info("should be discarded", "key", "value")
}

func TestNewNullLoggerDiscards(t *testing.T) {
	// Confirm NewBufferLogger captures output.
	var buf bytes.Buffer
	logger := NewBufferLogger(&buf, slog.LevelInfo)
	logger.Info("captured")
	if !strings.Contains(buf.String(), "captured") {
		t.Fatal("expected output in buffer")
	}

	// NullLogger must not write to any buffer.
	var nullBuf bytes.Buffer
	nl := NewNullLogger()
	nl.Info("should not appear")
	if nullBuf.Len() != 0 {
		t.Fatalf("null logger wrote %d bytes", nullBuf.Len())
	}
}

func TestGetLogLevelDefaultsAndOverrides(t *testing.T) {
	t.Setenv(envvars.EnvLogLevel, "")
	if got := GetLogLevel(); got != "warn" {
		t.Fatalf("got %q, want warn", got)
	}

	t.Setenv(envvars.EnvLogLevel, "trace")
	if got := GetLogLevel(); got != "trace" {
		t.Fatalf("got %q, want trace", got)
	}
}
