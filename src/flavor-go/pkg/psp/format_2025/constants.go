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

	// Purpose types - part of format spec
	PurposeData   = 0 // General data files
	PurposeCode   = 1 // Executable code
	PurposeConfig = 2 // Configuration files
	PurposeMedia  = 3 // Media/assets

	// Legacy aliases
	PurposePayload = PurposeData   // Deprecated: use PurposeData
	PurposeRuntime = PurposeCode   // Deprecated: use PurposeCode
	PurposeTool    = PurposeConfig // Deprecated: use PurposeConfig

	// Lifecycle types - part of format spec
	LifecycleInit      = 0  // First run only, removed after initialization
	LifecycleStartup   = 1  // Extracted/executed at every startup
	LifecycleRuntime   = 2  // Available during application execution (default)
	LifecycleShutdown  = 3  // Executed during cleanup/exit phase
	LifecycleCache     = 4  // Kept for performance, can be regenerated
	LifecycleTemporary = 5  // Removed after current session ends
	LifecycleLazy      = 6  // Loaded on-demand, not extracted initially
	LifecycleEager     = 7  // Loaded immediately on startup
	LifecycleDev       = 8  // Only extracted in development/debug mode
	LifecycleConfig    = 9  // User-modifiable configuration files
	LifecyclePlatform  = 10 // Platform/OS specific content
)
