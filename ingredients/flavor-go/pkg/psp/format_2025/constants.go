package format_2025

import (
	"github.com/provide-io/flavor/go/flavor/pkg/utils"
)

var (
	// Raw magic bytes (not exported, only for encoding)
	pspfMagicRaw      = []byte("PSPF2025")
	packageEmojiRaw   = []byte{0xF0, 0x9F, 0x93, 0xA6} // 📦
	magicWandEmojiRaw = []byte{0xF0, 0x9F, 0xAA, 0x84} // 🪄
	trailingMagicRaw  = append(packageEmojiRaw, magicWandEmojiRaw...)

	// XOR'd constants (prevents literals in binary)
	PSPFMagicEncoded     = utils.XOREncodeDefault(pspfMagicRaw)
	TrailingMagicEncoded = utils.XOREncodeDefault(trailingMagicRaw)

	// Decoded values for runtime use
	PSPFMagic     = utils.XORDecodeDefault(PSPFMagicEncoded)
	TrailingMagic = utils.XORDecodeDefault(TrailingMagicEncoded)
)

const (
	PSPFVersion        = 0x20250001
	IndexSize          = 8192
	MagicTrailerSize   = 16 // 8-byte index pointer + 8-byte emoji magic
	SlotAlignment      = 8  // Slots must be 8-byte aligned
	SlotDescriptorSize = 64 // Enhanced slot descriptor size
	
	// Default permissions (secure by default - user only)
	DefaultFilePerms       = 0600  // Read/write for owner only
	DefaultExecutablePerms = 0700  // Read/write/execute for owner only
	DefaultDirPerms        = 0700  // Read/write/execute for owner only
	
	// Memory limits
	DefaultMaxMemory = 128 * 1024 * 1024  // 128MB
	DefaultMinMemory = 8 * 1024 * 1024    // 8MB
	DefaultChunkSize = 64 * 1024          // 64KB for streaming
	
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

	// Encoding types - describe the actual format of slot data
	EncodingRaw  = 0 // Raw uncompressed data
	EncodingTar  = 1 // Uncompressed tar archive
	EncodingGzip = 2 // Gzipped single file
	EncodingTgz  = 3 // Tar archive, then gzipped (tar.gz)
	
	// Purpose types
	PurposePayload = 0 // Payload/data files
	PurposeRuntime = 1 // Runtime/executable code
	PurposeTool    = 2 // Tool/configuration files
	
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

	// Future encoding formats (not implemented yet):
	// EncodingZstd  = 4 // Zstd compressed single file
	// EncodingTzst  = 5 // Tar archive, then zstd compressed
	// EncodingBrotli = 6 // Brotli compressed single file
	// EncodingTbr   = 7 // Tar archive, then brotli compressed
	// EncodingZip   = 8 // Zip archive
	// Encoding7z    = 9 // 7-zip archive
)
