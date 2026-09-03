// SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
// SPDX-License-Identifier: Apache-2.0

package format_2025

import (
	"crypto/sha256"
	"io"
	"log/slog"
	"os"
)

// mustSeek returns the current offset, ending the build if the file will not
// report it. A package cannot be laid out without knowing where it is.
func mustSeek(out *os.File, logger *slog.Logger) int64 {
	pos, err := out.Seek(0, io.SeekCurrent)
	if err != nil {
		logger.Error("❌ Failed to get file position", "error", err)
		buildExitFn(1)
	}
	return pos
}

// mustConvert ends the build when a value does not fit the index field it is
// bound for. The converters carry the field name in their error, so this adds
// only the decision to stop.
//
// These are all width checks on values the builder computed, so a failure is a
// package that cannot be described rather than a condition to recover from.
// Go will not take a multi-value call alongside another argument, so callers
// pass the value and error separately -- still half the four lines each of
// these checks used to cost.
func mustConvert[T any](v T, err error, logger *slog.Logger) T {
	if err != nil {
		logger.Error("❌ Failed to convert value for index", "error", err)
		buildExitFn(1)
	}
	return v
}

// writePackageMetadata writes the gzipped metadata immediately after the
// launcher and records where it landed. It returns the Ed25519 signature over
// the bytes as written, which the index carries.
func writePackageMetadata(
	out *os.File,
	metadata *Metadata,
	privateKey []byte,
	publicKey []byte,
	index *PSPFIndex,
	logger *slog.Logger,
) []byte {
	metadataPos := mustSeek(out, logger)
	logger.Debug("📜 Writing metadata (gzipped JSON)", "position", metadataPos)

	metadataSize, signature, err := writeMetadataFn(out, metadata, privateKey, publicKey)
	if err != nil {
		logger.Error("❌ Failed to write metadata", "error", err)
		buildExitFn(1)
	}
	logger.Debug("✅ Metadata written", "size", metadataSize)

	offset, err := int64ToUint64Checked(metadataPos, "metadata offset")
	index.MetadataOffset = mustConvert(offset, err, logger)

	size, err := intToUint64Checked(metadataSize, "metadata size")
	index.MetadataSize = mustConvert(size, err, logger)

	return signature
}

// reserveSlotTable positions the slot table on its alignment boundary, records
// its geometry in the index, and leaves the file positioned past it so slot
// data can be written first.
//
// The table is written last because a descriptor cannot name a slot's offset
// until that slot has been placed.
func reserveSlotTable(out *os.File, index *PSPFIndex, slotCount int, logger *slog.Logger) int64 {
	slotTableOffset := AlignOffset(mustSeek(out, logger), SlotAlignment)
	if _, err := out.Seek(slotTableOffset, 0); err != nil {
		logger.Error("Failed to seek to slot table", "error", err)
		buildExitFn(1)
	}

	tableOffset, err := int64ToUint64Checked(slotTableOffset, "slot table offset")
	index.SlotTableOffset = mustConvert(tableOffset, err, logger)

	count32, err := intToUint32Checked(slotCount, "slot count")
	index.SlotCount = mustConvert(count32, err, logger)

	count64, err := intToUint64Checked(slotCount, "slot count")
	count64 = mustConvert(count64, err, logger)

	tableSize, err := multiplyUint64Checked(count64, SlotDescriptorSize, "slot table size")
	index.SlotTableSize = mustConvert(tableSize, err, logger)

	tableSizeInt64, err := uint64ToInt64Checked(index.SlotTableSize, "slot table size")
	tableSizeInt64 = mustConvert(tableSizeInt64, err, logger)

	if _, err := out.Seek(slotTableOffset+tableSizeInt64, 0); err != nil {
		logger.Error("Failed to seek past slot table", "error", err)
		buildExitFn(1)
	}

	return slotTableOffset
}

// recordMetadataChecksum hashes the metadata as it was stored and records the
// digest in the index.
//
// The bytes are read back from the file rather than hashed on the way out: the
// checksum has to cover the gzip stream a reader will find, and re-compressing
// the document is not guaranteed to reproduce it byte for byte.
func recordMetadataChecksum(out *os.File, index *PSPFIndex, logger *slog.Logger) {
	savedPos := mustSeek(out, logger)

	metadataOffset, err := uint64ToInt64Checked(index.MetadataOffset, "metadata offset")
	metadataOffset = mustConvert(metadataOffset, err, logger)

	if _, err := out.Seek(metadataOffset, 0); err != nil {
		logger.Error("❌ Failed to seek to metadata position", "error", err)
		buildExitFn(1)
	}

	compressedData := make([]byte, index.MetadataSize)
	if _, err := out.Read(compressedData); err != nil {
		logger.Error("❌ Failed to read compressed metadata", "error", err)
		buildExitFn(1)
	}

	if _, err := out.Seek(savedPos, 0); err != nil {
		logger.Error("❌ Failed to restore seek position", "error", err)
		buildExitFn(1)
	}

	metadataHash := sha256.Sum256(compressedData)
	copy(index.MetadataChecksum[:], metadataHash[:])
}

// recordPackageSize sets the package size, which counts the MagicTrailer that
// has not been written yet.
func recordPackageSize(out *os.File, index *PSPFIndex, logger *slog.Logger) {
	endOfContent, err := int64ToUint64Checked(mustSeek(out, logger), "package size")
	endOfContent = mustConvert(endOfContent, err, logger)

	size, err := addUint64Checked(endOfContent, MagicTrailerSize, "package size")
	index.PackageSize = mustConvert(size, err, logger)
}
