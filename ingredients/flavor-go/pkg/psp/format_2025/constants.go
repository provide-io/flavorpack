package format_2025

// Core format constants that never change
// For defaults and configuration, see defaults.go

var (
	// Individual emoji bytes for MagicTrailer bookends
	PackageEmojiBytes   = []byte{0xF0, 0x9F, 0x93, 0xA6} // 📦 as bytes (MagicTrailer start)
	MagicWandEmojiBytes = []byte{0xF0, 0x9F, 0xAA, 0x84} // 🪄 as bytes (MagicTrailer end)
)

const (
	// Format version - immutable
	PSPFVersion = 0x20250001
	
	// Fixed sizes - part of the format specification
	IndexSize          = 8192 // Index block size
	MagicTrailerSize   = 8200 // 📦 (4) + index (8192) + 🪄 (4)
	SlotAlignment      = 8    // Slots must be 8-byte aligned
	SlotDescriptorSize = 64   // Slot descriptor size
)
