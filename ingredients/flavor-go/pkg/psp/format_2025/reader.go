package format_2025

import (
	"archive/tar"
	"bytes"
	"compress/gzip"
	"crypto/ed25519"
	"encoding/binary"
	"encoding/json"
	"errors"
	"fmt"
	"hash/adler32"
	"io"
	"os"
	"path/filepath"
)

const (
	// Default file permissions
	DefaultFilePerms      os.FileMode = 0600  // Read/write for owner only
	DefaultExecutablePerms os.FileMode = 0700  // Read/write/execute for owner only
	DefaultDirPerms       os.FileMode = 0700  // Read/write/execute for owner only (secure by default)
)

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
}

// NewReader creates a new PSPF reader
func NewReader(bundlePath string) (*Reader, error) {
	return &Reader{
		bundlePath: bundlePath,
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

// VerifyMagic verifies the emoji magic at end of file
func (r *Reader) VerifyMagic() (bool, error) {
	if err := r.Open(); err != nil {
		return false, err
	}

	// Seek to end minus emoji magic size
	if _, err := r.file.Seek(-EmojiMagicSize, io.SeekEnd); err != nil {
		return false, err
	}

	magic := make([]byte, EmojiMagicSize)
	if _, err := r.file.Read(magic); err != nil {
		return false, err
	}

	// Check for package and magic wand emojis (8 bytes per PSPF/2025 spec)
	// Expected: 📦 (0xF0 0x9F 0x93 0xA6) + 🪄 (0xF0 0x9F 0xAA 0x84)
	expectedMagic := []byte{0xF0, 0x9F, 0x93, 0xA6, 0xF0, 0x9F, 0xAA, 0x84}
	if !bytes.Equal(magic, expectedMagic) {
		return false, ErrInvalidEmojiMagic
	}
	return true, nil
}

// DetectLauncherSize detects launcher size by finding index block
func (r *Reader) DetectLauncherSize() (int64, error) {
	if err := r.Open(); err != nil {
		return 0, err
	}

	// Read file in chunks to find PSPF magic
	const chunkSize = 1024 * 1024      // 1MB chunks
	const maxSearch = 10 * 1024 * 1024 // Search up to 10MB

	for offset := int64(0); offset < maxSearch; offset += chunkSize {
		if _, err := r.file.Seek(offset, io.SeekStart); err != nil {
			return 0, err
		}

		data := make([]byte, chunkSize)
		n, err := r.file.Read(data)
		if err != nil && err != io.EOF {
			return 0, err
		}
		if n == 0 {
			break
		}
		data = data[:n]

		// Search for PSPF magic in this chunk
		pos := bytes.Index(data, PSPFMagic)
		if pos >= 0 {
			return offset + int64(pos), nil
		}
	}

	return 0, ErrInvalidMagic
}

// ReadIndex reads and verifies the index block
func (r *Reader) ReadIndex() (*PSPFIndex, error) {
	if r.index != nil {
		return r.index, nil
	}

	if err := r.Open(); err != nil {
		return nil, err
	}

	launcherSize, err := r.DetectLauncherSize()
	if err != nil {
		return nil, err
	}

	// Seek to index position
	if _, err := r.file.Seek(launcherSize, io.SeekStart); err != nil {
		return nil, err
	}

	// Read index data
	indexData := make([]byte, IndexSize)
	if _, err := r.file.Read(indexData); err != nil {
		return nil, err
	}

	// Unpack index
	index := &PSPFIndex{}
	if err := index.Unpack(indexData); err != nil {
		return nil, err
	}

	// Verify magic
	if !bytes.Equal(index.FormatMagic[:], PSPFMagic) {
		return nil, ErrInvalidMagic
	}

	// Verify version
	if index.FormatVersion != PSPFVersion {
		return nil, ErrInvalidVersion
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

	// Verify checksum (Adler-32 stored in first 4 bytes)
	expectedChecksum := binary.LittleEndian.Uint32(index.MetadataChecksum[:4])
	actualChecksum := adler32.Checksum(metadataData)
	if actualChecksum != expectedChecksum {
		return nil, ErrChecksumMismatch
	}

	return metadataData, nil
}

// ReadSlot reads a specific slot
func (r *Reader) ReadSlot(slotIndex int) ([]byte, error) {
	index, err := r.ReadIndex()
	if err != nil {
		return nil, err
	}

	if slotIndex >= int(index.SlotCount) {
		return nil, ErrInvalidSlotIndex
	}

	// Read slot table entry (64 bytes per entry)
	slotTableEntryOffset := int64(index.SlotTableOffset) + int64(slotIndex*64)
	if _, err := r.file.Seek(slotTableEntryOffset, io.SeekStart); err != nil {
		return nil, err
	}

	// Read slot descriptor (64 bytes total)
	var entryData [64]byte
	if _, err := r.file.Read(entryData[:]); err != nil {
		return nil, err
	}

	// Unpack the 64-byte descriptor
	entry := SlotDescriptor{
		// Identity (16 bytes)
		ID:       binary.LittleEndian.Uint64(entryData[0:8]),
		NameHash: binary.LittleEndian.Uint64(entryData[8:16]),
		// Location (16 bytes)
		Offset: binary.LittleEndian.Uint64(entryData[16:24]),
		Size:   binary.LittleEndian.Uint64(entryData[24:32]),
		// Properties (16 bytes)
		OriginalSize: binary.LittleEndian.Uint64(entryData[32:40]),
		Checksum:     binary.LittleEndian.Uint32(entryData[40:44]),
		Encoding:     entryData[44],
		Encryption:   entryData[45],
		Alignment:    binary.LittleEndian.Uint16(entryData[46:48]),
		// Semantics (8 bytes)
		Purpose:     entryData[48],
		Lifecycle:   entryData[49],
		AccessHint:  entryData[50],
		Priority:    entryData[51],
		Permissions: binary.LittleEndian.Uint16(entryData[52:54]),
		Platform:    binary.LittleEndian.Uint16(entryData[54:56]),
		// Extended (8 bytes)
		ExtendedOffset: binary.LittleEndian.Uint32(entryData[56:60]),
		ExtendedSize:   binary.LittleEndian.Uint32(entryData[60:64]),
	}

	// Read slot data
	if _, err := r.file.Seek(int64(entry.Offset), io.SeekStart); err != nil {
		return nil, err
	}

	// Read compressed data
	slotData := make([]byte, entry.Size)
	if _, err := r.file.Read(slotData); err != nil {
		return nil, err
	}

	// Verify checksum of compressed data
	if adler32.Checksum(slotData) != entry.Checksum {
		return nil, ErrChecksumMismatch
	}

	// Decompress if needed based on entry.Encoding
	switch entry.Encoding {
	case EncodingRaw: // Raw uncompressed data
		return slotData, nil
	case EncodingTar: // Uncompressed tar archive
		// Return as-is, caller will extract tar
		return slotData, nil
	case EncodingGzip: // Single file, gzipped
		gz, err := gzip.NewReader(bytes.NewReader(slotData))
		if err != nil {
			return nil, fmt.Errorf("failed to create gzip reader: %w", err)
		}
		defer gz.Close()

		decompressed, err := io.ReadAll(gz)
		if err != nil {
			return nil, fmt.Errorf("failed to decompress gzip data: %w", err)
		}
		return decompressed, nil
	case EncodingTgz: // Tar archive, then gzipped
		// First decompress the gzip layer
		gz, err := gzip.NewReader(bytes.NewReader(slotData))
		if err != nil {
			return nil, fmt.Errorf("failed to create gzip reader for tar.gz: %w", err)
		}
		defer gz.Close()

		decompressed, err := io.ReadAll(gz)
		if err != nil {
			return nil, fmt.Errorf("failed to decompress tar.gz: %w", err)
		}
		// Return the tar archive for extraction
		return decompressed, nil
	default:
		// Unknown encoding, return as-is
		return slotData, nil
	}
}

// isTarball checks if data is a tar archive
func isTarball(data []byte) bool {
	// Check for tar magic header (ustar)
	if len(data) >= 512 {
		// Check for ustar magic at offset 257
		if string(data[257:262]) == "ustar" {
			return true
		}
		// Also check if it looks like a tar header (name field is ASCII)
		isASCII := true
		for i := 0; i < 100 && i < len(data); i++ {
			if data[i] == 0 {
				break
			}
			if data[i] < 32 || data[i] > 126 {
				isASCII = false
				break
			}
		}
		// We no longer use tar archives, so just check if it looks like text
		return isASCII && len(data) >= 512
	}
	return false
}

// ExtractSlot extracts a slot to the specified directory
func (r *Reader) ExtractSlot(slotIndex int, destDir string) (string, error) {
	metadata, err := r.ReadMetadata()
	if err != nil {
		return "", err
	}

	if slotIndex >= len(metadata.Slots) {
		return "", ErrInvalidSlotIndex
	}

	slotMeta := metadata.Slots[slotIndex]
	// ReadSlot already handles decompression based on the slot's encoding!
	decompressed, err := r.ReadSlot(slotIndex)
	if err != nil {
		return "", fmt.Errorf("%w: failed to read slot %d: %v", ErrSlotExtractionFailed, slotIndex, err)
	}

	// Read slot descriptor to get permissions
	index, err := r.ReadIndex()
	if err != nil {
		return "", err
	}
	
	// Read slot table entry (64 bytes per entry) to get permissions
	slotTableEntryOffset := int64(index.SlotTableOffset) + int64(slotIndex*64)
	if _, err := r.file.Seek(slotTableEntryOffset, io.SeekStart); err != nil {
		return "", err
	}
	
	var entryData [64]byte
	if _, err := r.file.Read(entryData[:]); err != nil {
		return "", err
	}
	
	// Extract permissions field (bytes 52-54)
	slotPermissions := binary.LittleEndian.Uint16(entryData[52:54])

	// Target field specifies where to extract (relative to workenv)
	destPath := filepath.Join(destDir, slotMeta.Target)
	extractDir := filepath.Dir(destPath)

	// Check if this is a tarball that needs extraction
	if isTarball(decompressed) {

		// Ensure extraction directory exists
		if err := os.MkdirAll(extractDir, DefaultDirPerms); err != nil {
			return "", fmt.Errorf("%w: failed to create extraction directory for slot %d: %v", ErrSlotExtractionFailed, slotIndex, err)
		}

		tr := tar.NewReader(bytes.NewReader(decompressed))
		for {
			hdr, err := tr.Next()
			if err == io.EOF {
				break
			}
			if err != nil {
				return "", fmt.Errorf("%w: tar extraction failed for slot %d: %v", ErrSlotExtractionFailed, slotIndex, err)
			}

			target := filepath.Join(extractDir, hdr.Name)

			switch hdr.Typeflag {
			case tar.TypeDir:
				if err := os.MkdirAll(target, os.FileMode(hdr.Mode)); err != nil {
					return "", fmt.Errorf("%w: failed to create directory during extraction: %v", ErrSlotExtractionFailed, err)
				}
			case tar.TypeReg:
				// Ensure parent directory exists
				if err := os.MkdirAll(filepath.Dir(target), DefaultDirPerms); err != nil {
					return "", err
				}

				out, err := os.OpenFile(target, os.O_CREATE|os.O_WRONLY|os.O_TRUNC, os.FileMode(hdr.Mode))
				if err != nil {
					return "", err
				}

				if _, err := io.Copy(out, tr); err != nil {
					if closeErr := out.Close(); closeErr != nil {
						// Log but don't mask the original error
						_ = closeErr
					}
					return "", err
				}
				if err := out.Close(); err != nil {
					return "", fmt.Errorf("failed to close output file: %w", err)
				}

				// Set executable bit if needed
				if hdr.Mode&0111 != 0 {
					if err := os.Chmod(target, os.FileMode(hdr.Mode)); err != nil {
						// Best effort - log but don't fail
						_ = err
					}
				}
			case tar.TypeSymlink:
				// Ensure parent directory exists
				if err := os.MkdirAll(filepath.Dir(target), DefaultDirPerms); err != nil {
					return "", err
				}

				// Remove existing symlink if present
				if err := os.Remove(target); err != nil && !os.IsNotExist(err) {
					// Best effort cleanup - only log if not "file doesn't exist"
					_ = err
				}

				// Create symlink
				if err := os.Symlink(hdr.Linkname, target); err != nil {
					return "", err
				}
			}
		}

		// Return the directory where we extracted
		return extractDir, nil
	}

	// Single file - write directly
	// Special case: if destPath is a directory (like for Python going to cache root),
	// write to a file inside it
	if info, err := os.Stat(destPath); err == nil && info.IsDir() {
		// This is the case where Python tarball goes to cache root
		// Just return the directory since it's a tarball that will be extracted
		return destPath, nil
	}

	if err := os.MkdirAll(filepath.Dir(destPath), DefaultDirPerms); err != nil {
		return "", err
	}

	// Use permissions from slot descriptor if available, otherwise use defaults
	var perm os.FileMode
	if slotPermissions != 0 {
		perm = os.FileMode(slotPermissions)
	} else {
		perm = DefaultFilePerms // 0600 - secure by default
	}

	if err := os.WriteFile(destPath, decompressed, perm); err != nil {
		return "", fmt.Errorf("%w: failed to write slot %d to disk: %v", ErrSlotExtractionFailed, slotIndex, err)
	}

	return destPath, nil
}

// VerifyAllChecksums verifies all slot checksums
func (r *Reader) VerifyAllChecksums() error {
	index, err := r.ReadIndex()
	if err != nil {
		return err
	}

	for i := 0; i < int(index.SlotCount); i++ {
		if _, err := r.ReadSlot(i); err != nil {
			return fmt.Errorf("slot %d: %w", i, err)
		}
	}

	return nil
}

// ReadEmojiMagic reads the emoji magic from the end of the file
func (r *Reader) ReadEmojiMagic(buf []byte) error {
	if len(buf) != 16 {
		return fmt.Errorf("buffer must be 16 bytes")
	}

	info, err := r.file.Stat()
	if err != nil {
		return err
	}

	// Seek to emoji magic position (last 16 bytes)
	if _, err := r.file.Seek(info.Size()-16, io.SeekStart); err != nil {
		return err
	}

	_, err = r.file.Read(buf)
	return err
}

// VerifyIntegritySeal verifies the metadata integrity using Ed25519 signature
func (r *Reader) VerifyIntegritySeal() (bool, error) {
	index, err := r.ReadIndex()
	if err != nil {
		return false, err
	}

	// Read metadata archive
	if _, err := r.file.Seek(int64(index.MetadataOffset), io.SeekStart); err != nil {
		return false, err
	}

	archiveData := make([]byte, index.MetadataSize)
	if _, err := r.file.Read(archiveData); err != nil {
		return false, err
	}

	// Extract psp.json and signature from archive
	// Decompress the gzipped JSON metadata
	gr, err := gzip.NewReader(bytes.NewReader(archiveData))
	if err != nil {
		return false, err
	}
	defer func() {
		if err := gr.Close(); err != nil {
			// Log error but don't fail - already returning data
			_ = err
		}
	}()

	// Read the JSON metadata
	jsonData, err := io.ReadAll(gr)
	if err != nil {
		return false, err
	}

	// Get signature from index (first 64 bytes of IntegritySignature field)
	signature := index.IntegritySignature[:64]

	// Check if signature is present (not all zeros)
	allZeros := true
	for _, b := range signature {
		if b != 0 {
			allZeros = false
			break
		}
	}
	if allZeros {
		return false, ErrNoIntegritySeal
	}

	// Verify signature using public key from index
	publicKey := index.PublicKey[:]
	if !ed25519.Verify(publicKey, jsonData, signature) {
		return false, ErrSignatureInvalid
	}
	return true, nil
}
