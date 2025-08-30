package format_2025

import (
	"crypto/ed25519"
	cryptorand "crypto/rand"
	"crypto/sha256"
	"encoding/binary"
	"encoding/json"
	"fmt"
	"hash/adler32"
	"io"
	"os"
	"os/exec"
	"path/filepath"
	"runtime"
	"runtime/debug"
	"strconv"
	"strings"
	"time"

	"github.com/hashicorp/go-hclog"
	"github.com/provide-io/flavor/go/flavor/pkg/logging"
)

type BuildConfig struct {
	// Package metadata (required per SPEC)
	Package         PackageConfig          `json:"package"`
	
	// Execution configuration (required per SPEC)
	Execution       ExecutionConfig        `json:"execution"`
	
	// Slots configuration
	Slots           []Slot                 `json:"slots"`
	
	// Optional configuration
	Launcher        string                 `json:"launcher,omitempty"`
	CacheValidation *CacheValidationConfig `json:"cache_validation,omitempty"`
	SetupCommands   []interface{}          `json:"setup_commands,omitempty"`
	Runtime         *RuntimeConfig         `json:"runtime,omitempty"`
}

type PackageConfig struct {
	Name        string `json:"name"`
	Version     string `json:"version"`
	Description string `json:"description,omitempty"`
}

type ExecutionConfig struct {
	PrimarySlot int               `json:"primary_slot,omitempty"`
	Command     string            `json:"command"`
	Environment map[string]string `json:"environment,omitempty"`
}

type RuntimeConfig struct {
	Env map[string]interface{} `json:"env,omitempty"`
}

type CacheValidationConfig struct {
	CheckFile       string `json:"check_file"`
	ExpectedContent string `json:"expected_content,omitempty"`
}

type Slot struct {
	Slot        *int   `json:"slot,omitempty"`        // Optional: position validator
	ID          string `json:"id"`                    // Arbitrary identifier
	Source      string `json:"source"`                 // Source path
	Target      string `json:"target"`                 // Destination in workenv
	Purpose     string `json:"purpose"`                // Role of the slot
	Lifecycle   string `json:"lifecycle"`              // Cache management
	Resolution  string `json:"resolution,omitempty"`   // When to resolve: build|runtime|lazy
	Encoding    string `json:"encoding"`               // Compression/encoding (string in JSON)
	Permissions string `json:"permissions,omitempty"`  // Unix permissions (e.g., "0755")
}

// hashSlotName computes a hash of the slot name (SHA256, first 8 bytes as uint64)
func hashSlotName(name string) uint64 {
	hash := sha256.Sum256([]byte(name))
	return binary.LittleEndian.Uint64(hash[:8])
}

// getBuilderTimestamp returns the compilation time of the builder binary
func getBuilderTimestamp() string {
	// Try to get build info from runtime
	if info, ok := debug.ReadBuildInfo(); ok {
		// Look for vcs.time setting (Go 1.18+)
		for _, setting := range info.Settings {
			if setting.Key == "vcs.time" {
				// Parse and format the time
				if t, err := time.Parse(time.RFC3339, setting.Value); err == nil {
					return t.UTC().Format(time.RFC3339)
				}
				return setting.Value
			}
		}
	}

	// Fallback: get the builder binary's modification time
	if exePath, err := os.Executable(); err == nil {
		if stat, err := os.Stat(exePath); err == nil {
			return stat.ModTime().UTC().Format(time.RFC3339)
		}
	}

	// Last resort: return current time
	return time.Now().UTC().Format(time.RFC3339)
}

// BuildWithLogLevel builds a PSPF package with explicit log level control
func BuildWithLogLevel(manifestPath, outputPath, launcherBin, privateKeyPath, publicKeyPath, keySeed, cliLogLevel string) {
	// Determine log level and source
	var logLevel string
	var logSource string
	
	if cliLogLevel != "" {
		logLevel = cliLogLevel
		logSource = "CLI --log-level"
	} else if envLevel := os.Getenv("FLAVOR_BUILDER_LOG_LEVEL"); envLevel != "" {
		logLevel = envLevel
		logSource = "FLAVOR_BUILDER_LOG_LEVEL"
	} else if envLevel := os.Getenv("FLAVOR_LOG_LEVEL"); envLevel != "" {
		logLevel = envLevel
		logSource = "FLAVOR_LOG_LEVEL"
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
	if logPath := os.Getenv("FLAVOR_LOG_PATH"); logPath != "" {
		if file, err := os.OpenFile(logPath, os.O_CREATE|os.O_WRONLY|os.O_APPEND, 0644); err == nil {
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
	logger.Info("🐹🐹🐹 Hello from Flavor's PSPF Builder 🐹🐹🐹")
	logger.Debug("Log level", "level", actualLevel, "source", logSource)
	logger.Info("PSPF Go Builder starting...")
	
	// Continue with normal build process
	doBuild(logger, manifestPath, outputPath, launcherBin, privateKeyPath, publicKeyPath, keySeed)
}

// BuildWithOptions builds a PSPF package with full control over key generation
func BuildWithOptions(manifestPath, outputPath, launcherBin, privateKeyPath, publicKeyPath, keySeed string) {
	BuildWithLogLevel(manifestPath, outputPath, launcherBin, privateKeyPath, publicKeyPath, keySeed, "")
}

// doBuild performs the actual build
func doBuild(logger hclog.Logger, manifestPath, outputPath, launcherBin, privateKeyPath, publicKeyPath, keySeed string) {

	// Read manifest
	manifestData, err := os.ReadFile(manifestPath)
	if err != nil {
		logger.Error("❌ Failed to read manifest", "error", err)
		os.Exit(1)
	}

	var config BuildConfig
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
	versionCmd := exec.Command(launcherPath, "--version")
	versionOutput, err := versionCmd.CombinedOutput()
	if err != nil {
		logger.Warn("⚠️ Failed to get launcher version", "error", err)
	} else {
		versionStr := strings.TrimSpace(string(versionOutput))
		logger.Info("🔍 Launcher version", "version", versionStr)
	}

	logger.Debug("🔍 Launcher path", "path", launcherPath)
	launcherData, err := os.ReadFile(launcherPath)
	if err != nil {
		logger.Error("❌ Failed to read launcher", "error", err, "path", launcherPath)
		os.Exit(1)
	}
	logger.Debug("✅ Launcher loaded", "size", len(launcherData))

	// 📁 Create output directory if it doesn't exist
	outputDir := filepath.Dir(outputPath)
	logger.Debug("📁 Ensuring output directory exists", "dir", outputDir)
	if err := os.MkdirAll(outputDir, os.FileMode(DefaultDirPerms)); err != nil {
		logger.Error("❌ Failed to create output directory", "error", err, "dir", outputDir)
		os.Exit(1)
	}

	// 💾 Create output file with executable permissions
	logger.Debug("💾 Creating output file", "path", outputPath)
	out, err := os.OpenFile(outputPath, os.O_RDWR|os.O_CREATE|os.O_TRUNC, os.FileMode(DefaultExecutablePerms))
	if err != nil {
		logger.Error("❌ Failed to create output file", "error", err)
		os.Exit(1)
	}
	defer func() {
		if err := out.Close(); err != nil {
			logger.Error("Failed to close output file", "error", err)
		}
	}()

	// ✍️ Write launcher
	logger.Debug("✍️ Writing launcher to output", "size", len(launcherData))
	if _, err := out.Write(launcherData); err != nil {
		logger.Error("❌ Failed to write launcher", "error", err)
		os.Exit(1)
	}
	launcherSize := int64(len(launcherData))

	// 📦 Create index
	logger.Debug("📦 Creating PSPF index")
	var formatMagic [8]byte
	copy(formatMagic[:], PSPFMagic)
	index := &PSPFIndex{
		FormatMagic:   formatMagic,
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
			actualSeed = os.Getenv("FLAVOR_KEY_SEED")
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

	// Skip index block space
	indexOffset := launcherSize
	if _, err := out.Seek(indexOffset+IndexSize, 0); err != nil {
		logger.Error("Failed to seek past index", "error", err)
		os.Exit(1)
	}

	// Build metadata
	var buildTimestamp string
	var buildHost string

	// Check for SOURCE_DATE_EPOCH for reproducible timestamps
	if epochStr := os.Getenv("SOURCE_DATE_EPOCH"); epochStr != "" {
		if epoch, err := time.Parse("2006-01-02T15:04:05Z07:00", epochStr); err == nil {
			buildTimestamp = epoch.UTC().Format(time.RFC3339)
		} else if epochDuration, err := time.ParseDuration(epochStr + "s"); err == nil {
			buildTimestamp = time.Unix(0, epochDuration.Nanoseconds()).UTC().Format(time.RFC3339)
		} else {
			buildTimestamp = time.Now().UTC().Format(time.RFC3339)
		}
		buildHost = fmt.Sprintf("%s/%s", runtime.GOOS, runtime.GOARCH)
	} else {
		hostname, _ := os.Hostname()
		buildTimestamp = time.Now().UTC().Format(time.RFC3339)
		buildHost = fmt.Sprintf("%s/%s %s", runtime.GOOS, runtime.GOARCH, hostname)
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
				Algorithm: "ecdsa-p256",
			},
		},
		Build: &BuildInfo{
			Tool:          "flavor-go",
			ToolVersion:   "1.0.0",
			Timestamp:     buildTimestamp,
			Deterministic: false, // TODO: Add KeySeed to BuildConfig if needed
			Platform: PlatformInfo{
				OS:   runtime.GOOS,
				Arch: runtime.GOARCH,
				Host: buildHost,
			},
		},
	}

	// 📦 Process slots
	logger.Info("📦 Processing slots", "count", len(config.Slots))
	logger.Debug("🔍 Slot processing details", "alignment", SlotAlignment, "descriptor_size", SlotDescriptorSize)
	var slotDescriptors []SlotDescriptor
	for i, slot := range config.Slots {
		// Validate required fields
		if slot.ID == "" {
			logger.Error("❌ Critical: Slot missing required 'id' field", "index", i)
			os.Exit(1)
		}
		if slot.Source == "" {
			logger.Error("❌ Critical: Slot missing required 'source' field", "index", i, "id", slot.ID)
			os.Exit(1)
		}
		if slot.Target == "" {
			logger.Error("❌ Critical: Slot missing required 'target' field", "index", i, "id", slot.ID)
			os.Exit(1)
		}
		
		// Set defaults
		if slot.Resolution == "" {
			slot.Resolution = "build"
		}
		if slot.Permissions == "" {
			slot.Permissions = fmt.Sprintf("%04o", DefaultFilePerms)  // Default to owner read/write, no execute
		}
		
		// Validate slot number if provided - critical error on mismatch
		if slot.Slot != nil && *slot.Slot != i {
			logger.Error("❌ Critical: Slot number mismatch", "expected", i, "declared", *slot.Slot, "id", slot.ID)
			os.Exit(1)
		}
		
		// 📂 Read slot data
		logger.Debug("📂 Processing slot", "index", i, "id", slot.ID, "source", slot.Source, "target", slot.Target)
		logger.Trace("🔎 Slot configuration", 
			"encoding", slot.Encoding, 
			"purpose", slot.Purpose, 
			"lifecycle", slot.Lifecycle,
			"resolution", slot.Resolution,
			"permissions", slot.Permissions)
		
		// Resolve {workenv} to base directory (FLAVOR_WORKENV_BASE or CWD)
		slotPath := slot.Source
		if strings.Contains(slotPath, "{workenv}") {
			// Priority: 1. FLAVOR_WORKENV_BASE env var, 2. Current working directory
			baseDir := os.Getenv("FLAVOR_WORKENV_BASE")
			if baseDir == "" {
				baseDir, _ = os.Getwd()
			}
			slotPath = strings.ReplaceAll(slotPath, "{workenv}", baseDir)
			logger.Debug("📍 Resolved path", "original", slot.Source, "resolved", slotPath, "base", baseDir)
		}
		
		slotData, err := os.ReadFile(slotPath)
		if err != nil {
			logger.Error("❌ Failed to read slot", "error", err, "path", slot.Source)
			os.Exit(1)
		}
		logger.Debug("📊 Slot size", "original", len(slotData), "encoding", slot.Encoding)

		// Add to metadata
		slotMeta := SlotMetadata{
			Slot:        i,  // Position validator
			ID:          slot.ID,
			Source:      slot.Source,
			Target:      slot.Target,
			Size:        0,  // Will be set after encoding handling
			Checksum:    "", // Will be set to compressed data checksum
			Encoding:    slot.Encoding,
			Purpose:     slot.Purpose,
			Lifecycle:   slot.Lifecycle,
			Resolution:  slot.Resolution,
			Permissions: slot.Permissions,
		}

		// Handle encoding based on manifest
		var compressed []byte
		var encodingMethod uint8 // defaults to 0 (none)

		logger.Debug("🎯 Processing slot encoding", "slot", i, "encoding", slot.Encoding, "id", slot.ID)
		switch slot.Encoding {
		case "gzip":
			compressed = slotData
			encodingMethod = EncodingGzip // 2 = single gzipped file
			logger.Debug("🗜️ Slot encoding", "slot", i, "encoding", slot.Encoding, "method", encodingMethod)
		case "tgz", "tar.gz":
			compressed = slotData
			encodingMethod = EncodingTgz // 3 = tar.gz
			logger.Debug("📦 Slot encoding", "slot", i, "encoding", slot.Encoding, "method", encodingMethod)
		case "tar":
			compressed = slotData
			encodingMethod = EncodingTar // 1 = uncompressed tar
			logger.Debug("📦 Slot encoding", "slot", i, "encoding", slot.Encoding, "method", encodingMethod)
		case "none", "":
			compressed = slotData
			encodingMethod = EncodingRaw // 0 = raw uncompressed
			logger.Debug("📄 Slot encoding", "slot", i, "encoding", slot.Encoding, "method", encodingMethod)
		default:
			compressed = slotData
			encodingMethod = EncodingRaw // 0 = raw uncompressed
			logger.Debug("⚠️ Unknown encoding, using raw", "slot", i, "encoding", slot.Encoding, "method", encodingMethod)
		}

		// Update metadata with size and checksum (using SHA-256 with prefix)
		slotMeta.Size = int64(len(compressed)) // Size as stored in the package
		slotMeta.Checksum = CalculateChecksum(compressed, ChecksumSHA256)
		metadata.Slots = append(metadata.Slots, slotMeta)

		// 🏷️ Align position
		currentPos, _ := out.Seek(0, 1)
		alignedPos := AlignOffset(currentPos, SlotAlignment)
		if alignedPos > currentPos {
			padding := make([]byte, alignedPos-currentPos)
			if _, err := out.Write(padding); err != nil {
				logger.Error("Failed to write padding", "error", err)
				os.Exit(1)
			}
			logger.Debug("🏷️ Aligned slot position", "from", currentPos, "to", alignedPos, "padding", len(padding))
		}

		// ✍️ Write slot
		slotOffset := alignedPos
		logger.Debug("✍️ Writing slot", "id", slot.ID, "offset", slotOffset, "size", len(compressed))
		if _, err := out.Write(compressed); err != nil {
			logger.Error("❌ Failed to write slot", "error", err)
			os.Exit(1)
		}

		// Map purpose string to uint8
		var purposeValue uint8
		switch slot.Purpose {
		case "payload":
			purposeValue = 0
		case "runtime":
			purposeValue = 1
		case "tool":
			purposeValue = 2
		default:
			purposeValue = 0 // default to payload
		}

		// Map lifecycle string to uint8
		var lifecycleValue uint8
		switch slot.Lifecycle {
		// Timing-based
		case "init":
			lifecycleValue = 0
		case "startup":
			lifecycleValue = 1
		case "runtime":
			lifecycleValue = 2
		case "shutdown":
			lifecycleValue = 3
		// Retention-based
		case "cache":
			lifecycleValue = 4
		case "temp":
			lifecycleValue = 5
		// Access-based
		case "lazy":
			lifecycleValue = 6
		case "eager":
			lifecycleValue = 7
		// Environment-based
		case "dev":
			lifecycleValue = 8
		case "config":
			lifecycleValue = 9
		case "platform":
			lifecycleValue = 10
		default:
			lifecycleValue = 2 // default to runtime
		}

		// Parse permissions from metadata or use default
		var permissions uint16
		if slot.Permissions != "" {
			// Parse octal string (e.g., "0755" -> 0o755)
			permStr := strings.TrimPrefix(slot.Permissions, "0")
			if parsed, err := strconv.ParseUint(permStr, 8, 16); err == nil {
				permissions = uint16(parsed)
			} else {
				permissions = uint16(DefaultFilePerms)
			}
		} else {
			permissions = uint16(DefaultFilePerms)  // Default: read/write for owner only
		}
		
		slotDescriptors = append(slotDescriptors, SlotDescriptor{
			ID:           uint64(i),
			NameHash:     hashSlotName(slot.ID),
			Offset:       uint64(slotOffset),
			Size:         uint64(len(compressed)), // actual stored size
			OriginalSize: uint64(len(slotData)),   // original uncompressed size
			Checksum:     adler32.Checksum(compressed),
			Encoding:     encodingMethod,
			Encryption:   0, // no encryption
			Alignment:    uint16(SlotAlignment),
			Purpose:      purposeValue,
			Lifecycle:    lifecycleValue,
			AccessHint:   0, // sequential
			Priority:     128, // normal priority
			Permissions:  permissions,
			Platform:     0, // all platforms
			ExtendedOffset: 0,
			ExtendedSize:   0,
		})
	}

	// Write slot table
	currentPos, _ := out.Seek(0, 1)
	slotTableOffset := AlignOffset(currentPos, SlotAlignment)
	if _, err := out.Seek(slotTableOffset, 0); err != nil {
		logger.Error("Failed to seek to slot table", "error", err)
		os.Exit(1)
	}

	index.SlotTableOffset = uint64(slotTableOffset)
	index.SlotCount = uint32(len(slotDescriptors))

	// Write 64-byte slot descriptors
	for _, desc := range slotDescriptors {
		// Write the descriptor as a packed 64-byte structure
		if err := binary.Write(out, binary.LittleEndian, desc); err != nil {
			logger.Error("Failed to write slot descriptor", "error", err)
			os.Exit(1)
		}
	}
	// Each slot descriptor is 64 bytes as per PSPF/2025 spec
	index.SlotTableSize = uint64(len(slotDescriptors) * SlotDescriptorSize)

	// 📜 Create and write metadata (gzipped JSON)
	metadataPos, _ := out.Seek(0, 1)
	logger.Debug("📜 Writing metadata (gzipped JSON)", "position", metadataPos)
	metadataSize, signature, err := writeMetadata(out, metadata, privateKey, publicKey)
	if err != nil {
		logger.Error("❌ Failed to write metadata", "error", err)
		os.Exit(1)
	}
	logger.Debug("✅ Metadata written", "size", metadataSize)

	index.MetadataOffset = uint64(metadataPos)
	index.MetadataSize = uint64(metadataSize)

	// Store signature in index (first 64 bytes of 512-byte field)
	copy(index.IntegritySignature[:64], signature)

	// Calculate metadata checksum (Adler-32 of compressed data)
	// Need to seek back and read the compressed data
	savedPos, _ := out.Seek(0, 1)
	out.Seek(int64(metadataPos), 0)
	compressedData := make([]byte, metadataSize)
	out.Read(compressedData)
	out.Seek(savedPos, 0)

	metadataChecksum := adler32.Checksum(compressedData)
	// Store as 4 bytes in the 32-byte field
	binary.LittleEndian.PutUint32(index.MetadataChecksum[:4], metadataChecksum)

	// 🪄 Write trailing magic (emoji bytes, XOR decoded)
	logger.Debug("🪄 Writing trailing magic")
	if _, err := out.Write(TrailingMagic); err != nil {
		logger.Error("❌ Failed to write trailing magic", "error", err)
		os.Exit(1)
	}

	// Update package size
	finalPos, _ := out.Seek(0, 1)
	index.PackageSize = uint64(finalPos)

	// 🔐 Calculate index checksum (with checksum field as 0)
	indexData := index.Pack()
	// Set checksum field to 0 for calculation
	binary.LittleEndian.PutUint32(indexData[12:16], 0)
	checksum := adler32.Checksum(indexData)
	index.IndexChecksum = checksum
	logger.Debug("🔐 Index checksum calculated", "checksum", fmt.Sprintf("0x%08x", checksum))

	// 📋 Write index with calculated checksum
	logger.Debug("📋 Writing index block", "offset", indexOffset, "size", IndexSize)
	if _, err := out.Seek(indexOffset, 0); err != nil {
		logger.Error("❌ Failed to seek to index", "error", err)
		os.Exit(1)
	}
	if _, err := out.Write(index.Pack()); err != nil {
		logger.Error("❌ Failed to write index", "error", err)
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
	if err := os.Chmod(outputPath, os.FileMode(DefaultExecutablePerms)); err != nil {
		logger.Error("❌ Failed to make output executable", "error", err)
		os.Exit(1)
	}
	logger.Debug("🔧 Set executable permissions on output file")
}
