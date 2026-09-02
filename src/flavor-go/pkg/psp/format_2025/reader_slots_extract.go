// SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
// SPDX-License-Identifier: Apache-2.0

package format_2025

import (
	"archive/tar"
	"bytes"
	"encoding/binary"
	"fmt"
	"io"
	"log/slog"
	"os"
	"path/filepath"
	"strings"

	"github.com/provide-io/flavor/go/flavor/pkg/logging"
)

// readSlotPermissions reads the permission bits from a slot's 64-byte table
// entry, where they occupy the last two bytes.
func (r *Reader) readSlotPermissions(index *PSPFIndex, slotIndex int) (uint16, error) {
	entryOffset := int64(index.SlotTableOffset) + int64(slotIndex*SlotDescriptorSize)
	if _, err := fileSeekFn(r.file, entryOffset, io.SeekStart); err != nil {
		return 0, err
	}

	var entryData [SlotDescriptorSize]byte
	if _, err := fileReadFn(r.file, entryData[:]); err != nil {
		return 0, err
	}

	return binary.LittleEndian.Uint16(entryData[62:64]), nil
}

// resolveSlotTarget strips the {workenv} placeholder from a slot's target.
// Extraction is already rooted at the work environment, so the placeholder
// would otherwise nest a second copy of it inside.
func resolveSlotTarget(target string) string {
	if !strings.Contains(target, "{workenv}") {
		return target
	}
	target = strings.ReplaceAll(target, "{workenv}/", "")
	return strings.ReplaceAll(target, "{workenv}", "")
}

// escapesDir reports whether a path resolves outside base.
func escapesDir(path, base string) bool {
	cleanPath := filepath.Clean(path)
	cleanBase := filepath.Clean(base)
	return !strings.HasPrefix(cleanPath, cleanBase+string(os.PathSeparator)) && cleanPath != cleanBase
}

// slotDestination decides where a slot's contents land.
//
// A tar slot always extracts to destDir whatever its target says, because the
// archive's own entries carry the directory structure: honouring the target as
// well would nest it twice (target "wheels" plus entry "wheels/foo.whl" gives
// wheels/wheels/foo.whl). The Rust launcher ignores the target here for the
// same reason.
//
// A non-tar slot aimed at the work environment root goes to a slot-specific
// subdirectory instead, so the merge afterwards can move it atomically.
func slotDestination(destDir, targetPath string, slotIndex int, slotID string, isTar bool) (string, error) {
	switch {
	case isTar:
		return destDir, nil

	case targetPath == "" || targetPath == ".":
		return filepath.Join(destDir, fmt.Sprintf("slot_%d_%s", slotIndex, slotID)), nil

	default:
		destPath := filepath.Join(destDir, targetPath)
		if escapesDir(destPath, destDir) {
			return "", fmt.Errorf("target path %q escapes extraction directory", targetPath)
		}
		return destPath, nil
	}
}

// extractTarEntry writes one archive member.
func extractTarEntry(tr *tar.Reader, hdr *tar.Header, target string) error {
	switch hdr.Typeflag {
	case tar.TypeDir:
		if err := tarMkdirAllFn(target, os.FileMode(hdr.Mode)); err != nil {
			return fmt.Errorf("%w: failed to create directory during extraction: %v", ErrSlotExtractionFailed, err)
		}
		return nil

	case tar.TypeReg:
		if err := tarMkdirAllFn(filepath.Dir(target), os.FileMode(DirPerms)); err != nil {
			return err
		}

		out, err := os.OpenFile(target, os.O_CREATE|os.O_WRONLY|os.O_TRUNC, os.FileMode(hdr.Mode))
		if err != nil {
			return err
		}
		if _, err := tarIoCopyFn(out, tr); err != nil {
			// Close, but report the copy failure rather than the close.
			_ = tarOutCloseFn(out)
			return err
		}
		if err := tarOutCloseFn(out); err != nil {
			return fmt.Errorf("failed to close output file: %w", err)
		}

		if hdr.Mode&0o111 != 0 {
			// Best effort: a file that is not executable is still extracted.
			_ = tarChmodFn(target, os.FileMode(hdr.Mode))
		}
		return nil

	case tar.TypeSymlink:
		return fmt.Errorf("tar entry %q contains a symlink — symlinks are not permitted in PSPF packages", hdr.Name)

	default:
		return nil
	}
}

// extractTarball unpacks a tar slot, refusing any entry that would write
// outside the extraction directory.
func extractTarball(data []byte, extractDir string, slotIndex int) (string, error) {
	if err := tarMkdirAllFn(extractDir, os.FileMode(DirPerms)); err != nil {
		return "", fmt.Errorf("%w: failed to create extraction directory for slot %d: %v", ErrSlotExtractionFailed, slotIndex, err)
	}

	tr := tar.NewReader(bytes.NewReader(data))
	for {
		hdr, err := tr.Next()
		if err == io.EOF {
			break
		}
		if err != nil {
			return "", fmt.Errorf("%w: tar extraction failed for slot %d: %v", ErrSlotExtractionFailed, slotIndex, err)
		}

		target := filepath.Join(extractDir, hdr.Name)
		if escapesDir(target, extractDir) {
			return "", fmt.Errorf("tar entry %q escapes extraction directory", hdr.Name)
		}

		if err := extractTarEntry(tr, hdr, target); err != nil {
			return "", err
		}
	}

	return extractDir, nil
}

// writeSlotFile writes a single-file slot.
//
// A destination that is already a directory is left alone: that is the shape a
// tarball bound for the cache root takes, and it has its own extraction.
func writeSlotFile(
	data []byte,
	destPath string,
	slotPermissions uint16,
	slotIndex int,
	logger *slog.Logger,
) (string, error) {
	if info, err := os.Stat(destPath); err == nil && info.IsDir() {
		logging.Trace(logger, "🔍 Destination is existing directory, skipping write", "destPath", destPath)
		return destPath, nil
	}

	if err := os.MkdirAll(filepath.Dir(destPath), os.FileMode(DirPerms)); err != nil {
		return "", err
	}

	perm := os.FileMode(FilePerms) // 0600 - secure by default
	if slotPermissions != 0 {
		perm = os.FileMode(slotPermissions)
	}

	logging.Trace(logger, "📝 Writing single file", "destPath", destPath, "dataLen", len(data), "permissions", fmt.Sprintf("%04o", perm))

	// A gzip header here means the decompression chain did not run.
	if len(data) >= 3 && data[0] == 0x1f && data[1] == 0x8b && data[2] == 0x08 {
		logger.Warn("⚠️ Data appears to still be gzipped!", "firstBytes", fmt.Sprintf("%x", data[:10]))
	}

	if err := os.WriteFile(destPath, data, perm); err != nil {
		return "", fmt.Errorf("%w: failed to write slot %d to disk: %v", ErrSlotExtractionFailed, slotIndex, err)
	}

	logging.Trace(logger, "✅ Wrote file", "path", destPath, "size", len(data))
	return destPath, nil
}
