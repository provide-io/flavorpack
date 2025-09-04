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

// BuildOptions represents the configuration for building a PSPF package.
// This aligns with Python's BuildOptions and Rust's BuildOptions for consistency.
type BuildOptions struct {
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
// SlotProcessor handles slot processing for PSPF packages.
// This aligns with Rust's SlotProcessor for consistency across implementations.
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

// ProcessSlots processes all slots from the manifest
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

// processSlot processes a single slot
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
		Size:        len(slotData),
		Checksum:    checksumStr,
		Encoding:    slot.Encoding,
		Purpose:     slot.Purpose,
		Lifecycle:   slot.Lifecycle,
		Resolution:  slot.Resolution,
		Permissions: slot.Permissions,
	}
	
	// Create slot descriptor
	descriptor := SlotDescriptor{
		Slot:         uint32(index),
		Offset:       0, // Will be set during write phase
		Size:         uint64(len(compressed)),
		Checksum:     checksumData[:],
		Encoding:     encodingMethod,
		Reserved1:    0,
		Reserved2:    0,
	}
	
	// Store processed data
	sp.metadataSlots = append(sp.metadataSlots, slotMeta)
	sp.slotDescriptors = append(sp.slotDescriptors, descriptor)
	sp.slotData = append(sp.slotData, compressed)
	
	sp.logger.Debug("✅ Slot processed", "index", index, "id", slot.ID, 
		"compressed_size", len(compressed), "original_size", len(slotData))
	
	return nil
}

// loadSlotData loads and processes slot data based on encoding
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
	case "none", "":
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
	
	// Note: OLD SLOT PROCESSING LOOP REMOVED - Now handled by SlotProcessor above
	// The SlotProcessor validates, processes encoding, and creates descriptors
	
	// TODO: Delete the old loop below after verifying SlotProcessor works correctly
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

		// Store compressed data for later (we'll write it after metadata and slot table)
		slotDataToWrite = append(slotDataToWrite, compressed)

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
		
		// We'll fill in the offset later when we actually write the slot data
		slotDescriptors = append(slotDescriptors, SlotDescriptor{
			ID:           uint64(i),
			NameHash:     hashSlotName(slot.ID),
			Offset:       0, // Will be filled in later
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

	// 📜 Create and write metadata (gzipped JSON) - RIGHT AFTER LAUNCHER
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

	// Write slot table
	currentPos, _ := out.Seek(0, 1)
	slotTableOffset := AlignOffset(currentPos, SlotAlignment)
	if _, err := out.Seek(slotTableOffset, 0); err != nil {
		logger.Error("Failed to seek to slot table", "error", err)
		os.Exit(1)
	}

	index.SlotTableOffset = uint64(slotTableOffset)
	index.SlotCount = uint32(len(slotDescriptors))
	index.SlotTableSize = uint64(len(slotDescriptors) * SlotDescriptorSize)

	// Reserve space for slot table (we'll write it after calculating slot offsets)
	if _, err := out.Seek(slotTableOffset + int64(index.SlotTableSize), 0); err != nil {
		logger.Error("Failed to seek past slot table", "error", err)
		os.Exit(1)
	}

	// Now write the actual slot data and update descriptors with correct offsets
	for i, compressed := range slotDataToWrite {
		// Align position
		currentPos, _ := out.Seek(0, 1)
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
		slotDescriptors[i].Offset = uint64(slotOffset)
		logger.Debug("✍️ Writing slot", "id", i, "offset", slotOffset, "size", len(compressed))
		if _, err := out.Write(compressed); err != nil {
			logger.Error("❌ Failed to write slot", "error", err)
			os.Exit(1)
		}
	}

	// Go back and write the slot table with correct offsets
	endOfSlots, _ := out.Seek(0, 1)
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

	// Update package size before writing MagicTrailer
	// (add 8200 for the trailer that will be written)
	currentPos, _ = out.Seek(0, 1)
	index.PackageSize = uint64(currentPos) + MagicTrailerSize

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
	if err := os.Chmod(outputPath, os.FileMode(DefaultExecutablePerms)); err != nil {
		logger.Error("❌ Failed to make output executable", "error", err)
		os.Exit(1)
	}
	logger.Debug("🔧 Set executable permissions on output file")
}
