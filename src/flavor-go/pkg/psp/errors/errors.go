package errors

import "errors"

var (
	// Format errors 📦
	ErrInvalidMagic      = errors.New("❌ invalid PSPF magic")
	ErrInvalidVersion    = errors.New("❌ unsupported PSPF version")
	ErrInvalidIndexSize  = errors.New("❌ invalid index size")
	ErrChecksumMismatch  = errors.New("❌ checksum mismatch")
	ErrInvalidEmojiMagic = errors.New("❌ invalid emoji magic")

	// Slot errors 📂
	ErrInvalidSlotIndex     = errors.New("❌ invalid slot index")
	ErrSlotExtractionFailed = errors.New("❌ slot extraction failed")

	// Security errors 🔒
	ErrIntegrityCheckFailed = errors.New("❌ integrity check failed")
	ErrSignatureInvalid     = errors.New("❌ invalid signature")
	ErrNoIntegritySeal      = errors.New("❌ no integrity seal found")

	// Execution errors 🚀
	ErrExecutionFailed = errors.New("❌ execution failed")
	ErrMissingSlot     = errors.New("❌ referenced slot missing")
)
