package logging

import (
	"bytes"
	"testing"
)

// TestPrefixWriterMultipleLines covers writing multiple complete lines in a single call.
func TestPrefixWriterMultipleLines(t *testing.T) {
	t.Parallel()

	var buf bytes.Buffer
	pw := NewPrefixWriter(">> ", &buf)

	input := "line1\nline2\nline3\n"
	n, err := pw.Write([]byte(input))
	if err != nil {
		t.Fatalf("Write error: %v", err)
	}
	if n != len(input) {
		t.Fatalf("Write returned n=%d, want %d", n, len(input))
	}

	want := ">> line1\n>> line2\n>> line3\n"
	if got := buf.String(); got != want {
		t.Fatalf("got %q, want %q", got, want)
	}
}

// TestPrefixWriterEmptyInput covers writing empty input (no output expected).
func TestPrefixWriterEmptyInput(t *testing.T) {
	t.Parallel()

	var buf bytes.Buffer
	pw := NewPrefixWriter("P ", &buf)

	n, err := pw.Write([]byte(""))
	if err != nil {
		t.Fatalf("Write error: %v", err)
	}
	if n != 0 {
		t.Fatalf("Write returned n=%d, want 0", n)
	}
	if buf.Len() != 0 {
		t.Fatalf("expected no output, got %q", buf.String())
	}
}

// TestPrefixWriterOnlyNewline covers writing just a newline character.
func TestPrefixWriterOnlyNewline(t *testing.T) {
	t.Parallel()

	var buf bytes.Buffer
	pw := NewPrefixWriter("P ", &buf)

	if _, err := pw.Write([]byte("\n")); err != nil {
		t.Fatalf("Write error: %v", err)
	}
	if got := buf.String(); got != "P \n" {
		t.Fatalf("got %q, want %q", got, "P \n")
	}
}

// TestPrefixWriterPartialThenNewline covers buffering a partial line
// then completing it with another write.
func TestPrefixWriterPartialThenNewline(t *testing.T) {
	t.Parallel()

	var buf bytes.Buffer
	pw := NewPrefixWriter("| ", &buf)

	// First write: partial (no newline) -- should buffer
	if _, err := pw.Write([]byte("hello")); err != nil {
		t.Fatalf("Write(partial) error: %v", err)
	}
	if buf.Len() != 0 {
		t.Fatalf("expected empty buffer after partial write, got %q", buf.String())
	}

	// Second write: complete the line
	if _, err := pw.Write([]byte(" world\n")); err != nil {
		t.Fatalf("Write(completion) error: %v", err)
	}
	if got := buf.String(); got != "| hello world\n" {
		t.Fatalf("got %q, want %q", got, "| hello world\n")
	}
}
