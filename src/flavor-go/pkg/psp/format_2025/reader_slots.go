package format_2025

import (
	"bytes"
	"compress/gzip"
	"crypto/sha256"
	"encoding/binary"
	"fmt"
	"io"
	"os"

	"log/slog"

	"github.com/provide-io/flavor/go/flavor/pkg/logging"
)

var tarMkdirAllFn = os.MkdirAll
var tarIoCopyFn = io.Copy
var tarOutCloseFn = func(f *os.File) error { return f.Close() }
var tarChmodFn = os.Chmod

// ReadSlot reads and decompresses a slot by index
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
	if _, err := fileSeekFn(r.file, slotTableEntryOffset, io.SeekStart); err != nil {
		return nil, err
	}

	// Read slot descriptor (64 bytes total)
	var entryData [64]byte
	if _, err := fileReadFn(r.file, entryData[:]); err != nil {
		return nil, err
	}

	// Unpack the 64-byte descriptor using the new format
	entry, err := UnpackSlotDescriptor(entryData[:])
	if err != nil {
		return nil, fmt.Errorf("failed to unpack slot descriptor: %w", err)
	}

	// Read slot data
	if _, err := fileSeekFn(r.file, int64(entry.Offset), io.SeekStart); err != nil {
		return nil, err
	}

	// Read compressed data
	slotData := make([]byte, entry.Size)
	if _, err := fileReadFn(r.file, slotData); err != nil {
		return nil, err
	}

	// Verify checksum of compressed data (SHA-256 first 8 bytes)
	hash := sha256.Sum256(slotData)
	actualChecksum := binary.LittleEndian.Uint64(hash[:8])

	logger := r.logger
	if logger == nil {
		logger = slog.Default()
	}
	firstBytesLen := len(slotData)
	if firstBytesLen > 16 {
		firstBytesLen = 16
	}
	logger.Debug("🐹 Go launcher verifying slot checksum",
		"slot_id", entry.ID,
		"data_length", len(slotData),
		"first_16_bytes", fmt.Sprintf("%02x", slotData[:firstBytesLen]),
		"computed_checksum", fmt.Sprintf("%016x", actualChecksum),
		"expected_checksum", fmt.Sprintf("%016x", entry.Checksum))

	if actualChecksum != entry.Checksum {
		return nil, ErrChecksumMismatch
	}

	// Decompress based on operations chain
	operations := UnpackOperations(entry.Operations)
	logging.Trace(logger, "🔍 Slot operations", "operations", fmt.Sprintf("%#x", entry.Operations), "unpacked", operations)

	// Apply operations in reverse order (unwrap the layers)
	result := slotData
	for i := len(operations) - 1; i >= 0; i-- {
		op := operations[i]
		logging.Trace(logger, "🔄 Processing operation", "op", fmt.Sprintf("%#x", op), "name", OperationName(op))

		switch op {
		case OP_GZIP:
			// Decompress gzip
			logging.Trace(logger, "📦 Decompressing GZIP", "inputSize", len(result))
			gz, err := gzip.NewReader(bytes.NewReader(result))
			if err != nil {
				return nil, fmt.Errorf("failed to create gzip reader: %w", err)
			}
			decompressed, err := io.ReadAll(gz)
			_ = gz.Close()
			if err != nil {
				return nil, fmt.Errorf("failed to decompress gzip data: %w", err)
			}
			logging.Trace(logger, "✅ GZIP decompressed", "outputSize", len(decompressed))
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
		// Also check for GNU tar format (oldgnu)
		if string(data[257:265]) == "ustar  \x00" {
			return true
		}
	}
	return false
}

// ExtractSlot extracts a slot to the specified directory
func (r *Reader) ExtractSlot(slotIndex int, destDir string) (string, error) {
	logger := r.logger
	if logger == nil {
		logger = slog.Default()
	}

	metadata, err := r.ReadMetadata()
	if err != nil {
		return "", err
	}

	if slotIndex >= len(metadata.Slots) {
		return "", ErrInvalidSlotIndex
	}

	slotMeta := metadata.Slots[slotIndex]
	logging.Trace(logger, "🔍 Extracting slot", "index", slotIndex, "id", slotMeta.ID, "target", slotMeta.Target)

	// ReadSlot already handles decompression based on the slot's encoding!
	decompressed, err := r.ReadSlot(slotIndex)
	if err != nil {
		return "", fmt.Errorf("%w: failed to read slot %d: %v", ErrSlotExtractionFailed, slotIndex, err)
	}

	index, err := r.ReadIndex()
	if err != nil {
		return "", err
	}

	slotPermissions, err := r.readSlotPermissions(index, slotIndex)
	if err != nil {
		return "", err
	}

	targetPath := resolveSlotTarget(slotMeta.Target)
	isTar := isTarball(decompressed)

	destPath, err := slotDestination(destDir, targetPath, slotIndex, slotMeta.ID, isTar)
	if err != nil {
		return "", err
	}

	logging.Trace(logger, "🔍 Slot data check", "isTarball", isTar, "dataLen", len(decompressed), "destPath", destPath)

	if isTar {
		return extractTarball(decompressed, destPath, slotIndex)
	}
	return writeSlotFile(decompressed, destPath, slotPermissions, slotIndex, logger)
}
