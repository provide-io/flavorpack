package format_2025

import (
	"bytes"
	"compress/gzip"
	"crypto/ed25519"
	"fmt"
	"io"
)

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

	// Verify magic sequence
	// Check emoji magic (last 8 bytes of trailer = last 8 bytes of file)
	emojiMagic := trailer[len(trailer)-8:]
	expectedEmoji := []byte{0xF0, 0x9F, 0x93, 0xA6, 0xF0, 0x9F, 0xAA, 0x84} // 📦🪄

	if !bytes.Equal(emojiMagic, expectedEmoji) {
		return false, ErrInvalidEmojiMagic
	}

	return true, nil
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
