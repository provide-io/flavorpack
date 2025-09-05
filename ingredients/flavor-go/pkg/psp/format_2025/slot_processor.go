package format_2025

import (
	"crypto/sha256"
	"fmt"
	"hash/adler32"
	"os"
	"strconv"
	"strings"

	"github.com/hashicorp/go-hclog"
)

// SlotProcessor handles slot processing for PSPF packages.
// 
// This abstraction encapsulates all slot-related operations including loading,
// processing, and preparing slot data for package assembly. It aligns with the
// Rust and Python implementations for cross-language consistency in the PSPF/2025
// format.
//
// The processor handles:
// - Loading slot data from disk
// - Applying encoding/compression
// - Calculating checksums
// - Creating slot descriptors for the binary format
// - Creating slot metadata for the JSON metadata section
//
// Slot processing workflow:
// 1. Load manifest slots configuration
// 2. Process each slot (read, compress, checksum)
// 3. Create descriptors for binary slot table
// 4. Create metadata for JSON metadata section
// 5. Store compressed data for writing to package
type SlotProcessor struct {
	// Slots from manifest configuration
	manifestSlots []Slot

	// Processed slot descriptors for the package
	slotDescriptors []SlotDescriptor

	// Slot metadata for the metadata section
	metadataSlots []SlotMetadata

	// Compressed slot data to write
	slotData [][]byte

	// Logger for debug output
	logger hclog.Logger
}

// NewSlotProcessor creates a new slot processor
func NewSlotProcessor(slots []Slot, logger hclog.Logger) *SlotProcessor {
	return &SlotProcessor{
		manifestSlots:   slots,
		slotDescriptors: make([]SlotDescriptor, 0, len(slots)),
		metadataSlots:   make([]SlotMetadata, 0, len(slots)),
		slotData:        make([][]byte, 0, len(slots)),
		logger:          logger,
	}
}

// ProcessSlots processes all slots from the manifest.
//
// This method iterates through all configured slots, loading their data,
// applying any specified encoding, and preparing both the binary descriptors
// and JSON metadata. Each slot is validated for required fields and processed
// according to its configuration.
//
// Returns an error if any slot fails to process.
func (sp *SlotProcessor) ProcessSlots() error {
	sp.logger.Info("📦 Processing slot metadata", "count", len(sp.manifestSlots))
	sp.logger.Debug("🔍 Slot processing details", "alignment", SlotAlignment, "descriptor_size", SlotDescriptorSize)

	for i, slot := range sp.manifestSlots {
		if err := sp.processSlot(i, &slot); err != nil {
			return fmt.Errorf("failed to process slot %d: %w", i, err)
		}
	}

	return nil
}

// mapPurposeToUint8 maps purpose string to uint8 value for binary format
func mapPurposeToUint8(purpose string) uint8 {
	switch purpose {
	case "payload":
		return 0
	case "runtime":
		return 1
	case "tool":
		return 2
	default:
		return 0 // default to payload
	}
}

// mapLifecycleToUint8 maps lifecycle string to uint8 value for binary format
func mapLifecycleToUint8(lifecycle string) uint8 {
	switch lifecycle {
	// Timing-based
	case "init":
		return 0
	case "startup":
		return 1
	case "runtime":
		return 2
	case "shutdown":
		return 3
	// Retention-based
	case "cache":
		return 4
	case "temp":
		return 5
	// Access-based
	case "lazy":
		return 6
	case "eager":
		return 7
	// Environment-based
	case "dev":
		return 8
	case "config":
		return 9
	case "platform":
		return 10
	default:
		return 2 // default to runtime
	}
}

// parsePermissions parses permission string (e.g., "0755") to uint16
func parsePermissions(permStr string) uint16 {
	if permStr == "" {
		return uint16(DefaultFilePerms)
	}

	// Parse octal string (e.g., "0755" -> 0o755)
	cleaned := strings.TrimPrefix(permStr, "0")
	if parsed, err := strconv.ParseUint(cleaned, 8, 16); err == nil {
		return uint16(parsed)
	}

	return uint16(DefaultFilePerms) // fallback to default
}

// hashSlotName is defined in builder.go and reused here

// processSlot processes a single slot.
//
// This method handles the complete processing of a single slot:
// - Validates required fields (id, source, target)
// - Sets defaults for optional fields
// - Loads and encodes the slot data
// - Calculates checksums
// - Creates slot descriptor for binary format
// - Creates slot metadata for JSON format
//
// Args:
//   index: The slot index (0-based)
//   slot: The slot configuration from the manifest
//
// Returns an error if the slot cannot be processed.
func (sp *SlotProcessor) processSlot(index int, slot *Slot) error {
	// Validate required fields
	if slot.ID == "" {
		return fmt.Errorf("slot %d missing required 'id' field", index)
	}
	if slot.Source == "" {
		return fmt.Errorf("slot %d missing required 'source' field (id: %s)", index, slot.ID)
	}
	if slot.Target == "" {
		return fmt.Errorf("slot %d missing required 'target' field (id: %s)", index, slot.ID)
	}

	// Set defaults
	if slot.Resolution == "" {
		slot.Resolution = "build"
	}
	if slot.Permissions == "" {
		slot.Permissions = fmt.Sprintf("%04o", DefaultFilePerms)
	}

	// Validate slot number if provided
	if slot.Slot != nil && *slot.Slot != index {
		return fmt.Errorf("slot number mismatch: expected %d, declared %d (id: %s)",
			index, *slot.Slot, slot.ID)
	}

	sp.logger.Debug("📂 Processing slot", "index", index, "id", slot.ID,
		"source", slot.Source, "target", slot.Target)

	// Read and process slot data
	slotData, compressed, encodingMethod, err := sp.loadSlotData(slot)
	if err != nil {
		return fmt.Errorf("failed to load slot data: %w", err)
	}

	// Calculate checksum of compressed data
	checksumData := sha256.Sum256(compressed)
	checksumStr := fmt.Sprintf("sha256:%x", checksumData)

	// Create slot metadata
	slotMeta := SlotMetadata{
		Slot:        index,
		ID:          slot.ID,
		Source:      slot.Source,
		Target:      slot.Target,
		Size:        int64(len(slotData)),
		Checksum:    checksumStr,
		Encoding:    slot.Encoding,
		Purpose:     slot.Purpose,
		Lifecycle:   slot.Lifecycle,
		Resolution:  slot.Resolution,
		Permissions: slot.Permissions,
	}

	// Create slot descriptor with all required fields
	descriptor := SlotDescriptor{
		ID:             uint64(index),
		Offset:         0, // Will be set during write phase
		Size:           uint64(len(compressed)),
		OriginalSize:   uint64(len(slotData)),
		Checksum:       adler32.Checksum(compressed), // Use adler32 for descriptor
		Encoding:       encodingMethod,
		Encryption:     0, // no encryption
		Alignment:      uint16(SlotAlignment),
		Purpose:        mapPurposeToUint8(slot.Purpose),
		Lifecycle:      mapLifecycleToUint8(slot.Lifecycle),
		AccessHint:     0,   // sequential
		Priority:       128, // normal priority
		Permissions:    parsePermissions(slot.Permissions),
		Platform:       0, // all platforms
		ExtendedOffset: 0,
		ExtendedSize:   0,
	}

	// Store processed data
	sp.metadataSlots = append(sp.metadataSlots, slotMeta)
	sp.slotDescriptors = append(sp.slotDescriptors, descriptor)
	sp.slotData = append(sp.slotData, compressed)

	sp.logger.Debug("✅ Slot processed", "index", index, "id", slot.ID,
		"compressed_size", len(compressed), "original_size", len(slotData))

	return nil
}

// loadSlotData loads and processes slot data based on encoding.
//
// This method reads the slot data from disk and applies any specified
// encoding. It supports path resolution with {workenv} placeholder and
// various encoding formats (gzip, tar, tar.gz, none).
//
// Args:
//   slot: The slot configuration containing source path and encoding
//
// Returns:
//   - Original uncompressed data
//   - Compressed/encoded data
//   - Encoding method constant for the binary format
//   - Error if the data cannot be loaded
func (sp *SlotProcessor) loadSlotData(slot *Slot) ([]byte, []byte, uint8, error) {
	// Resolve {workenv} placeholder
	slotPath := slot.Source
	if strings.Contains(slotPath, "{workenv}") {
		baseDir := os.Getenv("FLAVOR_WORKENV_BASE")
		if baseDir == "" {
			baseDir, _ = os.Getwd()
		}
		slotPath = strings.ReplaceAll(slotPath, "{workenv}", baseDir)
		sp.logger.Debug("📍 Resolved path", "original", slot.Source,
			"resolved", slotPath, "base", baseDir)
	}

	// Read slot data
	slotData, err := os.ReadFile(slotPath)
	if err != nil {
		return nil, nil, 0, fmt.Errorf("failed to read slot from %s: %w", slotPath, err)
	}

	sp.logger.Debug("📊 Slot size", "original", len(slotData), "encoding", slot.Encoding)

	// Handle encoding
	var compressed []byte
	var encodingMethod uint8

	switch slot.Encoding {
	case "gzip":
		compressed = slotData
		encodingMethod = EncodingGzip
	case "tgz", "tar.gz":
		compressed = slotData
		encodingMethod = EncodingTgz
	case "tar":
		compressed = slotData
		encodingMethod = EncodingTar
	case "raw", "none", "":
		compressed = slotData
		encodingMethod = EncodingRaw
	default:
		return nil, nil, 0, fmt.Errorf("unknown encoding: %s", slot.Encoding)
	}

	return slotData, compressed, encodingMethod, nil
}

// GetDescriptors returns the processed slot descriptors
func (sp *SlotProcessor) GetDescriptors() []SlotDescriptor {
	return sp.slotDescriptors
}

// GetMetadata returns the processed slot metadata
func (sp *SlotProcessor) GetMetadata() []SlotMetadata {
	return sp.metadataSlots
}

// GetSlotData returns the compressed slot data
func (sp *SlotProcessor) GetSlotData() [][]byte {
	return sp.slotData
}
