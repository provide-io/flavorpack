package logging

import (
	"bytes"
	"testing"
)

func TestPrefixWriterPrefixesCompleteLines(t *testing.T) {
	var buf bytes.Buffer
	writer := NewPrefixWriter("X ", &buf)

	if _, err := writer.Write([]byte("first\nsecond\n")); err != nil {
		t.Fatalf("write failed: %v", err)
	}

	if got := buf.String(); got != "X first\nX second\n" {
		t.Fatalf("got %q", got)
	}
}

func TestPrefixWriterBuffersPartialLines(t *testing.T) {
	var buf bytes.Buffer
	writer := NewPrefixWriter("> ", &buf)

	if _, err := writer.Write([]byte("partial")); err != nil {
		t.Fatalf("write failed: %v", err)
	}
	if got := buf.String(); got != "" {
		t.Fatalf("expected no flushed output, got %q", got)
	}

	if _, err := writer.Write([]byte(" line\n")); err != nil {
		t.Fatalf("second write failed: %v", err)
	}
	if got := buf.String(); got != "> partial line\n" {
		t.Fatalf("got %q", got)
	}
}
