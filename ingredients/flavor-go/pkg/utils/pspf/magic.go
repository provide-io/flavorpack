package pspf

import (
	"bytes"
)

// Common PSPF magic bytes
var (
	// PSPFMagic is the standard PSPF file identifier
	PSPFMagic = []byte("PSPF2025")
	
	// EmojiMagic is the trailing emoji sequence (📦🪄)
	EmojiMagic = []byte{
		0xF0, 0x9F, 0x93, 0xA6, // 📦 Package emoji
		0xF0, 0x9F, 0xAA, 0x84, // 🪄 Magic wand emoji
	}
)

// VerifyPSPFMagic checks if the provided data starts with PSPF magic bytes
func VerifyPSPFMagic(data []byte) bool {
	if len(data) < len(PSPFMagic) {
		return false
	}
	return bytes.Equal(data[:len(PSPFMagic)], PSPFMagic)
}

// VerifyEmojiMagic checks if the provided data matches the expected emoji magic
func VerifyEmojiMagic(data []byte) bool {
	return bytes.Equal(data, EmojiMagic)
}

// ExtractMagic safely extracts magic bytes from data at the given offset
func ExtractMagic(data []byte, offset int, size int) []byte {
	if offset < 0 || offset+size > len(data) {
		return nil
	}
	return data[offset : offset+size]
}