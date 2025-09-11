package format_2025

// =================================
// PSPF Format defaults
// =================================
const (
	// Format version
	DefaultPSPFVersion        = 0x20250001
	DefaultHeaderSize         = 8192  // Future-proof 8KB index block
	DefaultSlotDescriptorSize = 64    // Descriptor size
	DefaultMagicTrailerSize   = 8200  // Index block with markers
	DefaultSlotAlignment      = 8     // Minimum alignment

	// Platform-specific page sizes
	DefaultPageSize      = 4096 // Default for Linux/Windows
	DefaultPageSizeMacOS = 16384 // macOS, especially M1/M2
	DefaultCacheLine     = 64
	DefaultCacheLineMacOS = 128
)

// =================================
// File permissions defaults
// =================================
const (
	DefaultFilePerms       = 0o600 // Read/write for owner only
	DefaultExecutablePerms = 0o700 // Read/write/execute for owner only
	DefaultDirPerms        = 0o700 // Read/write/execute for owner only
)

// =================================
// Disk and memory defaults
// =================================
const (
	DefaultDiskSpaceMultiplier = 2               // Require 2x compressed size for extraction
	DefaultMaxMemory          = 128 * 1024 * 1024 // 128MB
	DefaultMinMemory          = 8 * 1024 * 1024   // 8MB
	DefaultChunkSize          = 64 * 1024         // 64KB for streaming
)

// =================================
// Path constants
// =================================
const (
	DefaultPSPFHiddenPrefix     = "."
	DefaultPSPFSuffix          = ".pspf"
	DefaultInstanceDir         = "instance"
	DefaultPackageDir          = "package"
	DefaultTmpDir              = "tmp"
	DefaultExtractDir          = "extract"
	DefaultLogDir              = "log"
	DefaultLockFile            = "lock"
	DefaultCompleteFile        = "complete"
	DefaultPackageChecksumFile = "package.checksum"
	DefaultPSPMetadataFile     = "psp.json"
	DefaultIndexMetadataFile   = "index.json"
)

// =================================
// Checksum algorithms
// =================================
const (
	ChecksumAdler32 = 0 // Default, fast
	ChecksumCRC32   = 1 // More robust than Adler-32
	ChecksumSHA256  = 2 // First 4 bytes of SHA256
	ChecksumXXHash  = 3 // Very fast, good distribution
)

// =================================
// Purpose types
// =================================
const (
	DefaultPurposeData   = 0 // General data files
	DefaultPurposeCode   = 1 // Executable code
	DefaultPurposeConfig = 2 // Configuration files
	DefaultPurposeMedia  = 3 // Media/assets
)

// =================================
// Lifecycle types
// =================================
const (
	// Timing-based
	DefaultLifecycleInit     = 0 // First run only, removed after initialization
	DefaultLifecycleStartup  = 1 // Extracted/executed at every startup
	DefaultLifecycleRuntime  = 2 // Available during application execution (default)
	DefaultLifecycleShutdown = 3 // Executed during cleanup/exit phase
	
	// Retention-based
	DefaultLifecycleCache     = 4 // Kept for performance, can be regenerated
	DefaultLifecycleTemporary = 5 // Removed after current session ends
	
	// Access-based
	DefaultLifecycleLazy  = 6 // Loaded on-demand, not extracted initially
	DefaultLifecycleEager = 7 // Loaded immediately on startup
	
	// Environment-based
	DefaultLifecycleDev      = 8  // Only extracted in development/debug mode
	DefaultLifecycleConfig   = 9  // User-modifiable configuration files
	DefaultLifecyclePlatform = 10 // Platform/OS specific content
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