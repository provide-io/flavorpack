package format_2025

import (
	"bytes"
	"crypto/ed25519"
	cryptorand "crypto/rand"
	"crypto/sha256"
	"encoding/binary"
	"encoding/json"
	"fmt"
	"hash/adler32"
	"io"
	"math"
	"os"
	"os/exec"
	"path/filepath"
	"runtime"
	"strconv"
	"strings"
	"time"

	"github.com/hashicorp/go-hclog"
	"github.com/provide-io/flavor/go/flavor/pkg/logging"
)

var (
	embedPSPFAsResourceImpl = EmbedPSPFAsResource
	atomicReplaceImpl       = atomicReplace
)

// BuildWithLogLevel builds a PSPF package with explicit log level control
func BuildWithLogLevel(manifestPath, outputPath, launcherBin, privateKeyPath, publicKeyPath, keySeed, cliLogLevel string) {
	// Determine log level and source
	var logLevel string
	var logSource string

	if cliLogLevel != "" {
		logLevel = cliLogLevel
		logSource = "CLI --log-level"
	} else if envLevel := os.Getenv(EnvBuilderLogLevel); envLevel != "" {
		logLevel = envLevel
		logSource = EnvBuilderLogLevel
	} else if envLevel := os.Getenv(EnvLogLevel); envLevel != "" {
		logLevel = envLevel
		logSource = EnvLogLevel
	} else {
		logLevel = "info"
		logSource = "default"
	}

	// Parse JSON format from log level
	jsonFormat := false
	actualLevel := logLevel
	if strings.HasPrefix(logLevel, "json") {
		jsonFormat = true
		parts := strings.Split(logLevel, ":")
		if len(parts) > 1 {
			actualLevel = parts[1]
		} else {
			actualLevel = "info"
		}
	}

	// Configure logger
	var output io.Writer = os.Stderr

	// Support log file output
	if logPath := os.Getenv(EnvLogPath); logPath != "" {
		if file, err := openFileValidated(logPath, os.O_CREATE|os.O_WRONLY|os.O_APPEND, os.FileMode(FilePerms)); err == nil {
			defer func() { _ = file.Close() }()
			output = file
		}
	}

	// Add 🐹 prefix to non-JSON output
	if !jsonFormat {
		output = logging.NewPrefixWriter("🐹 ", output)
	}

	logger := hclog.New(&hclog.LoggerOptions{
		Name:       "flavor-go-builder",
		Level:      hclog.LevelFromString(actualLevel),
		JSONFormat: jsonFormat,
		Output:     output,
		TimeFormat: "2006-01-02T15:04:05Z", // UTC ISO format without timezone
		TimeFn: func() time.Time {
			return time.Now().UTC() // Force UTC time
		},
	})

	// Log startup messages
	logger.Info("🐹🐹🐹 Hello from Flavor's Go Builder 🐹🐹🐹")
	logger.Debug("Log level", "level", actualLevel, "source", logSource)
	logger.Info("PSPF Go Builder starting...")

	// Continue with normal build process
	buildImpl(logger, manifestPath, outputPath, launcherBin, privateKeyPath, publicKeyPath, keySeed)
}

// BuildWithOptions builds a PSPF package with full control over key generation
func BuildWithOptions(manifestPath, outputPath, launcherBin, privateKeyPath, publicKeyPath, keySeed string) {
	BuildWithLogLevel(manifestPath, outputPath, launcherBin, privateKeyPath, publicKeyPath, keySeed, "")
}

var buildImpl = doBuild

// doBuild performs the actual build
func doBuild(logger hclog.Logger, manifestPath, outputPath, launcherBin, privateKeyPath, publicKeyPath, keySeed string) {

	// Read manifest
	manifestData, err := readFileValidated(manifestPath)
	if err != nil {
		logger.Error("❌ Failed to read manifest", "error", err)
		os.Exit(1)
	}

	var config BuildOptions
	if err := json.Unmarshal(manifestData, &config); err != nil {
		logger.Error("❌ Failed to parse manifest", "error", err)
		os.Exit(1)
	}

	// 🚀 Get launcher binary path
	// Priority: 1. Command-line arg, 2. FLAVOR_LAUNCHER_BIN env var
	launcherPath := launcherBin
	if launcherPath == "" {
		launcherPath = getLauncherPath("")
	}
	if launcherPath == "" {
		logger.Error("❌ Launcher binary path must be specified via --launcher-bin or FLAVOR_LAUNCHER_BIN environment variable")
		os.Exit(1)
	}
	logger.Info("🚀 Loading launcher", "path", launcherPath)

	// Check launcher version
	versionCmd := exec.Command(launcherPath, "--version") // #nosec G204 -- launcherPath is operator-supplied and executed directly without shell expansion for a version probe.
	versionOutput, err := versionCmd.CombinedOutput()
	if err != nil {
		logger.Warn("⚠️ Failed to get launcher version", "error", err)
	} else {
		versionStr := strings.TrimSpace(string(versionOutput))
		logger.Info("🔍 Launcher version", "version", versionStr)
	}

	logger.Debug("🔍 Launcher path", "path", launcherPath)
	launcherData, err := readFileValidated(launcherPath)
	if err != nil {
		logger.Error("❌ Failed to read launcher", "error", err, "path", launcherPath)
		os.Exit(1)
	}
	logger.Debug("✅ Launcher loaded", "size", len(launcherData))

	// Process launcher for Windows PE compatibility if needed
	launcherData, err = ProcessLauncherForPSPF(launcherData, logger)
	if err != nil {
		logger.Error("❌ Failed to process launcher for PSPF", "error", err)
		os.Exit(1)
	}
	logger.Debug("✅ Launcher processed for PSPF", "size", len(launcherData))

	// 📁 Create output directory if it doesn't exist
	outputDir := filepath.Dir(outputPath)
	logger.Debug("📁 Ensuring output directory exists", "dir", outputDir)
	if err := os.MkdirAll(outputDir, os.FileMode(DirPerms)); err != nil {
		logger.Error("❌ Failed to create output directory", "error", err, "dir", outputDir)
		os.Exit(1)
	}

	// 💾 Create output file with executable permissions
	logger.Debug("💾 Creating output file", "path", outputPath)
	out, err := openFileValidated(outputPath, os.O_RDWR|os.O_CREATE|os.O_TRUNC, os.FileMode(ExecutablePerms))
	if err != nil {
		logger.Error("❌ Failed to create output file", "error", err)
		os.Exit(1)
	}
	// Note: NOT using defer - we close explicitly before PE resource embedding
	// to avoid file locking issues on Windows ARM64

	// ✍️ Write launcher
	logger.Debug("✍️ Writing launcher to output", "size", len(launcherData))
	if _, err := out.Write(launcherData); err != nil {
		logger.Error("❌ Failed to write launcher", "error", err)
		os.Exit(1)
	}
	launcherSize := int64(len(launcherData))

	// 📦 Create index
	logger.Debug("📦 Creating PSPF index")
	index := &PSPFIndex{
		FormatVersion: PSPFVersion,
		LauncherSize:  uint64(launcherSize),
	}
	logger.Debug("📈 Index details", "format", "PSPF2025", "version", fmt.Sprintf("0x%08x", index.FormatVersion), "launcher_size", index.LauncherSize)

	// 🔐 Get or generate Ed25519 keys
	var publicKey ed25519.PublicKey
	var privateKey ed25519.PrivateKey

	if privateKeyPath != "" {
		// Priority 1: Load keys from files
		logger.Debug("🔐 Loading keys from files", "private", privateKeyPath, "public", publicKeyPath)
		privateKey, publicKey, err = loadKeysFromFiles(privateKeyPath, publicKeyPath)
		if err != nil {
			logger.Error("❌ Failed to load keys", "error", err)
			os.Exit(1)
		}
		logger.Info("🔑 Using provided keys")
	} else if keySeed != "" {
		// Priority 2: Use deterministic seed
		logger.Debug("🔐 Generating deterministic key pair from seed")

		// Allow seed from environment variable
		actualSeed := keySeed
		if keySeed == "env" {
			actualSeed = os.Getenv(EnvKeySeed)
			if actualSeed == "" {
				logger.Error("❌ FLAVOR_KEY_SEED environment variable not set")
				os.Exit(1)
			}
		}

		seed := sha256.Sum256([]byte(actualSeed))
		privateKey = ed25519.NewKeyFromSeed(seed[:])
		publicKey = privateKey.Public().(ed25519.PublicKey)
		logger.Info("🔑 Using seed-based key generation", "seed_hash", fmt.Sprintf("%x", seed[:8]))
	} else {
		// Priority 3: Generate random ephemeral keys
		logger.Debug("🔐 Generating random ephemeral key pair")
		publicKey, privateKey, err = ed25519.GenerateKey(cryptorand.Reader)
		if err != nil {
			logger.Error("❌ Failed to generate ephemeral keys", "error", err)
			os.Exit(1)
		}
		logger.Debug("🎲 Using random key generation")
	}
	copy(index.PublicKey[:], publicKey[:32])

	// Build metadata
	var buildTimestamp string
	var buildHost string

	// Check for SOURCE_DATE_EPOCH for reproducible timestamps
	if epochStr := os.Getenv("SOURCE_DATE_EPOCH"); epochStr != "" {
		if epochInt, err := strconv.ParseInt(epochStr, 10, 64); err == nil {
			buildTimestamp = time.Unix(epochInt, 0).UTC().Format(time.RFC3339)
		} else {
			buildTimestamp = time.Now().UTC().Format(time.RFC3339)
		}
		buildHost = fmt.Sprintf("%s/%s", runtime.GOOS, runtime.GOARCH)
	} else {
		hostname, err := os.Hostname()
		buildTimestamp = time.Now().UTC().Format(time.RFC3339)
		if err != nil {
			logger.Warn("⚠️ Failed to resolve hostname, using platform-only build host", "error", err)
			buildHost = fmt.Sprintf("%s/%s", runtime.GOOS, runtime.GOARCH)
		} else {
			buildHost = fmt.Sprintf("%s/%s %s", runtime.GOOS, runtime.GOARCH, hostname)
		}
	}

	// Convert cache validation config if present
	var cacheValidation *CacheValidationInfo
	if config.CacheValidation != nil {
		cacheValidation = &CacheValidationInfo{
			CheckFile:       config.CacheValidation.CheckFile,
			ExpectedContent: config.CacheValidation.ExpectedContent,
		}
	}

	// Convert runtime config if present
	var runtimeInfo *RuntimeInfo
	if config.Runtime != nil {
		runtimeInfo = &RuntimeInfo{
			Env: config.Runtime.Env,
		}
	}

	metadata := &Metadata{
		Format: "PSPF/2025",
		Package: PackageInfo{
			Name:        config.Package.Name,
			Version:     config.Package.Version,
			Description: config.Package.Description,
		},
		CacheValidation: cacheValidation,
		SetupCommands:   config.SetupCommands,
		Slots:           []SlotMetadata{},
		Execution: &ExecutionInfo{
			PrimarySlot: config.Execution.PrimarySlot,
			Command:     config.Execution.Command,
			Environment: config.Execution.Environment,
		},
		Runtime: runtimeInfo,
		Verification: &VerificationInfo{
			IntegritySeal: IntegritySealInfo{
				Required:  true,
				Algorithm: "ed25519",
			},
		},
		Build: &BuildInfo{
			Tool:          "flavor-go",
			ToolVersion:   "1.0.0",
			Timestamp:     buildTimestamp,
			Deterministic: false,
			Platform: PlatformInfo{
				OS:   runtime.GOOS,
				Arch: runtime.GOARCH,
				Host: buildHost,
			},
		},
	}

	// 📦 Process slots using SlotProcessor (aligns with Rust implementation)
	slotProcessor := NewSlotProcessor(config.Slots, logger)
	if err := slotProcessor.ProcessSlots(); err != nil {
		logger.Error("❌ Failed to process slots", "error", err)
		os.Exit(1)
	}

	// Get processed data from SlotProcessor
	slotDescriptors := slotProcessor.GetDescriptors()
	slotDataToWrite := slotProcessor.GetSlotData()
	slotMetadataList := slotProcessor.GetMetadata()

	// Add slot metadata to package metadata
	metadata.Slots = slotMetadataList

	// 📜 Create and write metadata (gzipped JSON) - RIGHT AFTER LAUNCHER
	metadataPos, err := out.Seek(0, io.SeekCurrent)
	if err != nil {
		logger.Error("❌ Failed to get file position", "error", err)
		os.Exit(1)
	}
	logger.Debug("📜 Writing metadata (gzipped JSON)", "position", metadataPos)
	metadataSize, signature, err := writeMetadata(out, metadata, privateKey, publicKey)
	if err != nil {
		logger.Error("❌ Failed to write metadata", "error", err)
		os.Exit(1)
	}
	logger.Debug("✅ Metadata written", "size", metadataSize)

	index.MetadataOffset, err = int64ToUint64Checked(metadataPos, "metadata offset")
	if err != nil {
		logger.Error("❌ Failed to convert metadata offset", "error", err)
		os.Exit(1)
	}
	index.MetadataSize, err = intToUint64Checked(metadataSize, "metadata size")
	if err != nil {
		logger.Error("❌ Failed to convert metadata size", "error", err)
		os.Exit(1)
	}

	// Write slot table
	currentPos, err := out.Seek(0, io.SeekCurrent)
	if err != nil {
		logger.Error("❌ Failed to get file position", "error", err)
		os.Exit(1)
	}
	slotTableOffset := AlignOffset(currentPos, SlotAlignment)
	if _, err := out.Seek(slotTableOffset, 0); err != nil {
		logger.Error("Failed to seek to slot table", "error", err)
		os.Exit(1)
	}

	index.SlotTableOffset, err = int64ToUint64Checked(slotTableOffset, "slot table offset")
	if err != nil {
		logger.Error("❌ Failed to convert slot table offset", "error", err)
		os.Exit(1)
	}
	index.SlotCount, err = intToUint32Checked(len(slotDescriptors), "slot count")
	if err != nil {
		logger.Error("❌ Failed to convert slot count", "error", err)
		os.Exit(1)
	}
	slotCount64, err := intToUint64Checked(len(slotDescriptors), "slot count")
	if err != nil {
		logger.Error("❌ Failed to convert slot count", "error", err)
		os.Exit(1)
	}
	index.SlotTableSize, err = multiplyUint64Checked(slotCount64, SlotDescriptorSize, "slot table size")
	if err != nil {
		logger.Error("❌ Failed to calculate slot table size", "error", err)
		os.Exit(1)
	}

	// Reserve space for slot table (we'll write it after calculating slot offsets)
	slotTableSizeInt64, err := uint64ToInt64Checked(index.SlotTableSize, "slot table size")
	if err != nil {
		logger.Error("❌ Failed to convert slot table size", "error", err)
		os.Exit(1)
	}
	if _, err := out.Seek(slotTableOffset+slotTableSizeInt64, 0); err != nil {
		logger.Error("Failed to seek past slot table", "error", err)
		os.Exit(1)
	}

	// Now write the actual slot data and update descriptors with correct offsets
	for i, compressed := range slotDataToWrite {
		// Skip empty data (self-referential slots)
		if len(compressed) == 0 {
			logger.Debug("⏭️  Skipping slot (self-referential, no data)", "index", i)
			slotDescriptors[i].Offset = 0 // No offset for self-ref slots
			continue
		}

		// Align position
		currentPos, err := out.Seek(0, io.SeekCurrent)
		if err != nil {
			logger.Error("❌ Failed to get file position", "error", err)
			os.Exit(1)
		}
		alignedPos := AlignOffset(currentPos, SlotAlignment)
		if alignedPos > currentPos {
			padding := make([]byte, alignedPos-currentPos)
			if _, err := out.Write(padding); err != nil {
				logger.Error("Failed to write padding", "error", err)
				os.Exit(1)
			}
		}

		// Write slot data
		slotOffset := alignedPos
		slotOffsetUint64, err := int64ToUint64Checked(slotOffset, "slot offset")
		if err != nil {
			logger.Error("❌ Failed to convert slot offset", "error", err)
			os.Exit(1)
		}
		slotDescriptors[i].Offset = slotOffsetUint64
		logger.Debug("✍️ Writing slot", "id", i, "offset", slotOffset, "size", len(compressed))
		if _, err := out.Write(compressed); err != nil {
			logger.Error("❌ Failed to write slot", "error", err)
			os.Exit(1)
		}
	}

	// Go back and write the slot table with correct offsets
	endOfSlots, err := out.Seek(0, io.SeekCurrent)
	if err != nil {
		logger.Error("❌ Failed to get file position", "error", err)
		os.Exit(1)
	}
	if _, err := out.Seek(slotTableOffset, 0); err != nil {
		logger.Error("Failed to seek to slot table for writing", "error", err)
		os.Exit(1)
	}

	// Write 64-byte slot descriptors
	for _, desc := range slotDescriptors {
		if err := binary.Write(out, binary.LittleEndian, desc); err != nil {
			logger.Error("Failed to write slot descriptor", "error", err)
			os.Exit(1)
		}
	}

	// Return to end of file
	if _, err := out.Seek(endOfSlots, 0); err != nil {
		logger.Error("Failed to seek to end", "error", err)
		os.Exit(1)
	}

	// Store signature in index (first 64 bytes of 512-byte field)
	copy(index.IntegritySignature[:64], signature)

	// Calculate metadata checksum (SHA-256 of compressed data)
	// Need to seek back and read the compressed data
	savedPos, err := out.Seek(0, io.SeekCurrent)
	if err != nil {
		logger.Error("❌ Failed to get file position", "error", err)
		os.Exit(1)
	}
	if _, err := out.Seek(int64(metadataPos), 0); err != nil {
		logger.Error("❌ Failed to seek to metadata position", "error", err)
		os.Exit(1)
	}
	compressedData := make([]byte, metadataSize)
	if _, err := out.Read(compressedData); err != nil {
		logger.Error("❌ Failed to read compressed metadata", "error", err)
		os.Exit(1)
	}
	if _, err := out.Seek(savedPos, 0); err != nil {
		logger.Error("❌ Failed to restore seek position", "error", err)
		os.Exit(1)
	}

	// Compute full SHA-256 checksum (32 bytes)
	metadataHash := sha256.Sum256(compressedData)
	copy(index.MetadataChecksum[:], metadataHash[:])

	// Update package size before writing MagicTrailer
	// (add 8200 for the trailer that will be written)
	currentPos, err = out.Seek(0, io.SeekCurrent)
	if err != nil {
		logger.Error("❌ Failed to get file position", "error", err)
		os.Exit(1)
	}
	currentPosUint64, err := int64ToUint64Checked(currentPos, "package size")
	if err != nil {
		logger.Error("❌ Failed to convert package size", "error", err)
		os.Exit(1)
	}
	index.PackageSize, err = addUint64Checked(currentPosUint64, MagicTrailerSize, "package size")
	if err != nil {
		logger.Error("❌ Failed to calculate package size", "error", err)
		os.Exit(1)
	}

	// 🔐 Calculate index checksum (with checksum field as 0)
	indexData := index.Pack()
	// Set checksum field to 0 for calculation
	binary.LittleEndian.PutUint32(indexData[12:16], 0)
	checksum := adler32.Checksum(indexData)
	index.IndexChecksum = checksum
	logger.Debug("🔐 Index checksum calculated", "checksum", fmt.Sprintf("0x%08x", checksum))

	// 🪄 Write MagicTrailer (8200 bytes: 📦 + index + 🪄)
	logger.Debug("🪄 Writing MagicTrailer")

	// Write package emoji (4 bytes)
	if _, err := out.Write(PackageEmojiBytes); err != nil {
		logger.Error("❌ Failed to write package emoji", "error", err)
		os.Exit(1)
	}

	// Write index (8192 bytes)
	if _, err := out.Write(index.Pack()); err != nil {
		logger.Error("❌ Failed to write index", "error", err)
		os.Exit(1)
	}

	// Write magic wand emoji (4 bytes)
	if _, err := out.Write(MagicWandEmojiBytes); err != nil {
		logger.Error("❌ Failed to write magic wand emoji", "error", err)
		os.Exit(1)
	}

	logger.Info("✅ Successfully built PSPF bundle",
		"output", outputPath,
		"package", config.Package.Name,
		"version", config.Package.Version,
		"launcher", config.Launcher,
		"slots", len(config.Slots),
		"size", fmt.Sprintf("%.2f MB", float64(index.PackageSize)/(1024*1024)))
	logger.Debug("📦 Package details",
		"checksum", fmt.Sprintf("0x%08x", index.IndexChecksum),
		"metadata_size", index.MetadataSize,
		"slot_table_size", index.SlotTableSize)

	// 🔧 Make the output file executable
	if err := os.Chmod(outputPath, os.FileMode(ExecutablePerms)); err != nil { // #nosec G302 -- the builder output must remain executable.
		logger.Error("❌ Failed to make output executable", "error", err)
		os.Exit(1)
	}
	logger.Debug("🔧 Set executable permissions on output file")

	// ⚠️ CRITICAL: Close the file BEFORE PE resource embedding on Windows
	// On Windows ARM64, file locks prevent atomic replacement if file is still open
	// This prevents "Access is denied" errors during PE resource embedding
	if err := out.Close(); err != nil {
		logger.Error("Failed to close output file before PE embedding", "error", err)
		os.Exit(1)
	}
	logger.Debug("Closed output file before PE embedding")

	// 🪟 Windows + Go Launcher: Convert append to resource embedding
	// For Windows Go launchers, we need to embed PSPF as a PE resource instead of appending
	// This is because Windows rejects modified Go binaries (with appended data)
	if shouldUseResourceEmbedding(launcherData, logger) {
		logger.Info("🪟 Converting to PE resource embedding (Windows Go launcher)")

		if err := convertToResourceEmbedding(outputPath, launcherSize, logger); err != nil {
			logger.Error("❌ Failed to convert to resource embedding", "error", err)
			os.Exit(1)
		}

		logger.Info("✅ Successfully embedded PSPF as PE resource")
	}
}

// shouldUseResourceEmbedding determines if we should use PE resource embedding
// instead of appending PSPF data to the file.
//
// Resource embedding is required for Windows Go launchers because Windows
// rejects Go binaries with appended data.
func shouldUseResourceEmbedding(launcherData []byte, logger hclog.Logger) bool {
	return shouldUseResourceEmbeddingForOS(runtime.GOOS, launcherData, logger)
}

func shouldUseResourceEmbeddingForOS(goos string, launcherData []byte, logger hclog.Logger) bool {
	return shouldUseResourceEmbeddingForPlatform(goos, GetLauncherType(launcherData, logger), logger)
}

func shouldUseResourceEmbeddingForPlatform(goos, launcherType string, logger hclog.Logger) bool {
	// Only on Windows
	if goos != "windows" {
		logger.Debug("Not Windows, using append mode")
		return false
	}

	logger.Debug("Launcher type detected", "type", launcherType, "os", goos)

	// Use resource embedding for Go launchers on Windows
	if launcherType == "go" {
		logger.Info("Windows Go launcher detected, will use PE resource embedding")
		return true
	}

	logger.Debug("Not a Go launcher, using append mode", "type", launcherType)
	return false
}

// adjustPSPFOffsets patches the PSPF data so that all absolute offsets are relative to the
// start of the PSPF blob itself (byte 0), rather than the start of the original combined
// launcher+PSPF file. This is required when the PSPF is extracted from a PE resource and
// written to a standalone temp file: without adjustment, seeks to MetadataOffset,
// SlotTableOffset, and slot data offsets would all land past end-of-file.
func adjustPSPFOffsets(pspfData []byte, launcherSize int64, logger hclog.Logger) ([]byte, error) {
	if int64(len(pspfData)) < MagicTrailerSize {
		return nil, fmt.Errorf("PSPF data too small: %d < %d", len(pspfData), MagicTrailerSize)
	}

	data := make([]byte, len(pspfData))
	copy(data, pspfData)

	trailerStart := int64(len(data)) - MagicTrailerSize
	trailer := data[trailerStart:]

	if !bytes.Equal(trailer[:4], PackageEmojiBytes) {
		return nil, fmt.Errorf("invalid MagicTrailer: missing 📦 at start")
	}
	if !bytes.Equal(trailer[MagicTrailerSize-4:], MagicWandEmojiBytes) {
		return nil, fmt.Errorf("invalid MagicTrailer: missing 🪄 at end")
	}

	index := &PSPFIndex{}
	if err := index.Unpack(trailer[4 : 4+IndexSize]); err != nil {
		return nil, fmt.Errorf("failed to unpack index: %w", err)
	}

	logger.Debug("Adjusting PSPF offsets for PE resource embedding",
		"launcher_size", launcherSize,
		"metadata_offset_before", index.MetadataOffset,
		"slot_table_offset_before", index.SlotTableOffset)

	// Patch each slot descriptor's Offset in the slot table
	slotTableOffset, err := uint64ToInt64Checked(index.SlotTableOffset, "slot table offset")
	if err != nil {
		return nil, fmt.Errorf("failed to convert slot table offset: %w", err)
	}
	if launcherSize > slotTableOffset {
		return nil, fmt.Errorf("launcher size exceeds slot table offset: launcher=%d offset=%d", launcherSize, slotTableOffset)
	}
	launcherSizeUint64, err := int64ToUint64Checked(launcherSize, "launcher size")
	if err != nil {
		return nil, fmt.Errorf("failed to convert launcher size: %w", err)
	}
	slotTableStart := slotTableOffset - launcherSize
	for i := 0; i < int(index.SlotCount); i++ {
		descStart := slotTableStart + int64(i)*int64(SlotDescriptorSize)
		if descStart < 0 || descStart+int64(SlotDescriptorSize) > int64(len(data)) {
			return nil, fmt.Errorf("slot descriptor %d out of bounds: start=%d", i, descStart)
		}
		desc, err := UnpackSlotDescriptor(data[descStart : descStart+int64(SlotDescriptorSize)])
		if err != nil {
			return nil, fmt.Errorf("failed to unpack slot descriptor %d: %w", i, err)
		}
		if desc.Offset > 0 {
			desc.Offset, err = subtractUint64Checked(desc.Offset, launcherSizeUint64, "slot descriptor offset")
			if err != nil {
				return nil, fmt.Errorf("failed to rebase slot descriptor %d offset: %w", i, err)
			}
		}
		copy(data[descStart:], desc.Pack())
	}

	// Patch index offsets
	index.MetadataOffset, err = subtractUint64Checked(index.MetadataOffset, launcherSizeUint64, "metadata offset")
	if err != nil {
		return nil, fmt.Errorf("failed to rebase metadata offset: %w", err)
	}
	index.SlotTableOffset, err = subtractUint64Checked(index.SlotTableOffset, launcherSizeUint64, "slot table offset")
	if err != nil {
		return nil, fmt.Errorf("failed to rebase slot table offset: %w", err)
	}
	index.PackageSize, err = intToUint64Checked(len(pspfData), "PSPF data size")
	if err != nil {
		return nil, fmt.Errorf("failed to convert PSPF size: %w", err)
	}
	index.LauncherSize = 0

	logger.Debug("Adjusted PSPF offsets",
		"metadata_offset_after", index.MetadataOffset,
		"slot_table_offset_after", index.SlotTableOffset)

	copy(trailer[4:4+IndexSize], index.Pack())
	return data, nil
}

// convertToResourceEmbedding converts an appended-PSPF file to resource-embedded PSPF.
//
// This reads the PSPF data that was appended after the launcher, removes it from the file,
// and embeds it as a PE resource instead.
func convertToResourceEmbedding(filePath string, launcherSize int64, logger hclog.Logger) error {
	logger.Debug("Converting append-mode to resource-embedding", "file", filePath, "launcher_size", launcherSize)

	// Read the entire file
	data, err := readFileValidated(filePath)
	if err != nil {
		return fmt.Errorf("failed to read file: %w", err)
	}

	totalSize := int64(len(data))
	logger.Debug("File sizes", "total", totalSize, "launcher", launcherSize, "pspf", totalSize-launcherSize)

	// Extract PSPF data (everything after launcher)
	if totalSize <= launcherSize {
		return fmt.Errorf("file is too small: total=%d, launcher=%d", totalSize, launcherSize)
	}

	pspfData := data[launcherSize:]
	logger.Debug("Extracted PSPF data", "size", len(pspfData))

	// Rebase all absolute offsets: they were relative to the combined launcher+PSPF file,
	// but when extracted to a standalone temp file the file starts at byte 0.
	adjustedPSPF, err := adjustPSPFOffsets(pspfData, launcherSize, logger)
	if err != nil {
		return fmt.Errorf("failed to adjust PSPF offsets: %w", err)
	}

	// Create unique temp file (NEVER modify original until success)
	// This avoids Windows file locking issues with in-place modification
	pid := os.Getpid()
	timestamp := time.Now().Unix()
	tempPath := fmt.Sprintf("%s.tmp.%d.%d", filePath, pid, timestamp)
	logger.Debug("Creating temporary file for resource embedding", "temp_path", tempPath)

	// Write launcher to temp file
	tempFile, err := openFileValidated(tempPath, os.O_CREATE|os.O_WRONLY|os.O_TRUNC, os.FileMode(ExecutablePerms))
	if err != nil {
		return fmt.Errorf("failed to write temp file: %w", err)
	}
	if _, err := tempFile.Write(data[:launcherSize]); err != nil {
		if closeErr := tempFile.Close(); closeErr != nil {
			logger.Debug("Failed to close temp file after write error", "error", closeErr)
		}
		return fmt.Errorf("failed to write temp file: %w", err)
	}
	if err := tempFile.Close(); err != nil {
		return fmt.Errorf("failed to close temp file: %w", err)
	}

	// Ensure temp file cleanup on error
	var embedErr error
	defer func() {
		if embedErr != nil {
			if err := removePath(tempPath); err != nil {
				logger.Warn("Failed to clean up temp file after error", "temp_path", tempPath, "error", err)
			} else {
				logger.Debug("Cleaned up temp file after error", "temp_path", tempPath)
			}
		}
	}()

	// Embed offset-adjusted PSPF as resource in temp file
	embedErr = embedPSPFAsResourceImpl(tempPath, adjustedPSPF, logger)
	if embedErr != nil {
		return fmt.Errorf("failed to embed as resource: %w", embedErr)
	}

	// Atomically replace original with temp file
	embedErr = atomicReplaceImpl(tempPath, filePath, logger)
	if embedErr != nil {
		return fmt.Errorf("failed to replace original file: %w", embedErr)
	}

	embedErr = nil // Success, don't delete temp file (it's now the original)

	// Verify the resource was embedded
	newSize, err := getFileSize(filePath)
	if err != nil {
		logger.Warn("Could not verify new file size", "error", err)
	} else {
		logger.Info("Resource embedding complete",
			"original_size", totalSize,
			"new_size", newSize,
			"launcher_size", launcherSize,
			"pspf_embedded", len(pspfData))
	}

	return nil
}

// getFileSize returns the size of a file
func getFileSize(path string) (int64, error) {
	info, err := os.Stat(path)
	if err != nil {
		return 0, err
	}
	return info.Size(), nil
}

func int64ToUint64Checked(value int64, field string) (uint64, error) {
	if value < 0 {
		return 0, fmt.Errorf("%s out of uint64 range: %d", field, value)
	}
	return uint64(value), nil
}

func intToUint32Checked(value int, field string) (uint32, error) {
	if value < 0 || value > math.MaxUint32 {
		return 0, fmt.Errorf("%s out of uint32 range: %d", field, value)
	}
	return uint32(value), nil
}

func addUint64Checked(base, addend uint64, field string) (uint64, error) {
	if base > math.MaxUint64-addend {
		return 0, fmt.Errorf("%s overflows uint64: %d + %d", field, base, addend)
	}
	return base + addend, nil
}

func subtractUint64Checked(value, subtract uint64, field string) (uint64, error) {
	if value < subtract {
		return 0, fmt.Errorf("%s underflows uint64: %d - %d", field, value, subtract)
	}
	return value - subtract, nil
}

func multiplyUint64Checked(value, multiplier uint64, field string) (uint64, error) {
	if multiplier != 0 && value > math.MaxUint64/multiplier {
		return 0, fmt.Errorf("%s overflows uint64: %d * %d", field, value, multiplier)
	}
	return value * multiplier, nil
}
