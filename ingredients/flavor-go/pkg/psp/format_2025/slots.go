package format_2025

type SlotMetadata struct {
	Slot        int    `json:"slot"`                     // Position validator
	ID          string `json:"id"`                       // Slot identifier
	Source      string `json:"source"`                   // Source path
	Target      string `json:"target"`                   // Destination path
	Size        int64  `json:"size"`
	Checksum    string `json:"checksum"`
	Encoding    string `json:"encoding"`
	Purpose     string `json:"purpose"`
	Lifecycle   string `json:"lifecycle"`
	Resolution  string `json:"resolution,omitempty"`     // When to resolve: build|runtime|lazy
	Permissions string `json:"permissions,omitempty"`   // Unix permissions (e.g., "0755")
}

// SlotDescriptor is the 64-byte enhanced slot descriptor format
type SlotDescriptor struct {
	// Identity (16 bytes)
	ID       uint64 // 8 bytes: slot ID
	NameHash uint64 // 8 bytes: hash of slot name

	// Location (16 bytes)
	Offset uint64 // 8 bytes: where slot data starts
	Size   uint64 // 8 bytes: size of data as stored (compressed)

	// Properties (16 bytes)
	OriginalSize uint64 // 8 bytes: uncompressed size
	Checksum     uint32 // 4 bytes: adler32 of stored data
	Encoding     uint8  // 1 byte: 0=raw, 1=tar, 2=gzip, 3=tgz
	Encryption   uint8  // 1 byte: encryption type
	Alignment    uint16 // 2 bytes: alignment requirement

	// Semantics (8 bytes)
	Purpose     uint8  // 1 byte: 0=data, 1=code, 2=config, 3=media
	Lifecycle   uint8  // 1 byte: lifecycle stage
	AccessHint  uint8  // 1 byte: access pattern hint
	Priority    uint8  // 1 byte: cache priority
	Permissions uint16 // 2 bytes: unix-style permissions
	Platform    uint16 // 2 bytes: platform filter

	// Extended (8 bytes)
	ExtendedOffset uint32 // 4 bytes: extended metadata offset
	ExtendedSize   uint32 // 4 bytes: extended metadata size
}

