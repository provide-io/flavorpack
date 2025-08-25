package format_2025

var (
	// PSPF 2025 constants - XOR encoded to prevent literal string from appearing in binary
	// This is the magic bytes XORed with 0x20 to prevent string from appearing in binary
	PSPFMagic = decodeMagic()
)

func decodeMagic() []byte {
	// XOR-encoded magic: each byte XORed with 0x20
	encoded := []byte{0x70, 0x73, 0x70, 0x66, 0x12, 0x10, 0x12, 0x15}
	magic := make([]byte, 8)
	for i, b := range encoded {
		magic[i] = b ^ 0x20
	}
	return magic
}

const (
	PSPFVersion        = 0x20250001
	IndexSize          = 8192
	EmojiMagicSize     = 8  // Package + magic wand emojis (8 bytes)
	SlotAlignment      = 8  // Slots must be 8-byte aligned
	SlotDescriptorSize = 64 // Enhanced slot descriptor size
	
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

	// Future encoding formats (not implemented yet):
	// EncodingZstd  = 4 // Zstd compressed single file
	// EncodingTzst  = 5 // Tar archive, then zstd compressed
	// EncodingBrotli = 6 // Brotli compressed single file
	// EncodingTbr   = 7 // Tar archive, then brotli compressed
	// EncodingZip   = 8 // Zip archive
	// Encoding7z    = 9 // 7-zip archive
)
