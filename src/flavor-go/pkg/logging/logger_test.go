package logging

import (
	"bytes"
	"strings"
	"testing"
)

func TestNewLoggerUsesPrefixWriterByDefault(t *testing.T) {
	t.Setenv("FLAVOR_JSON_LOG", "0")
	var buf bytes.Buffer

	logger := NewLogger("test", "debug", &buf)
	logger.Info("hello")

	output := buf.String()
	if !strings.Contains(output, "🐹 ") {
		t.Fatalf("expected prefixed output, got %q", output)
	}
	if !strings.Contains(output, "hello") {
		t.Fatalf("expected log message in output, got %q", output)
	}
}

func TestNewLoggerSupportsJSONMode(t *testing.T) {
	t.Setenv("FLAVOR_JSON_LOG", "1")
	var buf bytes.Buffer

	logger := NewLogger("json-test", "info", &buf)
	logger.Info("hello-json")

	output := buf.String()
	if strings.Contains(output, "🐹 ") {
		t.Fatalf("did not expect prefix in JSON mode, got %q", output)
	}
	if !strings.Contains(output, "\"@message\":\"hello-json\"") && !strings.Contains(output, "hello-json") {
		t.Fatalf("expected json log message in output, got %q", output)
	}
}

func TestGetLogLevelDefaultsAndOverrides(t *testing.T) {
	t.Setenv("FLAVOR_LOG_LEVEL", "")
	if got := GetLogLevel(); got != "warn" {
		t.Fatalf("got %q, want warn", got)
	}

	t.Setenv("FLAVOR_LOG_LEVEL", "trace")
	if got := GetLogLevel(); got != "trace" {
		t.Fatalf("got %q, want trace", got)
	}
}
