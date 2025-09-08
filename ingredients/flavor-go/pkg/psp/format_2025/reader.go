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
	"strings"

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

// VerifyMagicTrailer verifies the MagicTrailer emoji bookends
func (r *Reader) VerifyMagicTrailer() (bool, error) {
	if err := r.Open(); err != nil {
		return false, err
	}

	// Get file size
	info, err := r.file.Stat()
	if err != nil {
		return false, err
	}

	// Read MagicTrailer (last 8200 bytes)
	trailer := make([]byte, MagicTrailerSize)
	if _, err := r.file.ReadAt(trailer, info.Size()-MagicTrailerSize); err != nil {
		return false, err
	}

	// Verify emoji bookends (📦 at start, 🪄 at end)
	if !bytes.Equal(trailer[:4], PackageEmojiBytes) {
		return false, ErrInvalidEmojiMagic
	}
	if !bytes.Equal(trailer[MagicTrailerSize-4:], MagicWandEmojiBytes) {
		return false, ErrInvalidEmojiMagic
	}
	return true, nil
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

	// Unpack the 64-byte descriptor using the new format
	entry, err := UnpackSlotDescriptor(entryData[:])
	if err != nil {
		return nil, fmt.Errorf("failed to unpack slot descriptor: %w", err)
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

	// Verify checksum of compressed data (entry.Checksum is uint64 but only uses lower 32 bits)
	if uint64(adler32.Checksum(slotData)) != entry.Checksum {
		return nil, ErrChecksumMismatch
	}

	// Decompress based on operations chain
	operations := UnpackOperations(entry.Operations)
	
	// Apply operations in reverse order (unwrap the layers)
	result := slotData
	for i := len(operations) - 1; i >= 0; i-- {
		op := operations[i]
		switch op {
		case OP_GZIP:
			// Decompress gzip
			gz, err := gzip.NewReader(bytes.NewReader(result))
			if err != nil {
				return nil, fmt.Errorf("failed to create gzip reader: %w", err)
			}
			decompressed, err := io.ReadAll(gz)
			gz.Close()
			if err != nil {
				return nil, fmt.Errorf("failed to decompress gzip data: %w", err)
			}
			result = decompressed
			
		case OP_TAR:
			// TAR is handled by caller, just return the data
			// (TAR is a bundle format, not compression)
			continue
			
		case OP_BZIP2, OP_ZSTD, OP_XZ:
			// These would need additional libraries
			return nil, fmt.Errorf("operation %s not yet implemented", OperationName(op))
			
		case OP_AES256_GCM:
			// Encryption would need key material
			return nil, fmt.Errorf("encryption operation %s not yet implemented", OperationName(op))
			
		default:
			if op != OP_NONE {
				return nil, fmt.Errorf("unknown operation: 0x%02x", op)
			}
		}
	}
	
	return result, nil
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
	// Substitute {workenv} placeholder with the actual destDir
	targetPath := slotMeta.Target
	if strings.Contains(targetPath, "{workenv}") {
		// Remove {workenv}/ prefix if present, as we're already extracting to destDir
		targetPath = strings.ReplaceAll(targetPath, "{workenv}/", "")
		targetPath = strings.ReplaceAll(targetPath, "{workenv}", "")
	}

	// If targetPath is empty after stripping {workenv}, extract directly to destDir
	var destPath, extractDir string
	if targetPath == "" {
		// Target was "{workenv}" - extract directly to destDir
		destPath = destDir
		extractDir = destDir
	} else {
		// Target has a subpath - join it with destDir
		destPath = filepath.Join(destDir, targetPath)
		extractDir = filepath.Dir(destPath)
	}

	// Check if this is a tarball that needs extraction
	if isTarball(decompressed) {

		// Ensure extraction directory exists
		if err := os.MkdirAll(extractDir, os.FileMode(DefaultDirPerms)); err != nil {
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
				if err := os.MkdirAll(filepath.Dir(target), os.FileMode(DefaultDirPerms)); err != nil {
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
				if err := os.MkdirAll(filepath.Dir(target), os.FileMode(DefaultDirPerms)); err != nil {
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

	if err := os.MkdirAll(filepath.Dir(destPath), os.FileMode(DefaultDirPerms)); err != nil {
		return "", err
	}

	// Use permissions from slot descriptor if available, otherwise use defaults
	var perm os.FileMode
	if slotPermissions != 0 {
		perm = os.FileMode(slotPermissions)
	} else {
		perm = os.FileMode(DefaultFilePerms) // 0600 - secure by default
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
