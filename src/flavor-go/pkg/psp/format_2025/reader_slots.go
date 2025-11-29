package format_2025

import (
	"archive/tar"
	"bytes"
	"compress/gzip"
	"crypto/sha256"
	"encoding/binary"
	"fmt"
	"io"
	"os"
	"path/filepath"
	"strings"

	"github.com/hashicorp/go-hclog"
)

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

	// Verify checksum of compressed data (SHA-256 first 8 bytes)
	hash := sha256.Sum256(slotData)
	actualChecksum := binary.LittleEndian.Uint64(hash[:8])

	logger := r.logger
	if logger == nil {
		logger = hclog.L()
	}
	logger.Debug("🐹 Go launcher verifying slot checksum",
		"slot_id", entry.ID,
		"data_length", len(slotData),
		"first_16_bytes", fmt.Sprintf("%02x", slotData[:16]),
		"computed_checksum", fmt.Sprintf("%016x", actualChecksum),
		"expected_checksum", fmt.Sprintf("%016x", entry.Checksum))

	if actualChecksum != entry.Checksum {
		return nil, ErrChecksumMismatch
	}

	// Decompress based on operations chain
	operations := UnpackOperations(entry.Operations)
	logger.Trace("🔍 Slot operations", "operations", fmt.Sprintf("%#x", entry.Operations), "unpacked", operations)

	// Apply operations in reverse order (unwrap the layers)
	result := slotData
	for i := len(operations) - 1; i >= 0; i-- {
		op := operations[i]
		logger.Trace("🔄 Processing operation", "op", fmt.Sprintf("%#x", op), "name", OperationName(op))

		switch op {
		case OP_GZIP:
			// Decompress gzip
			logger.Trace("📦 Decompressing GZIP", "inputSize", len(result))
			gz, err := gzip.NewReader(bytes.NewReader(result))
			if err != nil {
				return nil, fmt.Errorf("failed to create gzip reader: %w", err)
			}
			decompressed, err := io.ReadAll(gz)
			gz.Close()
			if err != nil {
				return nil, fmt.Errorf("failed to decompress gzip data: %w", err)
			}
			logger.Trace("✅ GZIP decompressed", "outputSize", len(decompressed))
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
		logger = hclog.L()
	}

	metadata, err := r.ReadMetadata()
	if err != nil {
		return "", err
	}

	if slotIndex >= len(metadata.Slots) {
		return "", ErrInvalidSlotIndex
	}

	slotMeta := metadata.Slots[slotIndex]
	logger.Trace("🔍 Extracting slot", "index", slotIndex, "id", slotMeta.ID, "target", slotMeta.Target)

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

	// Extract permissions field (bytes 62-64)
	slotPermissions := binary.LittleEndian.Uint16(entryData[62:64])

	// Target field specifies where to extract (relative to workenv)
	// Substitute {workenv} placeholder with the actual destDir
	targetPath := slotMeta.Target
	if strings.Contains(targetPath, "{workenv}") {
		// Remove {workenv}/ prefix if present, as we're already extracting to destDir
		targetPath = strings.ReplaceAll(targetPath, "{workenv}/", "")
		targetPath = strings.ReplaceAll(targetPath, "{workenv}", "")
	}

	// Determine extraction paths based on target and whether it's a TAR archive
	var destPath, extractDir string

	// Check if this is a tarball first (needed for logic below)
	isTar := isTarball(decompressed)

	if targetPath == "" || targetPath == "." {
		// Target was "{workenv}" or "."
		if isTar {
			// TAR slots targeting {workenv}: extract directly to destDir (matches Rust behavior)
			// The tarball contents will be extracted directly to destDir
			destPath = destDir
			extractDir = destDir
		} else {
			// Non-TAR slots targeting {workenv}: extract to slot-specific subdirectory for atomic move
			slotSubdir := fmt.Sprintf("slot_%d_%s", slotIndex, slotMeta.ID)
			destPath = filepath.Join(destDir, slotSubdir)
			extractDir = destPath
		}
	} else {
		// Target has a subpath - join it with destDir
		destPath = filepath.Join(destDir, targetPath)
		extractDir = filepath.Dir(destPath)
	}

	logger.Trace("🔍 Slot data check", "isTarball", isTar, "dataLen", len(decompressed), "destPath", destPath)

	if isTar {

		// Ensure extraction directory exists
		if err := os.MkdirAll(extractDir, os.FileMode(DirPerms)); err != nil {
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
				if err := os.MkdirAll(filepath.Dir(target), os.FileMode(DirPerms)); err != nil {
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
				if err := os.MkdirAll(filepath.Dir(target), os.FileMode(DirPerms)); err != nil {
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
		logger.Trace("🔍 Destination is existing directory, skipping write", "destPath", destPath)
		return destPath, nil
	}

	if err := os.MkdirAll(filepath.Dir(destPath), os.FileMode(DirPerms)); err != nil {
		return "", err
	}

	// Use permissions from slot descriptor if available, otherwise use defaults
	var perm os.FileMode
	if slotPermissions != 0 {
		perm = os.FileMode(slotPermissions)
	} else {
		perm = os.FileMode(FilePerms) // 0600 - secure by default
	}

	// Log what we're about to write
	logger.Trace("📝 Writing single file", "destPath", destPath, "dataLen", len(decompressed), "permissions", fmt.Sprintf("%04o", perm))

	// Check first few bytes to see if it's still compressed
	if len(decompressed) >= 3 && decompressed[0] == 0x1f && decompressed[1] == 0x8b && decompressed[2] == 0x08 {
		logger.Warn("⚠️ Data appears to still be gzipped!", "firstBytes", fmt.Sprintf("%x", decompressed[:10]))
	}

	if err := os.WriteFile(destPath, decompressed, perm); err != nil {
		return "", fmt.Errorf("%w: failed to write slot %d to disk: %v", ErrSlotExtractionFailed, slotIndex, err)
	}

	logger.Trace("✅ Wrote file", "path", destPath, "size", len(decompressed))
	return destPath, nil
}
