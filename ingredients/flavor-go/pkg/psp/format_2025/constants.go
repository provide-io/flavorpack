package format_2025

var (
	// Individual emoji bytes for MagicTrailer bookends
	PackageEmojiBytes   = []byte{0xF0, 0x9F, 0x93, 0xA6} // 📦 as bytes (MagicTrailer start)
	MagicWandEmojiBytes = []byte{0xF0, 0x9F, 0xAA, 0x84} // 🪄 as bytes (MagicTrailer end)
)

const (
	PSPFVersion        = 0x20250001
	IndexSize          = 8192
	MagicTrailerSize   = 8200 // 📦 (4) + index (8192) + 🪄 (4)
	SlotAlignment      = 8    // Slots must be 8-byte aligned
	SlotDescriptorSize = 64   // Enhanced slot descriptor size

	// Default permissions (secure by default - user only)
	DefaultFilePerms       = 0600 // Read/write for owner only
	DefaultExecutablePerms = 0700 // Read/write/execute for owner only
	DefaultDirPerms        = 0700 // Read/write/execute for owner only

	// Memory limits
	DefaultMaxMemory = 128 * 1024 * 1024 // 128MB
	DefaultMinMemory = 8 * 1024 * 1024   // 8MB
	DefaultChunkSize = 64 * 1024         // 64KB for streaming

	// DiskSpaceMultiplier is the safety factor for disk space requirements
	// We require 2x the compressed size to account for extraction overhead
	DiskSpaceMultiplier = 2

	// ==================== Path Constants ====================
	// PSPFHiddenPrefix is the hidden directory prefix for metadata
	PSPFHiddenPrefix = "."

	// PSPFSuffix is the suffix for metadata directory
	PSPFSuffix = ".pspf"

	// InstanceDir is the instance metadata directory (persistent across extractions)
	InstanceDir = "instance"

	// PackageDir is the package metadata directory (replaced each extraction)
	PackageDir = "package"

	// TmpDir is the temporary extraction directory
	TmpDir = "tmp"

	// ExtractDir is the extract operations directory (under instance)
	ExtractDir = "extract"

	// LogDir is the log directory (under instance)
	LogDir = "log"

	// LockFile is the lock file name (in instance/extract/)
	LockFile = "lock"

	// CompleteFile is the completion marker file name (in instance/extract/)
	CompleteFile = "complete"

	// PackageChecksumFile is the package checksum file name (in instance/)
	PackageChecksumFile = "package.checksum"

	// PSPMetadataFile is the PSP metadata JSON file name (in package/)
	PSPMetadataFile = "psp.json"

	// IndexMetadataFile is the index metadata JSON file name (in instance/)
	IndexMetadataFile = "index.json"

	// Legacy codec constants - REMOVED
	// Use operations (OP_TAR, OP_GZIP, etc.) instead

	// Purpose types - aligned with Python naming
	PurposeData   = 0 // General data files
	PurposeCode   = 1 // Executable code
	PurposeConfig = 2 // Configuration files
	PurposeMedia  = 3 // Media/assets

	// Legacy aliases for backward compatibility
	PurposePayload = PurposeData   // Deprecated: use PurposeData
	PurposeRuntime = PurposeCode   // Deprecated: use PurposeCode
	PurposeTool    = PurposeConfig // Deprecated: use PurposeConfig

	// Lifecycle types - must match Python/Rust
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

	// Future codec formats (not implemented yet):
	// CodecZstd  = 4 // Zstd compressed single file
	// CodecTzst  = 5 // Tar archive, then zstd compressed
	// CodecBrotli = 6 // Brotli compressed single file
	// CodecTbr   = 7 // Tar archive, then brotli compressed
	// CodecZip   = 8 // Zip archive
	// Codec7z    = 9 // 7-zip archive
)
