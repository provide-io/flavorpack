// SPDX-FileCopyrightText: Copyright (c) 2026 provide.io llc. All rights reserved.
// SPDX-License-Identifier: Apache-2.0

package logging

import (
	"bytes"
	"errors"
	"io"
	"testing"
)

// failWriter is an io.Writer that always returns an error.
type failWriter struct{ err error }

func (f *failWriter) Write(_ []byte) (int, error) { return 0, f.err }

// nthFailWriter succeeds for the first n-1 writes then returns an error.
type nthFailWriter struct {
	err     error
	written int
	failAt  int
}

func (w *nthFailWriter) Write(p []byte) (int, error) {
	w.written++
	if w.written >= w.failAt {
		return 0, w.err
	}
	return len(p), nil
}

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

func TestPrefixWriterPropagatesPrefixWriteError(t *testing.T) {
	boom := errors.New("disk full")
	pw := NewPrefixWriter("P ", &failWriter{err: boom})
	_, err := pw.Write([]byte("line\n"))
	if !errors.Is(err, boom) {
		t.Fatalf("expected write error to propagate, got %v", err)
	}
}

func TestPrefixWriterPropagatesLineWriteError(t *testing.T) {
	// Succeeds on prefix write (1st write) but fails on line write (2nd write).
	boom := errors.New("disk full on line")
	pw := NewPrefixWriter("P ", &nthFailWriter{err: boom, failAt: 2})
	_, err := pw.Write([]byte("line\n"))
	if !errors.Is(err, boom) {
		t.Fatalf("expected line write error to propagate, got %v", err)
	}
}

func TestPrefixWriterNilCompileCheck(_ *testing.T) {
	// Ensure PrefixWriter implements io.Writer at compile time.
	var _ io.Writer = &PrefixWriter{}
}
