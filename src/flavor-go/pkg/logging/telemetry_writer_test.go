package logging

import (
	"bytes"
	"context"
	"strings"
	"testing"
)

// The launcher prefix is why provide-telemetry 0.8.x was backed out: with no
// writer hook the launcher cannot mark its own lines, and Go and Rust output
// becomes indistinguishable when both share one stream. 0.9.0 restored
// WithLogOutput, so this pins that the prefix reaches the records.
func TestPrefixSurvivesTelemetrySetup(t *testing.T) {
	var buf bytes.Buffer
	Setup("debug", NewPrefixWriter("🐹 ", &buf))

	NewLogger(context.Background(), "smoke").Info("hello from the launcher")

	out := buf.String()
	if !strings.Contains(out, "🐹 ") {
		t.Fatalf("prefix missing from telemetry output: %q", out)
	}
	if !strings.Contains(out, "hello from the launcher") {
		t.Fatalf("message missing from telemetry output: %q", out)
	}
	t.Logf("output: %s", strings.TrimSpace(out))
}
