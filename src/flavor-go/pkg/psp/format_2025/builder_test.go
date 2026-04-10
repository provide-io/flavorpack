package format_2025

import (
	"bytes"
	"crypto/ed25519"
	cryptorand "crypto/rand"
	"crypto/sha256"
	"crypto/x509"
	"encoding/binary"
	"encoding/json"
	"encoding/pem"
	"log/slog"
	"math"
	"os"
	"path/filepath"
	"runtime"
	"strings"
	"testing"

	"github.com/provide-io/flavor/go/flavor/pkg/logging"
)

func TestBuilderBuildWithLogLevelDelegates(t *testing.T) {
	oldBuildImpl := buildImpl
	t.Cleanup(func() {
		buildImpl = oldBuildImpl
	})

	type call struct {
		manifestPath   string
		outputPath     string
		launcherBin    string
		privateKeyPath string
		publicKeyPath  string
		keySeed        string
	}

	var got call
	buildImpl = func(_ *slog.Logger, manifestPath, outputPath, launcherBin, privateKeyPath, publicKeyPath, keySeed string) {
		got = call{
			manifestPath:   manifestPath,
			outputPath:     outputPath,
			launcherBin:    launcherBin,
			privateKeyPath: privateKeyPath,
			publicKeyPath:  publicKeyPath,
			keySeed:        keySeed,
		}
	}

	t.Setenv(EnvBuilderLogLevel, "warn")
	t.Setenv(EnvLogLevel, "error")

	BuildWithLogLevel("manifest.json", "bundle.pspf", "launcher.bin", "private.key", "public.key", "seed", "json:debug")

	if got.manifestPath != "manifest.json" || got.outputPath != "bundle.pspf" || got.launcherBin != "launcher.bin" || got.privateKeyPath != "private.key" || got.publicKeyPath != "public.key" || got.keySeed != "seed" {
		t.Fatalf("BuildWithLogLevel() delegated unexpected arguments: %#v", got)
	}
}

func TestBuilderBuildWithOptionsDelegates(t *testing.T) {
	oldBuildImpl := buildImpl
	t.Cleanup(func() {
		buildImpl = oldBuildImpl
	})

	var got struct {
		manifestPath   string
		outputPath     string
		launcherBin    string
		privateKeyPath string
		publicKeyPath  string
		keySeed        string
	}
	buildImpl = func(_ *slog.Logger, manifestPath, outputPath, launcherBin, privateKeyPath, publicKeyPath, keySeed string) {
		got.manifestPath = manifestPath
		got.outputPath = outputPath
		got.launcherBin = launcherBin
		got.privateKeyPath = privateKeyPath
		got.publicKeyPath = publicKeyPath
		got.keySeed = keySeed
	}

	BuildWithOptions("manifest.json", "bundle.pspf", "launcher.bin", "private.key", "public.key", "seed")

	if got.manifestPath != "manifest.json" || got.outputPath != "bundle.pspf" || got.launcherBin != "launcher.bin" || got.privateKeyPath != "private.key" || got.publicKeyPath != "public.key" || got.keySeed != "seed" {
		t.Fatalf("BuildWithOptions() delegated unexpected arguments: %#v", got)
	}
}

func TestBuilderBuildWithLogLevelWritesExpectedLogs(t *testing.T) {
	oldBuildImpl := buildImpl
	t.Cleanup(func() {
		buildImpl = oldBuildImpl
	})

	cases := []struct {
		name       string
		cliLog     string
		builderLog string
		globalLog  string
		wantSource string
		wantJSON   bool
	}{
		{
			name:       "builder env wins",
			builderLog: "debug",
			globalLog:  "error",
			wantSource: EnvBuilderLogLevel,
		},
		{
			name:       "global env fallback",
			globalLog:  "debug",
			wantSource: EnvLogLevel,
		},
		{
			name:       "cli json overrides env",
			cliLog:     "json:debug",
			builderLog: "debug",
			globalLog:  "error",
			wantSource: "CLI --log-level",
			wantJSON:   true,
		},
	}

	for _, tt := range cases {
		tt := tt
		t.Run(tt.name, func(t *testing.T) {
			dir := t.TempDir()
			logPath := filepath.Join(dir, "builder.log")
			t.Setenv(EnvLogPath, logPath)
			if tt.builderLog != "" {
				t.Setenv(EnvBuilderLogLevel, tt.builderLog)
			}
			if tt.globalLog != "" {
				t.Setenv(EnvLogLevel, tt.globalLog)
			}

			called := false
			buildImpl = func(_ *slog.Logger, manifestPath, outputPath, launcherBin, privateKeyPath, publicKeyPath, keySeed string) {
				called = true
				if manifestPath != "manifest.json" || outputPath != "bundle.pspf" || launcherBin != "launcher.bin" || privateKeyPath != "private.key" || publicKeyPath != "public.key" || keySeed != "seed" {
					t.Fatalf("BuildWithLogLevel() delegated unexpected arguments: %q %q %q %q %q %q", manifestPath, outputPath, launcherBin, privateKeyPath, publicKeyPath, keySeed)
				}
			}

			BuildWithLogLevel("manifest.json", "bundle.pspf", "launcher.bin", "private.key", "public.key", "seed", tt.cliLog)

			if !called {
				t.Fatal("expected buildImpl to be called")
			}

			data, err := os.ReadFile(logPath)
			if err != nil {
				t.Fatalf("ReadFile() error = %v", err)
			}
			if !bytes.Contains(data, []byte(tt.wantSource)) {
				t.Fatalf("expected log output to mention %q, got %q", tt.wantSource, string(data))
			}

			firstLine := data
			if newline := bytes.IndexByte(firstLine, '\n'); newline >= 0 {
				firstLine = firstLine[:newline]
			}
			if tt.wantJSON {
				if !bytes.HasPrefix(firstLine, []byte("{")) {
					t.Fatalf("expected JSON log output, got %q", string(data))
				}
				if !bytes.Contains(data, []byte(`"level":"DEBUG"`)) {
					t.Fatalf("expected JSON log output, got %q", string(data))
				}
			} else {
				if !bytes.HasPrefix(firstLine, []byte("time=")) {
					t.Fatalf("expected prefixed text log output, got %q", string(data))
				}
				if bytes.Contains(data, []byte(`"level":"DEBUG"`)) {
					t.Fatalf("expected text log output, got %q", string(data))
				}
			}
		})
	}
}

func TestDoBuildSuccessWithConcreteSlot(t *testing.T) {
	dir := t.TempDir()
	manifestPath := filepath.Join(dir, "manifest.json")
	outputPath := filepath.Join(dir, "bundle.pspf")
	launcherPath := filepath.Join(dir, "launcher.sh")
	slotSource := filepath.Join(dir, "payload.txt")

	if err := os.WriteFile(slotSource, []byte("payload-data"), 0o600); err != nil {
		t.Fatalf("WriteFile(slot source) error = %v", err)
	}

	launcherScript := []byte("#!/bin/sh\nif [ \"$1\" = \"--version\" ]; then\n  echo launcher 1.0\nfi\n")
	if err := os.WriteFile(launcherPath, launcherScript, 0o755); err != nil {
		t.Fatalf("WriteFile(launcher) error = %v", err)
	}

	manifest := BuildOptions{
		Package: PackageConfig{
			Name:    "demo",
			Version: "1.0.0",
		},
		Execution: ExecutionConfig{
			Command: "/bin/true",
		},
		Slots: []Slot{
			{
				ID:     "payload",
				Source: slotSource,
				Target: "payload.txt",
			},
		},
	}

	manifestData, err := json.Marshal(manifest)
	if err != nil {
		t.Fatalf("json.Marshal() error = %v", err)
	}
	if err := os.WriteFile(manifestPath, manifestData, 0o600); err != nil {
		t.Fatalf("WriteFile(manifest) error = %v", err)
	}

	t.Setenv("SOURCE_DATE_EPOCH", "1735689600")

	doBuild(logging.NewNullLogger(), manifestPath, outputPath, launcherPath, "", "", "seed")

	got, err := os.ReadFile(outputPath)
	if err != nil {
		t.Fatalf("ReadFile(output) error = %v", err)
	}
	if len(got) <= len(launcherScript) {
		t.Fatalf("expected bundled output to be larger than launcher, got %d bytes", len(got))
	}

	trailerStart := len(got) - MagicTrailerSize
	if !bytes.Equal(got[trailerStart:trailerStart+4], PackageEmojiBytes) {
		t.Fatalf("output trailer missing package emoji: %q", got[trailerStart:trailerStart+4])
	}
	if !bytes.Equal(got[trailerStart+MagicTrailerSize-4:], MagicWandEmojiBytes) {
		t.Fatalf("output trailer missing magic wand emoji: %q", got[trailerStart+MagicTrailerSize-4:])
	}

	var index PSPFIndex
	if err := index.Unpack(got[trailerStart+4 : trailerStart+4+IndexSize]); err != nil {
		t.Fatalf("index.Unpack() error = %v", err)
	}
	if got, want := index.LauncherSize, uint64(len(launcherScript)); got != want {
		t.Fatalf("index.LauncherSize = %d, want %d", got, want)
	}
	if got, want := index.SlotCount, uint32(1); got != want {
		t.Fatalf("index.SlotCount = %d, want %d", got, want)
	}
}

func TestDoBuildLoadsKeyFilesAndCarriesRuntimeMetadata(t *testing.T) {
	dir := t.TempDir()
	manifestPath := filepath.Join(dir, "manifest.json")
	outputPath := filepath.Join(dir, "bundle.pspf")
	launcherPath := filepath.Join(dir, "launcher.sh")
	slotSource := filepath.Join(dir, "payload.txt")
	privateKeyPath := filepath.Join(dir, "private.pem")
	publicKeyPath := filepath.Join(dir, "public.pem")

	if err := os.WriteFile(slotSource, []byte("payload-data"), 0o600); err != nil {
		t.Fatalf("WriteFile(slot source) error = %v", err)
	}
	if err := os.WriteFile(launcherPath, []byte("#!/bin/sh\nexit 0\n"), 0o755); err != nil {
		t.Fatalf("WriteFile(launcher) error = %v", err)
	}

	publicKey, privateKey, err := ed25519.GenerateKey(cryptorand.Reader)
	if err != nil {
		t.Fatalf("GenerateKey() error = %v", err)
	}
	privateDER, err := x509.MarshalPKCS8PrivateKey(privateKey)
	if err != nil {
		t.Fatalf("MarshalPKCS8PrivateKey() error = %v", err)
	}
	publicDER, err := x509.MarshalPKIXPublicKey(publicKey)
	if err != nil {
		t.Fatalf("MarshalPKIXPublicKey() error = %v", err)
	}
	if err := os.WriteFile(privateKeyPath, pem.EncodeToMemory(&pem.Block{Type: "PRIVATE KEY", Bytes: privateDER}), 0o600); err != nil {
		t.Fatalf("WriteFile(private key) error = %v", err)
	}
	if err := os.WriteFile(publicKeyPath, pem.EncodeToMemory(&pem.Block{Type: "PUBLIC KEY", Bytes: publicDER}), 0o600); err != nil {
		t.Fatalf("WriteFile(public key) error = %v", err)
	}

	manifest := BuildOptions{
		Package: PackageConfig{Name: "demo", Version: "2.0.0"},
		Execution: ExecutionConfig{
			Command: "/bin/true",
			Environment: map[string]string{
				"APP_MODE": "test",
			},
		},
		Runtime: &RuntimeConfig{
			Env: map[string]interface{}{
				"set": map[string]interface{}{"RUNTIME_FLAG": "1"},
			},
		},
		CacheValidation: &CacheValidationConfig{
			CheckFile:       "{workenv}/ready.txt",
			ExpectedContent: "ok",
		},
		SetupCommands: []interface{}{
			"/bin/true",
		},
		Slots: []Slot{
			{ID: "payload", Source: slotSource, Target: "payload.txt"},
		},
	}

	manifestData, err := json.Marshal(manifest)
	if err != nil {
		t.Fatalf("json.Marshal() error = %v", err)
	}
	if err := os.WriteFile(manifestPath, manifestData, 0o600); err != nil {
		t.Fatalf("WriteFile(manifest) error = %v", err)
	}

	doBuild(logging.NewNullLogger(), manifestPath, outputPath, launcherPath, privateKeyPath, publicKeyPath, "")

	reader, err := NewReader(outputPath)
	if err != nil {
		t.Fatalf("NewReader() error = %v", err)
	}
	defer func() { _ = reader.Close() }()

	index, err := reader.ReadIndex()
	if err != nil {
		t.Fatalf("ReadIndex() error = %v", err)
	}

	metadata, err := reader.ReadMetadata()
	if err != nil {
		t.Fatalf("ReadMetadata() error = %v", err)
	}
	if metadata.Package.Version != "2.0.0" {
		t.Fatalf("metadata package version = %q", metadata.Package.Version)
	}
	if metadata.Runtime == nil || metadata.Runtime.Env == nil {
		t.Fatal("expected runtime env metadata to be present")
	}
	if metadata.CacheValidation == nil || metadata.CacheValidation.ExpectedContent != "ok" {
		t.Fatalf("expected cache validation metadata, got %#v", metadata.CacheValidation)
	}
	if metadata.Verification == nil || metadata.Verification.IntegritySeal.Algorithm != "ed25519" {
		t.Fatalf("expected verification metadata, got %#v", metadata.Verification)
	}
	if !bytes.Equal(index.PublicKey[:32], publicKey[:32]) {
		t.Fatalf("expected index public key to match loaded key")
	}
	expectedFP, err := ComputeKeyFingerprint(publicKey)
	if err != nil {
		t.Fatalf("ComputeKeyFingerprint() error = %v", err)
	}
	if got := strings.TrimRight(string(index.AttestationKeyFp[:]), "\x00"); got != expectedFP {
		t.Fatalf("expected attestation fingerprint %q, got %q", expectedFP, got)
	}
	if metadata.Execution == nil || metadata.Execution.Environment["APP_MODE"] != "test" {
		t.Fatalf("expected execution environment metadata, got %#v", metadata.Execution)
	}
}

func TestDoBuildUsesEnvSeedWhenRequested(t *testing.T) {
	dir := t.TempDir()
	manifestPath := filepath.Join(dir, "manifest.json")
	outputPath := filepath.Join(dir, "bundle.pspf")
	launcherPath := filepath.Join(dir, "launcher.sh")
	slotSource := filepath.Join(dir, "payload.txt")

	if err := os.WriteFile(slotSource, []byte("payload-data"), 0o600); err != nil {
		t.Fatalf("WriteFile(slot source) error = %v", err)
	}
	if err := os.WriteFile(launcherPath, []byte("#!/bin/sh\nif [ \"$1\" = \"--version\" ]; then\n  exit 1\nfi\nexit 0\n"), 0o755); err != nil {
		t.Fatalf("WriteFile(launcher) error = %v", err)
	}

	manifest := BuildOptions{
		Package:   PackageConfig{Name: "seeded", Version: "3.0.0"},
		Execution: ExecutionConfig{Command: "/bin/true"},
		Slots: []Slot{
			{ID: "payload", Source: slotSource, Target: "payload.txt"},
		},
	}
	manifestData, err := json.Marshal(manifest)
	if err != nil {
		t.Fatalf("json.Marshal() error = %v", err)
	}
	if err := os.WriteFile(manifestPath, manifestData, 0o600); err != nil {
		t.Fatalf("WriteFile(manifest) error = %v", err)
	}

	t.Setenv(EnvKeySeed, "seed-from-env")
	t.Setenv("SOURCE_DATE_EPOCH", "not-a-number")

	doBuild(logging.NewNullLogger(), manifestPath, outputPath, launcherPath, "", "", "env")

	reader, err := NewReader(outputPath)
	if err != nil {
		t.Fatalf("NewReader() error = %v", err)
	}
	defer func() { _ = reader.Close() }()

	index, err := reader.ReadIndex()
	if err != nil {
		t.Fatalf("ReadIndex() error = %v", err)
	}
	metadata, err := reader.ReadMetadata()
	if err != nil {
		t.Fatalf("ReadMetadata() error = %v", err)
	}

	expectedSeed := sha256.Sum256([]byte("seed-from-env"))
	expectedPrivate := ed25519.NewKeyFromSeed(expectedSeed[:])
	expectedPublic := expectedPrivate.Public().(ed25519.PublicKey)
	if !bytes.Equal(index.PublicKey[:32], expectedPublic[:32]) {
		t.Fatalf("expected index public key to match env-derived seed")
	}
	if metadata.Build == nil || metadata.Build.Timestamp == "" || metadata.Build.Platform.Host == "" {
		t.Fatalf("expected build metadata to be populated, got %#v", metadata.Build)
	}
}

func TestBuilderShouldUseResourceEmbeddingForOS(t *testing.T) {
	t.Parallel()

	logger := logging.NewNullLogger()
	goLauncher := syntheticPELauncherForBuilderTest(t, 0x80)
	rustLauncher := syntheticPELauncherForBuilderTest(t, 0xE8)

	tests := []struct {
		name string
		goos string
		data []byte
		want bool
	}{
		{name: "non-windows always appends", goos: "linux", data: goLauncher, want: false},
		{name: "windows go launcher embeds", goos: "windows", data: goLauncher, want: true},
		{name: "windows rust launcher appends", goos: "windows", data: rustLauncher, want: false},
	}

	for _, tt := range tests {
		tt := tt
		t.Run(tt.name, func(t *testing.T) {
			t.Parallel()
			if got := shouldUseResourceEmbeddingForOS(tt.goos, tt.data, logger); got != tt.want {
				t.Fatalf("shouldUseResourceEmbeddingForOS(%q, ...) = %v, want %v", tt.goos, got, tt.want)
			}
		})
	}

	if runtime.GOOS != "windows" {
		if got := shouldUseResourceEmbedding(goLauncher, logger); got {
			t.Fatalf("shouldUseResourceEmbedding() on %s = true, want false", runtime.GOOS)
		}
	}
}

func TestBuilderAdjustPSPFOffsetsRebasesOffsets(t *testing.T) {
	t.Parallel()

	logger := logging.NewNullLogger()
	launcherSize := int64(100)
	pspfData, slotStart := syntheticPSPFDataForBuilderTest(t, launcherSize, 180, 200, 240)

	adjusted, err := adjustPSPFOffsets(pspfData, launcherSize, logger)
	if err != nil {
		t.Fatalf("adjustPSPFOffsets() error = %v", err)
	}

	adjustedDesc, err := UnpackSlotDescriptor(adjusted[slotStart : slotStart+SlotDescriptorSize])
	if err != nil {
		t.Fatalf("UnpackSlotDescriptor() error = %v", err)
	}
	if got, want := adjustedDesc.Offset, uint64(140); got != want {
		t.Fatalf("descriptor offset = %d, want %d", got, want)
	}

	trailerStart := len(adjusted) - MagicTrailerSize
	var index PSPFIndex
	if err := index.Unpack(adjusted[trailerStart+4 : trailerStart+4+IndexSize]); err != nil {
		t.Fatalf("index.Unpack() error = %v", err)
	}
	if got, want := index.MetadataOffset, uint64(80); got != want {
		t.Fatalf("metadata offset = %d, want %d", got, want)
	}
	if got, want := index.SlotTableOffset, uint64(100); got != want {
		t.Fatalf("slot table offset = %d, want %d", got, want)
	}
	if got, want := index.PackageSize, uint64(len(pspfData)); got != want {
		t.Fatalf("package size = %d, want %d", got, want)
	}
	if got, want := index.LauncherSize, uint64(0); got != want {
		t.Fatalf("launcher size = %d, want %d", got, want)
	}
}

func TestBuilderAdjustPSPFOffsetsRejectsInvalidInputs(t *testing.T) {
	t.Parallel()

	logger := logging.NewNullLogger()
	validData, _ := syntheticPSPFDataForBuilderTest(t, 100, 180, 200, 240)

	tests := []struct {
		name         string
		data         []byte
		launcherSize int64
		wantErr      string
	}{
		{name: "too small", data: make([]byte, MagicTrailerSize-1), launcherSize: 0, wantErr: "PSPF data too small"},
		{name: "bad trailer magic", data: mutateTrailerMagicForBuilderTest(t, validData), launcherSize: 100, wantErr: "missing 📦"},
		{name: "launcher underflow", data: validData, launcherSize: 250, wantErr: "launcher size exceeds slot table offset"},
	}

	for _, tt := range tests {
		tt := tt
		t.Run(tt.name, func(t *testing.T) {
			t.Parallel()
			_, err := adjustPSPFOffsets(tt.data, tt.launcherSize, logger)
			if err == nil || !bytes.Contains([]byte(err.Error()), []byte(tt.wantErr)) {
				t.Fatalf("adjustPSPFOffsets() error = %v, want substring %q", err, tt.wantErr)
			}
		})
	}
}

func TestBuilderConvertToResourceEmbeddingRejectsShortFile(t *testing.T) {
	t.Parallel()

	tempDir := t.TempDir()
	filePath := filepath.Join(tempDir, "bundle.pspf")
	if err := os.WriteFile(filePath, []byte("launcher"), 0o644); err != nil {
		t.Fatalf("WriteFile() error = %v", err)
	}

	err := convertToResourceEmbedding(filePath, 64, logging.NewNullLogger())
	if err == nil || !bytes.Contains([]byte(err.Error()), []byte("file is too small")) {
		t.Fatalf("convertToResourceEmbedding() error = %v, want short-file failure", err)
	}
}

func TestBuilderConvertToResourceEmbeddingRewritesFile(t *testing.T) {
	tempDir := t.TempDir()
	filePath := filepath.Join(tempDir, "bundle.pspf")
	launcherSize := int64(100)
	launcher := bytes.Repeat([]byte("L"), int(launcherSize))
	pspfData, _ := syntheticPSPFDataForBuilderTest(t, launcherSize, 180, 200, 240)
	original := append(append([]byte(nil), launcher...), pspfData...)

	if err := os.WriteFile(filePath, original, 0o644); err != nil {
		t.Fatalf("WriteFile() error = %v", err)
	}

	oldEmbed := embedPSPFAsResourceImpl
	oldAtomic := atomicReplaceImpl
	t.Cleanup(func() {
		embedPSPFAsResourceImpl = oldEmbed
		atomicReplaceImpl = oldAtomic
	})

	embedPSPFAsResourceImpl = func(exePath string, adjustedPSPF []byte, logger *slog.Logger) error {
		launcherBytes, err := os.ReadFile(exePath)
		if err != nil {
			return err
		}
		return os.WriteFile(exePath, append(launcherBytes, adjustedPSPF...), 0o700)
	}
	atomicReplaceImpl = func(sourcePath, destPath string, logger *slog.Logger) error {
		return os.Rename(sourcePath, destPath)
	}

	logger := logging.NewNullLogger()
	if err := convertToResourceEmbedding(filePath, launcherSize, logger); err != nil {
		t.Fatalf("convertToResourceEmbedding() error = %v", err)
	}

	got, err := os.ReadFile(filePath)
	if err != nil {
		t.Fatalf("ReadFile() error = %v", err)
	}

	adjustedPSPF, err := adjustPSPFOffsets(pspfData, launcherSize, logger)
	if err != nil {
		t.Fatalf("adjustPSPFOffsets() error = %v", err)
	}
	want := append(append([]byte(nil), launcher...), adjustedPSPF...)
	if !bytes.Equal(got, want) {
		t.Fatalf("rewritten bundle mismatch")
	}
}

func TestBuilderGetFileSize(t *testing.T) {
	t.Parallel()

	tempDir := t.TempDir()
	filePath := filepath.Join(tempDir, "size.txt")
	content := []byte("flavorpack")
	if err := os.WriteFile(filePath, content, 0o644); err != nil {
		t.Fatalf("WriteFile() error = %v", err)
	}

	got, err := getFileSize(filePath)
	if err != nil {
		t.Fatalf("getFileSize() error = %v", err)
	}
	if want := int64(len(content)); got != want {
		t.Fatalf("getFileSize() = %d, want %d", got, want)
	}
}

func TestBuilderGetFileSizeReturnsErrorForMissingFile(t *testing.T) {
	t.Parallel()

	_, err := getFileSize(filepath.Join(t.TempDir(), "nonexistent.txt"))
	if err == nil {
		t.Fatal("expected error for nonexistent file")
	}
}

func TestBuilderCheckedArithmeticHelpers(t *testing.T) {
	t.Parallel()

	if got, err := int64ToUint64Checked(42, "value"); err != nil || got != 42 {
		t.Fatalf("int64ToUint64Checked() = (%d, %v), want (42, nil)", got, err)
	}
	if _, err := int64ToUint64Checked(-1, "value"); err == nil {
		t.Fatal("int64ToUint64Checked() should fail for negative values")
	}

	if got, err := intToUint32Checked(42, "value"); err != nil || got != 42 {
		t.Fatalf("intToUint32Checked() = (%d, %v), want (42, nil)", got, err)
	}
	if _, err := intToUint32Checked(math.MaxUint32+1, "value"); err == nil {
		t.Fatal("intToUint32Checked() should fail for oversized values")
	}

	if got, err := addUint64Checked(10, 20, "value"); err != nil || got != 30 {
		t.Fatalf("addUint64Checked() = (%d, %v), want (30, nil)", got, err)
	}
	if _, err := addUint64Checked(math.MaxUint64, 1, "value"); err == nil {
		t.Fatal("addUint64Checked() should fail on overflow")
	}

	if got, err := subtractUint64Checked(30, 10, "value"); err != nil || got != 20 {
		t.Fatalf("subtractUint64Checked() = (%d, %v), want (20, nil)", got, err)
	}
	if _, err := subtractUint64Checked(10, 20, "value"); err == nil {
		t.Fatal("subtractUint64Checked() should fail on underflow")
	}

	if got, err := multiplyUint64Checked(3, 7, "value"); err != nil || got != 21 {
		t.Fatalf("multiplyUint64Checked() = (%d, %v), want (21, nil)", got, err)
	}
	if _, err := multiplyUint64Checked(math.MaxUint64, 2, "value"); err == nil {
		t.Fatal("multiplyUint64Checked() should fail on overflow")
	}
}

func syntheticPELauncherForBuilderTest(t *testing.T, peOffset int) []byte {
	t.Helper()

	data := make([]byte, peOffset+4)
	data[0] = 'M'
	data[1] = 'Z'
	binary.LittleEndian.PutUint32(data[0x3C:0x40], uint32(peOffset))
	copy(data[peOffset:peOffset+4], []byte{'P', 'E', 0, 0})
	return data
}

func syntheticPSPFDataForBuilderTest(t *testing.T, launcherSize int64, metadataOffset, slotTableOffset, descriptorOffset uint64) ([]byte, int) {
	t.Helper()

	slotStart := int(slotTableOffset) - int(launcherSize)
	if slotStart < 0 {
		t.Fatalf("slot table start underflow: launcher=%d offset=%d", launcherSize, slotTableOffset)
	}

	totalSize := slotStart + SlotDescriptorSize + 32 + MagicTrailerSize
	data := make([]byte, totalSize)

	desc := (&SlotDescriptor{
		ID:     1,
		Offset: descriptorOffset,
		Size:   16,
	}).Pack()
	copy(data[slotStart:slotStart+SlotDescriptorSize], desc)

	index := &PSPFIndex{
		FormatVersion:   PSPFVersion,
		PackageSize:     uint64(totalSize) + uint64(launcherSize),
		LauncherSize:    uint64(launcherSize),
		MetadataOffset:  metadataOffset,
		MetadataSize:    16,
		SlotTableOffset: slotTableOffset,
		SlotTableSize:   SlotDescriptorSize,
		SlotCount:       1,
	}

	trailerStart := totalSize - MagicTrailerSize
	copy(data[trailerStart:trailerStart+4], PackageEmojiBytes)
	copy(data[trailerStart+4:trailerStart+4+IndexSize], index.Pack())
	copy(data[trailerStart+MagicTrailerSize-4:], MagicWandEmojiBytes)

	return data, slotStart
}

func mutateTrailerMagicForBuilderTest(t *testing.T, data []byte) []byte {
	t.Helper()

	mutated := append([]byte(nil), data...)
	trailerStart := len(mutated) - MagicTrailerSize
	mutated[trailerStart] = 'X'
	return mutated
}

func TestBuildWithLogLevelConsolePrefixesLines(t *testing.T) {
	oldBuildImpl := buildImpl
	t.Cleanup(func() { buildImpl = oldBuildImpl })
	buildImpl = func(_ *slog.Logger, _, _, _, _, _, _ string) {}

	t.Run("console mode adds prefix", func(t *testing.T) {
		var buf bytes.Buffer
		old := builderStderrWriter
		builderStderrWriter = &buf
		t.Cleanup(func() { builderStderrWriter = old })

		BuildWithLogLevel("m.json", "out.psp", "l.bin", "", "", "", "info")

		out := buf.String()
		if out == "" {
			t.Skip("no output captured — logger may be at warn level")
		}
		for _, line := range strings.Split(strings.TrimRight(out, "\n"), "\n") {
			if line == "" {
				continue
			}
			if !strings.HasPrefix(line, "🐹 ") {
				t.Fatalf("expected every line to start with '🐹 ', got: %q", line)
			}
		}
	})

	t.Run("json mode has no prefix", func(t *testing.T) {
		var buf bytes.Buffer
		old := builderStderrWriter
		builderStderrWriter = &buf
		t.Cleanup(func() { builderStderrWriter = old })

		BuildWithLogLevel("m.json", "out.psp", "l.bin", "", "", "", "json:info")

		out := buf.String()
		if strings.Contains(out, "🐹 ") {
			t.Fatalf("expected no 🐹 prefix in JSON output, got: %q", out)
		}
	})
}
