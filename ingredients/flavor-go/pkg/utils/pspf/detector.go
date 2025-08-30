// Package pspf provides utilities for working with PSPF files
package pspf

import (
	"bytes"
	"fmt"
	"io"
)

const (
	// ChunkSize for reading files when searching for magic
	ChunkSize = 1024 * 1024 // 1MB chunks
	// MaxSearchSize limits how far we'll search for PSPF magic
	MaxSearchSize = 10 * 1024 * 1024 // 10MB max
)

// FindIndexOffset searches for PSPF magic bytes and returns the offset where the index block starts
// This is equivalent to the launcher size since the index immediately follows the launcher
func FindIndexOffset(r io.ReadSeeker, magic []byte) (int64, error) {
	// Start from beginning
	if _, err := r.Seek(0, io.SeekStart); err != nil {
		return 0, fmt.Errorf("failed to seek to start: %w", err)
	}

	// Read file in chunks to find PSPF magic
	for offset := int64(0); offset < MaxSearchSize; offset += ChunkSize {
		if _, err := r.Seek(offset, io.SeekStart); err != nil {
			return 0, fmt.Errorf("failed to seek to offset %d: %w", offset, err)
		}

		data := make([]byte, ChunkSize)
		n, err := r.Read(data)
		if err != nil && err != io.EOF {
			return 0, fmt.Errorf("failed to read chunk at offset %d: %w", offset, err)
		}
		if n == 0 {
			break
		}
		data = data[:n]

		// Search for PSPF magic in this chunk
		pos := bytes.Index(data, magic)
		if pos >= 0 {
			// Return the position where the index starts
			indexOffset := offset + int64(pos)
			// Reset to beginning for caller
			if _, err := r.Seek(0, io.SeekStart); err != nil {
				return indexOffset, fmt.Errorf("failed to reset position: %w", err)
			}
			return indexOffset, nil
		}
	}

	return 0, fmt.Errorf("PSPF magic not found in first %d bytes", MaxSearchSize)
}

// FindTrailingMagic searches for the trailing emoji magic at the end of a PSPF file
func FindTrailingMagic(r io.ReadSeeker, expectedMagic []byte) (bool, error) {
	// Get file size
	size, err := r.Seek(0, io.SeekEnd)
	if err != nil {
		return false, fmt.Errorf("failed to seek to end: %w", err)
	}

	// Seek to position for trailing magic (last N bytes)
	magicSize := int64(len(expectedMagic))
	if size < magicSize {
		return false, fmt.Errorf("file too small for trailing magic")
	}

	if _, err := r.Seek(size-magicSize, io.SeekStart); err != nil {
		return false, fmt.Errorf("failed to seek to trailing magic position: %w", err)
	}

	// Read the trailing bytes
	magic := make([]byte, magicSize)
	if _, err := r.Read(magic); err != nil {
		return false, fmt.Errorf("failed to read trailing magic: %w", err)
	}

	// Reset to beginning for caller
	if _, err := r.Seek(0, io.SeekStart); err != nil {
		return bytes.Equal(magic, expectedMagic), fmt.Errorf("failed to reset position: %w", err)
	}

	return bytes.Equal(magic, expectedMagic), nil
}