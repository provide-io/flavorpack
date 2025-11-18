package logging

import (
	"bytes"
	"io"
)

// PrefixWriter wraps an io.Writer and adds a prefix to each line.
type PrefixWriter struct {
	prefix string
	writer io.Writer
	buffer bytes.Buffer
}

// NewPrefixWriter creates a new PrefixWriter.
func NewPrefixWriter(prefix string, w io.Writer) *PrefixWriter {
	return &PrefixWriter{
		prefix: prefix,
		writer: w,
	}
}

// Write implements the io.Writer interface. It buffers data until a newline
// is encountered, then writes the prefixed line to the underlying writer.
func (pw *PrefixWriter) Write(p []byte) (int, error) {
	n := len(p)
	if _, err := pw.buffer.Write(p); err != nil {
		return 0, err
	}

	for {
		line, err := pw.buffer.ReadBytes('\n')
		if err != nil {
			// If we have an incomplete line, write it back to the buffer and wait for more data.
			if len(line) > 0 {
				// This operation should not fail as we are writing to an in-memory buffer.
				if _, wErr := pw.buffer.Write(line); wErr != nil {
					return 0, wErr
				}
			}
			break
		}

		if _, err := pw.writer.Write([]byte(pw.prefix)); err != nil {
			return 0, err
		}
		if _, err := pw.writer.Write(line); err != nil {
			return 0, err
		}
	}

	return n, nil
}
