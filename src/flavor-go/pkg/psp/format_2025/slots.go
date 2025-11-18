package format_2025

import (
	"crypto/sha256"
	"encoding/binary"
	"fmt"

	"github.com/hashicorp/go-hclog"
)

// HashName generates a 64-bit hash of a string for fast lookup.
// Uses first 8 bytes of SHA256 as little-endian integer.
// This matches the Python and Rust implementations.
func HashName(name string) uint64 {
	hash := sha256.Sum256([]byte(name))
	return binary.LittleEndian.Uint64(hash[:8])
}

type SlotMetadata struct {
	Slot        int    `json:"slot"`   // Position validator
	ID          string `json:"id"`     // Slot identifier
	Source      string `json:"source"` // Source path
	Target      string `json:"target"` // Destination path
	Size        int64  `json:"size"`
	Checksum    string `json:"checksum"`
	Operations  string `json:"operations"` // Operation chain (e.g., "gzip", "tar|gzip")
	Purpose     string `json:"purpose"`
	Lifecycle   string `json:"lifecycle"`
	Resolution  string `json:"resolution,omitempty"`  // When to resolve: build|runtime|lazy
	Permissions string `json:"permissions,omitempty"` // Unix permissions (e.g., "0755")
	SelfRef     *bool  `json:"self_ref,omitempty"`    // Self-referential slot (references launcher itself)
}

// SlotDescriptor is the 64-byte enhanced slot descriptor format
// Binary layout: 7 uint64 fields (56 bytes) + 8 uint8 fields (8 bytes) = 64 bytes
type SlotDescriptor struct {
	// Core fields (56 bytes total - 7x uint64)
	ID           uint64 // Unique slot identifier
	NameHash     uint64 // Hash of slot name for fast lookup
	Offset       uint64 // Byte offset in bundle
	Size         uint64 // Size as stored (possibly compressed)
	OriginalSize uint64 // Original uncompressed size
	Operations   uint64 // Packed operation chain (up to 8 ops)
	Checksum     uint64 // Checksum of stored data (32-bit value in 64-bit field)

	// Metadata fields (8 bytes total - 8x uint8)
	Purpose         uint8 // 0=data, 1=code, 2=config, 3=media
	Lifecycle       uint8 // When to extract/use
	Priority        uint8 // Cache priority hint
	Platform        uint8 // Platform requirements
	Reserved1       uint8 // Reserved for future use
	Reserved2       uint8 // Reserved for future use
	Permissions     uint8 // Unix permissions (lower 8 bits)
	PermissionsHigh uint8 // Unix permissions (upper 8 bits)
}

// SlotDescriptorSize is defined in constants.go

var slotLogger = hclog.New(&hclog.LoggerOptions{
	Name:  "pspf2025.slots",
	Level: hclog.Trace,
})

// Pack serializes the descriptor to exactly 64 bytes
func (d *SlotDescriptor) Pack() []byte {
	slotLogger.Trace("📦 Packing slot descriptor",
		"id", d.ID,
		"operations", fmt.Sprintf("0x%016x", d.Operations),
	)

	buf := make([]byte, SlotDescriptorSize)

	// Pack 7 uint64 fields (56 bytes)
	binary.LittleEndian.PutUint64(buf[0:8], d.ID)
	binary.LittleEndian.PutUint64(buf[8:16], d.NameHash)
	binary.LittleEndian.PutUint64(buf[16:24], d.Offset)
	binary.LittleEndian.PutUint64(buf[24:32], d.Size)
	binary.LittleEndian.PutUint64(buf[32:40], d.OriginalSize)
	binary.LittleEndian.PutUint64(buf[40:48], d.Operations)
	binary.LittleEndian.PutUint64(buf[48:56], d.Checksum)

	// Pack 8 uint8 fields (8 bytes)
	buf[56] = d.Purpose
	buf[57] = d.Lifecycle
	buf[58] = d.Priority
	buf[59] = d.Platform
	buf[60] = d.Reserved1
	buf[61] = d.Reserved2
	buf[62] = d.Permissions
	buf[63] = d.PermissionsHigh

	slotLogger.Debug("✅ Packed slot descriptor",
		"size", len(buf),
	)

	return buf
}

// Unpack deserializes a descriptor from 64 bytes
func UnpackSlotDescriptor(data []byte) (*SlotDescriptor, error) {
	if len(data) != SlotDescriptorSize {
		slotLogger.Error("❌ Invalid descriptor size",
			"expected", SlotDescriptorSize,
			"got", len(data),
		)
		return nil, fmt.Errorf("invalid descriptor size: expected %d, got %d", SlotDescriptorSize, len(data))
	}

	slotLogger.Trace("📂 Unpacking slot descriptor")

	d := &SlotDescriptor{
		// Unpack uint64 fields
		ID:           binary.LittleEndian.Uint64(data[0:8]),
		NameHash:     binary.LittleEndian.Uint64(data[8:16]),
		Offset:       binary.LittleEndian.Uint64(data[16:24]),
		Size:         binary.LittleEndian.Uint64(data[24:32]),
		OriginalSize: binary.LittleEndian.Uint64(data[32:40]),
		Operations:   binary.LittleEndian.Uint64(data[40:48]),
		Checksum:     binary.LittleEndian.Uint64(data[48:56]),

		// Unpack uint8 fields
		Purpose:         data[56],
		Lifecycle:       data[57],
		Priority:        data[58],
		Platform:        data[59],
		Reserved1:       data[60],
		Reserved2:       data[61],
		Permissions:     data[62],
		PermissionsHigh: data[63],
	}

	slotLogger.Debug("✅ Unpacked slot descriptor",
		"id", d.ID,
		"operations", fmt.Sprintf("0x%016x", d.Operations),
	)

	return d, nil
}

// GetPermissions returns the full 16-bit permissions value
func (d *SlotDescriptor) GetPermissions() uint16 {
	return uint16(d.Permissions) | (uint16(d.PermissionsHigh) << 8)
}

// SetPermissions sets the 16-bit permissions value
func (d *SlotDescriptor) SetPermissions(perms uint16) {
	d.Permissions = uint8(perms & 0xFF)
	d.PermissionsHigh = uint8(perms >> 8)
}
