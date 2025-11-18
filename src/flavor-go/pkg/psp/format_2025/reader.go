package format_2025

import (
	"bytes"
	"compress/gzip"
	"crypto/sha256"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"os"

	"github.com/hashicorp/go-hclog"
)

// Constants are defined in constants.go

var (
	ErrInvalidMagic      = errors.New("invalid magic sequence")
	ErrInvalidEmojiMagic = errors.New("invalid emoji magic")
	ErrInvalidVersion    = errors.New("invalid version")
	ErrChecksumMismatch  = errors.New("checksum mismatch")
	ErrInvalidSlotIndex  = errors.New("invalid slot index")
	ErrNoIntegritySeal   = errors.New("no integrity seal found")
	ErrSignatureInvalid  = errors.New("signature verification failed")
	// ErrSlotExtractionFailed is already declared in execution.go
)

// Reader reads PSPF 2025 bundles
type Reader struct {
	bundlePath string
	file       *os.File
	index      *PSPFIndex
	metadata   *Metadata
	logger     hclog.Logger
}

// NewReader creates a new PSPF reader
func NewReader(bundlePath string) (*Reader, error) {
	return NewReaderWithLogger(bundlePath, hclog.NewNullLogger())
}

// NewReaderWithLogger creates a new PSPF reader with a custom logger
func NewReaderWithLogger(bundlePath string, logger hclog.Logger) (*Reader, error) {
	if logger == nil {
		logger = hclog.NewNullLogger()
	}
	return &Reader{
		bundlePath: bundlePath,
		logger:     logger,
	}, nil
}

// Open opens the bundle file
func (r *Reader) Open() error {
	if r.file != nil {
		return nil
	}

	file, err := os.Open(r.bundlePath)
	if err != nil {
		return err
	}

	r.file = file
	return nil
}

// Close closes the bundle file
func (r *Reader) Close() error {
	if r.file != nil {
		err := r.file.Close()
		r.file = nil
		return err
	}
	return nil
}

// ReadMagicTrailer reads the MagicTrailer and returns the index data
func (r *Reader) ReadMagicTrailer() ([]byte, error) {
	if err := r.Open(); err != nil {
		return nil, err
	}

	// Get file size
	info, err := r.file.Stat()
	if err != nil {
		return nil, err
	}

	// Read MagicTrailer (last 8200 bytes)
	trailer := make([]byte, MagicTrailerSize)
	if _, err := r.file.ReadAt(trailer, info.Size()-MagicTrailerSize); err != nil {
		return nil, err
	}

	// Verify emoji bookends
	if !bytes.Equal(trailer[:4], PackageEmojiBytes) {
		return nil, fmt.Errorf("invalid MagicTrailer: missing 📦 at start")
	}
	if !bytes.Equal(trailer[MagicTrailerSize-4:], MagicWandEmojiBytes) {
		return nil, fmt.Errorf("invalid MagicTrailer: missing 🪄 at end")
	}

	// Extract index from between emojis
	indexData := trailer[4 : 4+IndexSize]

	r.logger.Debug("Found index in MagicTrailer", "trailer_size", MagicTrailerSize, "file_size", info.Size())

	return indexData, nil
}

// ReadIndex reads and verifies the index block
func (r *Reader) ReadIndex() (*PSPFIndex, error) {
	if r.index != nil {
		return r.index, nil
	}

	if err := r.Open(); err != nil {
		return nil, err
	}

	// Read index from MagicTrailer
	indexData, err := r.ReadMagicTrailer()
	if err != nil {
		return nil, err
	}

	// Debug: Log that we got the index
	r.logger.Debug("Parsing index from MagicTrailer", "size", IndexSize)

	// Unpack index
	index := &PSPFIndex{}
	if err := index.Unpack(indexData); err != nil {
		return nil, err
	}

	// Verify version
	if index.FormatVersion != PSPFVersion {
		return nil, fmt.Errorf("%w: got 0x%08x, expected 0x%08x", ErrInvalidVersion, index.FormatVersion, PSPFVersion)
	}

	r.index = index
	return index, nil
}

// ReadMetadata reads and parses metadata
func (r *Reader) ReadMetadata() (*Metadata, error) {
	if r.metadata != nil {
		return r.metadata, nil
	}

	index, err := r.ReadIndex()
	if err != nil {
		return nil, err
	}

	// Seek to metadata
	if _, err := r.file.Seek(int64(index.MetadataOffset), io.SeekStart); err != nil {
		return nil, err
	}

	// Read metadata archive
	archiveData := make([]byte, index.MetadataSize)
	if _, err := r.file.Read(archiveData); err != nil {
		return nil, err
	}

	// Decompress the gzipped JSON metadata
	gr, err := gzip.NewReader(bytes.NewReader(archiveData))
	if err != nil {
		return nil, err
	}
	defer func() {
		if err := gr.Close(); err != nil {
			// Log error but don't fail - already returning data
			_ = err
		}
	}()

	// Read and decode JSON directly
	var metadata Metadata
	if err := json.NewDecoder(gr).Decode(&metadata); err != nil {
		return nil, err
	}

	r.metadata = &metadata
	return &metadata, nil
}

// ReadMetadataArchive reads the raw metadata archive
func (r *Reader) ReadMetadataArchive() ([]byte, error) {
	index, err := r.ReadIndex()
	if err != nil {
		return nil, err
	}

	// Read metadata archive
	if _, err := r.file.Seek(int64(index.MetadataOffset), io.SeekStart); err != nil {
		return nil, err
	}

	metadataData := make([]byte, index.MetadataSize)
	if _, err := r.file.Read(metadataData); err != nil {
		return nil, err
	}

	// Verify checksum (full SHA-256, 32 bytes)
	actualHash := sha256.Sum256(metadataData)
	if actualHash != index.MetadataChecksum {
		return nil, ErrChecksumMismatch
	}

	return metadataData, nil
}
