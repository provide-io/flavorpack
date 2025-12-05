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
	// resourceData holds PSPF bytes extracted from PE resources when available.
	// When populated, the bundle no longer has PSPF data appended to the end
	// of the executable, so all reads must be served from this buffer.
	resourceData    []byte
	resourceChecked bool
	index           *PSPFIndex
	metadata        *Metadata
	logger          hclog.Logger
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

// ensureResourceDataLoaded attempts to load PSPF data from PE resources once.
// When successful, subsequent reads operate on the in-memory buffer instead of
// expecting PSPF data to be appended to the executable.
func (r *Reader) ensureResourceDataLoaded() {
	if r.resourceChecked {
		return
	}
	r.resourceChecked = true

	data, err := ReadPSPFFromResource(r.bundlePath, r.logger)
	if err != nil || len(data) == 0 {
		if r.logger != nil {
			r.logger.Debug("📖 No PE resource detected, reading PSPF from EOF (appended to executable)",
				"error", err)
		}
		return
	}

	r.resourceData = data
	if r.logger != nil {
		r.logger.Info("📖 PSPF payload found in PE resources",
			"size", len(r.resourceData))
	}
}

func (r *Reader) usingResourceData() bool {
	return len(r.resourceData) > 0
}

// resourceRelativeOffset converts an absolute file offset into an offset
// relative to the start of the PSPF resource data.
func (r *Reader) resourceRelativeOffset(absOffset uint64) (int64, error) {
	if r.index == nil {
		return 0, fmt.Errorf("resource offset requested before index is loaded")
	}
	rel := int64(absOffset) - int64(r.index.LauncherSize)
	if rel < 0 {
		return 0, fmt.Errorf("offset 0x%x lies inside launcher code, unavailable in resource", absOffset)
	}
	if rel > int64(len(r.resourceData)) {
		return 0, fmt.Errorf("offset 0x%x beyond resource bounds", absOffset)
	}
	return rel, nil
}

// readBytesAt reads size bytes starting at offset and returns the slice.
func (r *Reader) readBytesAt(offset uint64, size uint64) ([]byte, error) {
	buf := make([]byte, size)
	if err := r.readIntoBuffer(buf, offset); err != nil {
		return nil, err
	}
	return buf, nil
}

// readIntoBuffer fills buf with bytes at absolute offset.
func (r *Reader) readIntoBuffer(buf []byte, offset uint64) error {
	if len(buf) == 0 {
		return nil
	}

	if r.usingResourceData() {
		rel, err := r.resourceRelativeOffset(offset)
		if err != nil {
			return err
		}
		if rel+int64(len(buf)) > int64(len(r.resourceData)) {
			return fmt.Errorf("resource read beyond bounds at 0x%x", offset)
		}
		start := int(rel)
		end := start + len(buf)
		copy(buf, r.resourceData[start:end])
		return nil
	}

	if err := r.Open(); err != nil {
		return err
	}
	if _, err := r.file.Seek(int64(offset), io.SeekStart); err != nil {
		return err
	}
	if _, err := io.ReadFull(r.file, buf); err != nil {
		return err
	}
	return nil
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
	r.ensureResourceDataLoaded()

	if r.usingResourceData() {
		if len(r.resourceData) < MagicTrailerSize {
			return nil, fmt.Errorf("resource PSPF data too small for MagicTrailer")
		}
		trailer := r.resourceData[len(r.resourceData)-MagicTrailerSize:]

		if !bytes.Equal(trailer[:4], PackageEmojiBytes) {
			return nil, fmt.Errorf("invalid MagicTrailer: missing 📦 at start")
		}
		if !bytes.Equal(trailer[MagicTrailerSize-4:], MagicWandEmojiBytes) {
			return nil, fmt.Errorf("invalid MagicTrailer: missing 🪄 at end")
		}

		r.logger.Debug("Found index in PE resource MagicTrailer",
			"trailer_size", MagicTrailerSize,
			"resource_size", len(r.resourceData))
		return trailer[4 : 4+IndexSize], nil
	}

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

	archiveData, err := r.readBytesAt(index.MetadataOffset, index.MetadataSize)
	if err != nil {
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

	metadataData, err := r.readBytesAt(index.MetadataOffset, index.MetadataSize)
	if err != nil {
		return nil, err
	}

	// Verify checksum (full SHA-256, 32 bytes)
	actualHash := sha256.Sum256(metadataData)
	if actualHash != index.MetadataChecksum {
		return nil, ErrChecksumMismatch
	}

	return metadataData, nil
}
