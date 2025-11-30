package format_2025

// =================================
// Platform-specific defaults
// =================================
const (
	// Platform-specific page sizes
	PageSize       = 4096  // Default for Linux/Windows
	PageSizeMacOS  = 16384 // macOS, especially M1/M2
	CacheLine      = 64
	CacheLineMacOS = 128
)

// =================================
// File permissions defaults
// =================================
const (
	FilePerms       = 0o600 // Read/write for owner only
	ExecutablePerms = 0o700 // Read/write/execute for owner only
	DirPerms        = 0o700 // Read/write/execute for owner only
)

// =================================
// Disk and memory defaults
// =================================
const (
	DiskSpaceMultiplier = 2                 // Require 2x compressed size for extraction
	MaxMemory           = 128 * 1024 * 1024 // 128MB
	MinMemory           = 8 * 1024 * 1024   // 8MB
	ChunkSize           = 64 * 1024         // 64KB for streaming
)

// =================================
// Path constants
// =================================
const (
	PSPFHiddenPrefix    = "."
	PSPFSuffix          = ".pspf"
	InstanceDir         = "instance"
	PackageDir          = "package"
	TmpDir              = "tmp"
	ExtractDir          = "extract"
	LogDir              = "log"
	LockFile            = "lock"
	CompleteFile        = "complete"
	PackageChecksumFile = "package.checksum"
	PSPMetadataFile     = "psp.json"
	IndexMetadataFile   = "index.json"
)

// =================================
// Access modes
// =================================
const (
	AccessFile   = 0 // Traditional file I/O
	AccessMmap   = 1 // Memory-mapped access
	AccessAuto   = 2 // Choose based on size/system
	AccessStream = 3 // Streaming access
)

// =================================
// Cache priorities
// =================================
const (
	CacheLow      = 0 // Evict first
	CacheNormal   = 1 // Standard caching
	CacheHigh     = 2 // Keep in memory
	CacheCritical = 3 // Never evict
)

// =================================
// Access hints (bit flags)
// =================================
const (
	AccessHintSequential = 0 // Sequential access pattern
	AccessHintRandom     = 1 // Random access pattern
	AccessHintOnce       = 2 // Access once then discard
	AccessHintPrefetch   = 3 // Prefetch next slot
)

// =================================
// Capability flags
// =================================
const (
	CapabilityMmap            = 1 << 0 // Has memory-mapped support
	CapabilityPageAligned     = 1 << 1 // Page-aligned slots
	CapabilityCompressedIndex = 1 << 2 // Compressed index
	CapabilityStreaming       = 1 << 3 // Streaming-optimized
	CapabilityPrefetch        = 1 << 4 // Has prefetch hints
	CapabilityCacheAware      = 1 << 5 // Cache-aware layout
	CapabilityEncrypted       = 1 << 6 // Has encrypted slots
	CapabilitySigned          = 1 << 7 // Digitally signed
)

// =================================
// Signature algorithms
// =================================
var (
	SignatureNone    = []byte{0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00}
	SignatureED25519 = []byte("ED25519\x00")
	SignatureRSA4096 = []byte("RSA4096\x00")
)

// =================================
// Metadata formats
// =================================
var (
	MetadataJSON    = []byte("JSON\x00\x00\x00\x00")
	MetadataCBOR    = []byte("CBOR\x00\x00\x00\x00")
	MetadataMsgpack = []byte("MSGPACK\x00")
)

// =================================
// Build configuration defaults
// =================================
const (
	DefaultBuildUseIsolation = true
	DefaultBuildNoDeps       = false
	DefaultBuildResolver     = "backtracking"
)

// =================================
// Package configuration defaults
// =================================
const (
	DefaultPackageVersion = "0.0.1"
	DefaultPackageAuthor  = "Unknown"
)

// =================================
// Extraction defaults
// =================================
const (
	DefaultExtractVerify    = true
	DefaultExtractOverwrite = false
)

// =================================
// Launcher defaults
// =================================
const (
	DefaultLauncherLogLevel = "INFO"
	DefaultLauncherTimeout  = 30.0 // seconds
)

// =================================
// Validation defaults
// =================================
const (
	DefaultValidationLevel = "standard" // Default validation level
)
