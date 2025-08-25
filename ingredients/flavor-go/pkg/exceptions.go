package pkg

import "errors"

var (
	// Security errors 🔒
	ErrIntegrityCheckFailed = errors.New("❌ integrity check failed")
	ErrSignatureInvalid     = errors.New("❌ invalid signature")
	ErrNoIntegritySeal      = errors.New("❌ no integrity seal found")
)
