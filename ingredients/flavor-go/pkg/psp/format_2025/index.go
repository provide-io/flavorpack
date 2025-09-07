package format_2025

import (
	"encoding/binary"
	"fmt"
)

// PSPFIndex represents the PSPF 2025 index block (8192 bytes)
type PSPFIndex struct {
	// Core identification (8 bytes)
	FormatVersion uint32 // 0x20250001
	IndexChecksum uint32 // Adler-32 of index block (with this field as 0)

	// File structure (48 bytes)
	PackageSize     uint64 // Total file size
	LauncherSize    uint64 // Size of launcher binary
	MetadataOffset  uint64 // Offset to metadata archive
	MetadataSize    uint64 // Size of metadata archive
	SlotTableOffset uint64 // Offset to slot table
	SlotTableSize   uint64 // Size of slot table

	// Slot information (8 bytes)
	SlotCount uint32 // Number of slots
	Flags     uint32 // Feature flags

	// Security (576 bytes)
	PublicKey          [32]byte  // Ed25519 public key for signature verification
	MetadataChecksum   [32]byte  // Adler-32 of compressed metadata (first 4 bytes, rest zeros)
	IntegritySignature [512]byte // Ed25519 signature of uncompressed JSON (first 64 bytes, rest zeros)

	// Performance hints (64 bytes)
	AccessMode      uint8    // 0=auto, 1=mmap, 2=file, 3=stream
	CacheStrategy   uint8    // 0=none, 1=lazy, 2=eager, 3=critical
	CodecType       uint8    // 0=raw, 1=tar, 2=gzip, 3=tgz
	EncryptionType  uint8    // 0=none, 1=aes256-gcm, 2=chacha20
	PageSize        uint32   // Optimal page size for alignment
	MaxMemory       uint64   // Suggested maximum memory usage
	MinMemory       uint64   // Minimum required memory
	CpuFeatures     uint64   // Required CPU features (bit flags)
	GpuRequirements uint64   // GPU requirements (bit flags)
	NumaHints       uint64   // NUMA topology hints
	StreamChunkSize uint32   // Optimal streaming chunk size
	Padding1        [12]byte // Alignment padding

	// Extended metadata (128 bytes)
	BuildTimestamp uint64   // Unix timestamp of build
	BuildMachine   [32]byte // Build machine identifier
	SourceHash     [32]byte // Hash of source code/inputs
	DependencyHash [32]byte // Hash of all dependencies
	LicenseID      [16]byte // SPDX license identifier
	ProvenanceURI  [8]byte  // Short URI to provenance data

	// Capabilities (32 bytes)
	Capabilities    uint64 // What this package can do
	Requirements    uint64 // What this package needs
	Extensions      uint64 // Extended features
	Compatibility   uint32 // Minimum reader version
	ProtocolVersion uint32 // Protocol version for negotiation

	// Future cryptography space (512 bytes)
	FutureCrypto [512]byte // Reserved for post-quantum signatures

	// Reserved for future use (6808 bytes)
	Reserved [6816]byte // Large buffer for future expansion
}

// Pack serializes the index to bytes
func (idx *PSPFIndex) Pack() []byte {
	buf := make([]byte, IndexSize)

	binary.LittleEndian.PutUint32(buf[0:4], idx.FormatVersion)
	binary.LittleEndian.PutUint32(buf[4:8], idx.IndexChecksum)
	binary.LittleEndian.PutUint64(buf[8:16], idx.PackageSize)
	binary.LittleEndian.PutUint64(buf[16:24], idx.LauncherSize)
	binary.LittleEndian.PutUint64(buf[24:32], idx.MetadataOffset)
	binary.LittleEndian.PutUint64(buf[32:40], idx.MetadataSize)
	binary.LittleEndian.PutUint64(buf[40:48], idx.SlotTableOffset)
	binary.LittleEndian.PutUint64(buf[48:56], idx.SlotTableSize)
	binary.LittleEndian.PutUint32(buf[56:60], idx.SlotCount)
	binary.LittleEndian.PutUint32(buf[60:64], idx.Flags)
	copy(buf[64:96], idx.PublicKey[:])
	copy(buf[96:128], idx.MetadataChecksum[:])
	copy(buf[128:640], idx.IntegritySignature[:])

	// Pack performance hints
	buf[640] = idx.AccessMode
	buf[641] = idx.CacheStrategy
	buf[642] = idx.CodecType
	buf[643] = idx.EncryptionType
	binary.LittleEndian.PutUint32(buf[644:648], idx.PageSize)
	binary.LittleEndian.PutUint64(buf[648:656], idx.MaxMemory)
	binary.LittleEndian.PutUint64(buf[656:664], idx.MinMemory)
	binary.LittleEndian.PutUint64(buf[664:672], idx.CpuFeatures)
	binary.LittleEndian.PutUint64(buf[672:680], idx.GpuRequirements)
	binary.LittleEndian.PutUint64(buf[680:688], idx.NumaHints)
	binary.LittleEndian.PutUint32(buf[688:692], idx.StreamChunkSize)
	copy(buf[692:704], idx.Padding1[:])

	// Pack extended metadata
	binary.LittleEndian.PutUint64(buf[704:712], idx.BuildTimestamp)
	copy(buf[712:744], idx.BuildMachine[:])
	copy(buf[744:776], idx.SourceHash[:])
	copy(buf[776:808], idx.DependencyHash[:])
	copy(buf[808:824], idx.LicenseID[:])
	copy(buf[824:832], idx.ProvenanceURI[:])

	// Pack capabilities
	binary.LittleEndian.PutUint64(buf[840:848], idx.Capabilities)
	binary.LittleEndian.PutUint64(buf[848:856], idx.Requirements)
	binary.LittleEndian.PutUint64(buf[856:864], idx.Extensions)
	binary.LittleEndian.PutUint32(buf[864:868], idx.Compatibility)
	binary.LittleEndian.PutUint32(buf[868:872], idx.ProtocolVersion)

	// Pack future crypto and reserved
	copy(buf[872:1384], idx.FutureCrypto[:])
	copy(buf[1384:8192], idx.Reserved[:])

	return buf
}

// Unpack deserializes the index from bytes
func (idx *PSPFIndex) Unpack(data []byte) error {
	if len(data) != IndexSize {
		return fmt.Errorf("invalid index size: %d", len(data))
	}

	idx.FormatVersion = binary.LittleEndian.Uint32(data[0:4])
	idx.IndexChecksum = binary.LittleEndian.Uint32(data[4:8])
	idx.PackageSize = binary.LittleEndian.Uint64(data[8:16])
	idx.LauncherSize = binary.LittleEndian.Uint64(data[16:24])
	idx.MetadataOffset = binary.LittleEndian.Uint64(data[24:32])
	idx.MetadataSize = binary.LittleEndian.Uint64(data[32:40])
	idx.SlotTableOffset = binary.LittleEndian.Uint64(data[40:48])
	idx.SlotTableSize = binary.LittleEndian.Uint64(data[48:56])
	idx.SlotCount = binary.LittleEndian.Uint32(data[56:60])
	idx.Flags = binary.LittleEndian.Uint32(data[60:64])
	copy(idx.PublicKey[:], data[64:96])
	copy(idx.MetadataChecksum[:], data[96:128])
	copy(idx.IntegritySignature[:], data[128:640])

	// Unpack performance hints
	idx.AccessMode = data[640]
	idx.CacheStrategy = data[641]
	idx.CodecType = data[642]
	idx.EncryptionType = data[643]
	idx.PageSize = binary.LittleEndian.Uint32(data[644:648])
	idx.MaxMemory = binary.LittleEndian.Uint64(data[648:656])
	idx.MinMemory = binary.LittleEndian.Uint64(data[656:664])
	idx.CpuFeatures = binary.LittleEndian.Uint64(data[664:672])
	idx.GpuRequirements = binary.LittleEndian.Uint64(data[672:680])
	idx.NumaHints = binary.LittleEndian.Uint64(data[680:688])
	idx.StreamChunkSize = binary.LittleEndian.Uint32(data[688:692])
	copy(idx.Padding1[:], data[692:704])

	// Unpack extended metadata
	idx.BuildTimestamp = binary.LittleEndian.Uint64(data[704:712])
	copy(idx.BuildMachine[:], data[712:744])
	copy(idx.SourceHash[:], data[744:776])
	copy(idx.DependencyHash[:], data[776:808])
	copy(idx.LicenseID[:], data[808:824])
	copy(idx.ProvenanceURI[:], data[824:832])

	// Unpack capabilities
	idx.Capabilities = binary.LittleEndian.Uint64(data[840:848])
	idx.Requirements = binary.LittleEndian.Uint64(data[848:856])
	idx.Extensions = binary.LittleEndian.Uint64(data[856:864])
	idx.Compatibility = binary.LittleEndian.Uint32(data[864:868])
	idx.ProtocolVersion = binary.LittleEndian.Uint32(data[868:872])

	// Unpack future crypto and reserved
	copy(idx.FutureCrypto[:], data[872:1384])
	copy(idx.Reserved[:], data[1384:8192])

	return nil
}

// AlignOffset aligns an offset to the specified alignment
