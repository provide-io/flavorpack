package format_2025

import (
	"bytes"
	"compress/gzip"
	"crypto/sha256"
	"encoding/binary"
	"encoding/json"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"testing"

	"github.com/hashicorp/go-hclog"
)

type multiSlotBundleSpec struct {
	meta         SlotMetadata
	storedData   []byte
	originalData []byte
	operations   []uint8
	permissions  uint16
}

func gzipDataForExecutionTests(t *testing.T, src []byte) []byte {
	t.Helper()

	var buf bytes.Buffer
	gw := gzip.NewWriter(&buf)
	if _, err := gw.Write(src); err != nil {
		t.Fatalf("gzip.Write() error = %v", err)
	}
	if err := gw.Close(); err != nil {
		t.Fatalf("gzip.Close() error = %v", err)
	}
	return buf.Bytes()
}

func buildMultiSlotBundleForTests(t *testing.T, specs []multiSlotBundleSpec, metadata Metadata) string {
	t.Helper()

	if metadata.Format == "" {
		metadata.Format = "PSPF/2025"
	}
	if metadata.FormatVersion == "" {
		metadata.FormatVersion = "2025.0"
	}
	if metadata.Package.Name == "" {
		metadata.Package.Name = "demo"
	}
	if metadata.Package.Version == "" {
		metadata.Package.Version = "1.0.0"
	}
	if metadata.Execution == nil {
		metadata.Execution = &ExecutionInfo{PrimarySlot: 0, Command: "/bin/true"}
	}
	if metadata.Build == nil {
		metadata.Build = &BuildInfo{Tool: "flavor-go"}
	}
	if len(metadata.Slots) == 0 {
		metadata.Slots = make([]SlotMetadata, len(specs))
	}

	bundlePath := testBundlePath(t, ".psp")
	f, err := os.Create(bundlePath)
	if err != nil {
		t.Fatalf("Create() error = %v", err)
	}
	defer func() {
		if err := f.Close(); err != nil {
			t.Fatalf("Close() error = %v", err)
		}
	}()

	offset := 0
	slotDescriptors := make([]SlotDescriptor, 0, len(specs))
	for i, spec := range specs {
		stored := spec.storedData
		if stored == nil {
			stored = []byte{}
		}
		original := spec.originalData
		if original == nil {
			original = stored
		}
		if spec.meta.ID == "" {
			spec.meta.ID = strings.TrimSuffix(filepath.Base(bundlePath), ".psp") + "-slot"
		}
		if spec.meta.Target == "" {
			spec.meta.Target = "{workenv}"
		}
		spec.meta.Slot = i
		spec.meta.Size = int64(len(original))
		metadata.Slots[i] = spec.meta

		if _, err := f.Write(stored); err != nil {
			t.Fatalf("Write(slot %d data) error = %v", i, err)
		}

		checksum := sha256.Sum256(stored)
		desc := SlotDescriptor{
			ID:           uint64(i + 1),
			NameHash:     HashName(spec.meta.ID),
			Offset:       uint64(offset),
			Size:         uint64(len(stored)),
			OriginalSize: uint64(len(original)),
			Operations:   PackOperations(spec.operations),
			Checksum:     binary.LittleEndian.Uint64(checksum[:8]),
		}
		desc.SetPermissions(spec.permissions)
		slotDescriptors = append(slotDescriptors, desc)
		offset += len(stored)
	}

	slotTableOffset := uint64(offset)
	for _, desc := range slotDescriptors {
		if _, err := f.Write(desc.Pack()); err != nil {
			t.Fatalf("Write(slot descriptor) error = %v", err)
		}
	}

	metadataJSON, err := json.MarshalIndent(metadata, "", "  ")
	if err != nil {
		t.Fatalf("MarshalIndent(metadata) error = %v", err)
	}
	gzMeta := gzipDataForExecutionTests(t, metadataJSON)
	metadataOffset := slotTableOffset + uint64(len(slotDescriptors))*SlotDescriptorSize
	if _, err := f.Write(gzMeta); err != nil {
		t.Fatalf("Write(metadata) error = %v", err)
	}

	index := &PSPFIndex{
		FormatVersion:   PSPFVersion,
		PackageSize:     uint64(offset) + uint64(len(slotDescriptors))*SlotDescriptorSize + uint64(len(gzMeta)) + MagicTrailerSize,
		LauncherSize:    0,
		MetadataOffset:  metadataOffset,
		MetadataSize:    uint64(len(gzMeta)),
		SlotTableOffset: slotTableOffset,
		SlotTableSize:   uint64(len(slotDescriptors)) * SlotDescriptorSize,
		SlotCount:       uint32(len(slotDescriptors)),
	}
	metaHash := sha256.Sum256(gzMeta)
	copy(index.MetadataChecksum[:], metaHash[:])

	trailer := make([]byte, MagicTrailerSize)
	copy(trailer[0:4], PackageEmojiBytes)
	copy(trailer[4:4+IndexSize], index.Pack())
	copy(trailer[4+IndexSize:], MagicWandEmojiBytes)
	if _, err := f.Write(trailer); err != nil {
		t.Fatalf("Write(trailer) error = %v", err)
	}

	return bundlePath
}

// This test only proves the non-Windows/appended-EOF path. The PE-resource
// extraction branch is Windows-only and is validated on Windows runners.
func TestPrepareBundlePathReturnsExecutableWithoutResource(t *testing.T) {
	t.Parallel()

	bundle := buildSingleSlotBundleForTests(t, []byte("bundle"), []byte("bundle"), nil, SlotMetadata{
		ID:     "prepare",
		Target: "{workenv}",
	}, 0, false)

	path, cleanup, err := prepareBundlePath(bundle, hclog.NewNullLogger())
	if err != nil {
		t.Fatalf("prepareBundlePath() error = %v", err)
	}
	if cleanup != nil {
		t.Fatal("expected no cleanup function when bundle is not a PE resource")
	}
	if path != bundle {
		t.Fatalf("prepareBundlePath() = %q, want %q", path, bundle)
	}
}

func TestRunBundleWithCwdPreparesWorkenvAndCommands(t *testing.T) {
	cacheRoot := t.TempDir()
	t.Setenv("FLAVOR_CACHE_DIR", cacheRoot)
	t.Setenv(EnvValidation, "none")
	t.Setenv(EnvWorkenvCache, "false")

	metadata := Metadata{
		Format:        "PSPF/2025",
		FormatVersion: "2025.0",
		Package: PackageInfo{
			Name:    "demo",
			Version: "1.0.0",
		},
		Workenv: &WorkenvInfo{
			Directories: []DirectorySpec{
				{Path: "{workenv}/metadata", Mode: "0700"},
				{Path: "{workenv}/nested", Mode: "0755"},
			},
		},
		SetupCommands: []interface{}{
			map[string]interface{}{
				"type":    "write_file",
				"path":    "{workenv}/metadata/generated.txt",
				"content": "hello {package_name} {version}",
				"mode":    float64(0o640),
			},
			map[string]interface{}{
				"type":    "enumerate_and_execute",
				"command": "/bin/true",
				"enumerate": map[string]interface{}{
					"path":    "{workenv}/metadata",
					"pattern": "generated.txt",
				},
			},
			"/bin/true",
			123,
		},
		Runtime: &RuntimeInfo{
			Env: map[string]interface{}{
				"set": map[string]interface{}{
					"RUNTIME_FLAG": "on",
				},
			},
		},
		Execution: &ExecutionInfo{
			PrimarySlot: 0,
			Command:     "/bin/true {slot:0} {slot:1} {workenv}",
			Environment: map[string]string{
				"CUSTOM_SLOT": "{slot:0}",
			},
		},
		Build: &BuildInfo{Tool: "flavor-go"},
	}

	bundle := buildMultiSlotBundleForTests(t, []multiSlotBundleSpec{
		{
			meta: SlotMetadata{
				ID:     "slot-alpha",
				Target: "{workenv}",
			},
			storedData:   []byte("alpha"),
			originalData: []byte("alpha"),
			permissions:  0o644,
		},
		{
			meta: SlotMetadata{
				ID:     "slot-beta",
				Target: "{workenv}",
			},
			storedData:   []byte("beta"),
			originalData: []byte("beta"),
			permissions:  0o600,
		},
	}, metadata)

	userCwd := t.TempDir()
	logger := hclog.NewNullLogger()

	cmd, err := runBundleWithCwd(bundle, []string{"--flag"}, userCwd, logger)
	if err != nil {
		t.Fatalf("runBundleWithCwd() error = %v", err)
	}
	if cmd == nil {
		t.Fatal("expected exec.Cmd")
	}
	if cmd.Dir != userCwd {
		t.Fatalf("cmd.Dir = %q, want %q", cmd.Dir, userCwd)
	}
	if len(cmd.Env) == 0 {
		t.Fatal("expected command environment to be populated")
	}

	paths := NewWorkenvPaths(cacheRoot, bundle)
	workenvDir := paths.Workenv()

	if _, err := os.Stat(workenvDir); err != nil {
		t.Fatalf("expected workenv directory to exist: %v", err)
	}
	if _, err := os.Stat(filepath.Join(workenvDir, "slot_0_slot-alpha")); err != nil {
		t.Fatalf("expected first slot file to exist: %v", err)
	}
	if _, err := os.Stat(filepath.Join(workenvDir, "slot_1_slot-beta")); err != nil {
		t.Fatalf("expected second slot file to exist: %v", err)
	}

	firstSlot, err := os.ReadFile(filepath.Join(workenvDir, "slot_0_slot-alpha"))
	if err != nil {
		t.Fatalf("ReadFile(first slot) error = %v", err)
	}
	if string(firstSlot) != "alpha" {
		t.Fatalf("first slot contents = %q, want %q", string(firstSlot), "alpha")
	}

	secondSlot, err := os.ReadFile(filepath.Join(workenvDir, "slot_1_slot-beta"))
	if err != nil {
		t.Fatalf("ReadFile(second slot) error = %v", err)
	}
	if string(secondSlot) != "beta" {
		t.Fatalf("second slot contents = %q, want %q", string(secondSlot), "beta")
	}

	if _, err := os.Stat(filepath.Join(paths.Metadata(), "package", "psp.json")); err != nil {
		t.Fatalf("expected package metadata to be written: %v", err)
	}
	if _, err := os.Stat(filepath.Join(workenvDir, "metadata", "generated.txt")); err != nil {
		t.Fatalf("expected setup command output to exist: %v", err)
	}

	env := strings.Join(cmd.Env, "\n")
	if !strings.Contains(env, "FLAVOR_WORKENV="+workenvDir) {
		t.Fatalf("expected FLAVOR_WORKENV to point at workenv, env=%q", env)
	}
	if !strings.Contains(env, "RUNTIME_FLAG=on") {
		t.Fatalf("expected runtime env entry in cmd.Env, env=%q", env)
	}
	if !strings.Contains(env, "CUSTOM_SLOT=") || !strings.Contains(env, "slot_0_slot-alpha") {
		t.Fatalf("expected slot placeholder expansion in cmd.Env, env=%q", env)
	}
}

func TestRunBundleWithCwdMergesTarSlotDirectories(t *testing.T) {
	cacheRoot := t.TempDir()
	t.Setenv("FLAVOR_CACHE_DIR", cacheRoot)
	t.Setenv(EnvValidation, "none")
	t.Setenv(EnvWorkenvCache, "false")

	sharedTar0 := buildTarArchiveWithDirAndFile(t, "shared", "first.txt", 0o644, []byte("first"))
	sharedTar1 := buildTarArchiveWithDirAndFile(t, "shared", "second.txt", 0o644, []byte("second"))

	bundle := buildMultiSlotBundleForTests(t, []multiSlotBundleSpec{
		{
			meta: SlotMetadata{
				ID:     "tar-alpha",
				Target: "{workenv}",
			},
			storedData:   gzipDataForExecutionTests(t, sharedTar0),
			originalData: sharedTar0,
			operations:   []uint8{OP_TAR, OP_GZIP},
			permissions:  0o755,
		},
		{
			meta: SlotMetadata{
				ID:     "tar-beta",
				Target: "{workenv}",
			},
			storedData:   gzipDataForExecutionTests(t, sharedTar1),
			originalData: sharedTar1,
			operations:   []uint8{OP_TAR, OP_GZIP},
			permissions:  0o755,
		},
	}, Metadata{
		Format:        "PSPF/2025",
		FormatVersion: "2025.0",
		Package: PackageInfo{
			Name:    "demo",
			Version: "1.0.0",
		},
		Execution: &ExecutionInfo{PrimarySlot: 0, Command: "/bin/true"},
		Build:     &BuildInfo{Tool: "flavor-go"},
	})

	logger := hclog.NewNullLogger()
	if _, err := runBundleWithCwd(bundle, []string{"--flag"}, t.TempDir(), logger); err != nil {
		t.Fatalf("runBundleWithCwd() error = %v", err)
	}

	paths := NewWorkenvPaths(cacheRoot, bundle)
	workenvDir := paths.Workenv()

	first, err := os.ReadFile(filepath.Join(workenvDir, "shared", "first.txt"))
	if err != nil {
		t.Fatalf("ReadFile(first tar slot) error = %v", err)
	}
	if string(first) != "first" {
		t.Fatalf("first tar slot contents = %q, want %q", string(first), "first")
	}

	second, err := os.ReadFile(filepath.Join(workenvDir, "shared", "second.txt"))
	if err != nil {
		t.Fatalf("ReadFile(second tar slot) error = %v", err)
	}
	if string(second) != "second" {
		t.Fatalf("second tar slot contents = %q, want %q", string(second), "second")
	}
}

func TestExtractAndMergeSlotsToWorkenvMergesContentAndWritesMetadata(t *testing.T) {
	cacheRoot := t.TempDir()
	t.Setenv("FLAVOR_CACHE_DIR", cacheRoot)

	slotZeroTar := buildTarArchiveWithDirAndFile(t, "bin", "tool.sh", 0o755, []byte("#!/bin/sh\nexit 0\n"))
	slotOneTar := buildTarArchiveWithDirAndFile(t, "shared", "payload.txt", 0o644, []byte("payload"))

	metadata := Metadata{
		Format:        "PSPF/2025",
		FormatVersion: "2025.0",
		Package: PackageInfo{
			Name:    "demo",
			Version: "1.0.0",
		},
		Execution: &ExecutionInfo{PrimarySlot: 0, Command: "/bin/true"},
		Build:     &BuildInfo{Tool: "flavor-go"},
	}

	bundle := buildMultiSlotBundleForTests(t, []multiSlotBundleSpec{
		{
			meta: SlotMetadata{
				ID:     "slot-zero",
				Target: "{workenv}",
			},
			storedData:   gzipDataForExecutionTests(t, slotZeroTar),
			originalData: slotZeroTar,
			operations:   []uint8{OP_TAR, OP_GZIP},
			permissions:  0o755,
		},
		{
			meta: SlotMetadata{
				ID:     "slot-one",
				Target: "{workenv}",
			},
			storedData:   gzipDataForExecutionTests(t, slotOneTar),
			originalData: slotOneTar,
			operations:   []uint8{OP_TAR, OP_GZIP},
			permissions:  0o755,
		},
	}, metadata)

	logger := hclog.NewNullLogger()
	reader, err := NewReaderWithLogger(bundle, logger)
	if err != nil {
		t.Fatalf("NewReaderWithLogger() error = %v", err)
	}
	t.Cleanup(func() {
		if err := reader.Close(); err != nil {
			t.Fatalf("Close() error = %v", err)
		}
	})

	index, err := reader.ReadIndex()
	if err != nil {
		t.Fatalf("ReadIndex() error = %v", err)
	}
	readMetadata, err := reader.ReadMetadata()
	if err != nil {
		t.Fatalf("ReadMetadata() error = %v", err)
	}

	paths := NewWorkenvPaths(cacheRoot, bundle)
	slotPaths, err := extractAndMergeSlotsToWorkenv(reader, readMetadata, paths, index, logger)
	if err != nil {
		t.Fatalf("extractAndMergeSlotsToWorkenv() error = %v", err)
	}
	if len(slotPaths) != 2 {
		t.Fatalf("slot path count = %d, want 2", len(slotPaths))
	}
	if slotPaths[0] == "" || slotPaths[1] == "" {
		t.Fatalf("expected extracted slot paths, got %#v", slotPaths)
	}

	workenvDir := paths.Workenv()
	slotZeroFile := filepath.Join(workenvDir, "bin", "tool.sh")
	if _, err := os.Stat(slotZeroFile); err != nil {
		t.Fatalf("expected slot 0 content in workenv root: %v", err)
	}
	slotOneFile := filepath.Join(workenvDir, "shared", "payload.txt")
	slotOneContent, err := os.ReadFile(slotOneFile)
	if err != nil {
		t.Fatalf("ReadFile(slot one payload) error = %v", err)
	}
	if string(slotOneContent) != "payload" {
		t.Fatalf("slot one payload = %q, want %q", string(slotOneContent), "payload")
	}

	metadataBytes, err := os.ReadFile(filepath.Join(paths.Metadata(), "package", "psp.json"))
	if err != nil {
		t.Fatalf("ReadFile(psp metadata) error = %v", err)
	}
	if !bytes.Contains(metadataBytes, []byte(`"name": "demo"`)) {
		t.Fatalf("expected package metadata JSON, got %q", string(metadataBytes))
	}

	tempDirs, err := paths.ListTempExtractions()
	if err != nil {
		t.Fatalf("ListTempExtractions() error = %v", err)
	}
	if len(tempDirs) != 0 {
		t.Fatalf("expected temp extraction cleanup, found %v", tempDirs)
	}
	if _, err := os.Stat(paths.IndexMetadataFile()); err != nil {
		t.Fatalf("expected index metadata file to be saved: %v", err)
	}
}

func TestExtractAndMergeSlotsToWorkenvCleansUpTempDirOnExtractionFailure(t *testing.T) {
	cacheRoot := t.TempDir()

	metadata := Metadata{
		Format:        "PSPF/2025",
		FormatVersion: "2025.0",
		Package: PackageInfo{
			Name:    "demo",
			Version: "1.0.0",
		},
		Execution: &ExecutionInfo{PrimarySlot: 0, Command: "/bin/true"},
		Build:     &BuildInfo{Tool: "flavor-go"},
	}

	bundle := buildMultiSlotBundleForTests(t, []multiSlotBundleSpec{
		{
			meta: SlotMetadata{
				ID:     "bad-slot",
				Target: "{workenv}",
			},
			storedData:   []byte("not really bzip2"),
			originalData: []byte("not really bzip2"),
			operations:   []uint8{OP_BZIP2},
			permissions:  0o644,
		},
	}, metadata)

	logger := hclog.NewNullLogger()
	reader, err := NewReaderWithLogger(bundle, logger)
	if err != nil {
		t.Fatalf("NewReaderWithLogger() error = %v", err)
	}
	t.Cleanup(func() {
		if err := reader.Close(); err != nil {
			t.Fatalf("Close() error = %v", err)
		}
	})

	index, err := reader.ReadIndex()
	if err != nil {
		t.Fatalf("ReadIndex() error = %v", err)
	}
	readMetadata, err := reader.ReadMetadata()
	if err != nil {
		t.Fatalf("ReadMetadata() error = %v", err)
	}

	paths := NewWorkenvPaths(cacheRoot, bundle)
	if _, err := extractAndMergeSlotsToWorkenv(reader, readMetadata, paths, index, logger); err == nil {
		t.Fatal("expected extractAndMergeSlotsToWorkenv() to fail for unsupported operation")
	}

	tempDirs, err := paths.ListTempExtractions()
	if err != nil {
		t.Fatalf("ListTempExtractions() error = %v", err)
	}
	if len(tempDirs) != 0 {
		t.Fatalf("expected temp extraction cleanup after failure, found %v", tempDirs)
	}
}

func TestExtractAndMergeSlotsToWorkenvFailsWhenTempExtractionCannotBeCreated(t *testing.T) {
	fileRoot := filepath.Join(t.TempDir(), "cache-root-file")
	if err := os.WriteFile(fileRoot, []byte("not a directory"), 0o600); err != nil {
		t.Fatalf("WriteFile(cache root) error = %v", err)
	}

	bundle := buildMultiSlotBundleForTests(t, []multiSlotBundleSpec{
		{
			meta: SlotMetadata{
				ID:     "temp-failure",
				Target: "{workenv}",
			},
			storedData:   []byte("content"),
			originalData: []byte("content"),
		},
	}, Metadata{
		Format:        "PSPF/2025",
		FormatVersion: "2025.0",
		Package: PackageInfo{
			Name:    "demo",
			Version: "1.0.0",
		},
		Execution: &ExecutionInfo{PrimarySlot: 0, Command: "/bin/true"},
		Build:     &BuildInfo{Tool: "flavor-go"},
	})

	t.Setenv("FLAVOR_CACHE_DIR", fileRoot)

	logger := hclog.NewNullLogger()
	reader, err := NewReaderWithLogger(bundle, logger)
	if err != nil {
		t.Fatalf("NewReaderWithLogger() error = %v", err)
	}
	t.Cleanup(func() {
		if err := reader.Close(); err != nil {
			t.Fatalf("Close() error = %v", err)
		}
	})

	index, err := reader.ReadIndex()
	if err != nil {
		t.Fatalf("ReadIndex() error = %v", err)
	}
	readMetadata, err := reader.ReadMetadata()
	if err != nil {
		t.Fatalf("ReadMetadata() error = %v", err)
	}

	paths := NewWorkenvPaths(fileRoot, bundle)
	if _, err := extractAndMergeSlotsToWorkenv(reader, readMetadata, paths, index, logger); err == nil {
		t.Fatal("expected extractAndMergeSlotsToWorkenv() to fail when temp extraction dir cannot be created")
	}
}

func TestExecBundleSpawnMode(t *testing.T) {
	bundle := buildLauncherTestBundle(t)
	t.Setenv(EnvValidation, "none")
	t.Setenv(EnvExecMode, "spawn")

	logger := hclog.NewNullLogger()
	oldOsExitFn := osExitFn
	t.Cleanup(func() {
		osExitFn = oldOsExitFn
	})

	type exitSentinel struct{}
	osExitFn = func(code int) {
		if code != 0 {
			t.Fatalf("expected zero exit from spawnBundle, got %d", code)
		}
		panic(exitSentinel{})
	}

	defer func() {
		r := recover()
		if r == nil {
			t.Fatal("expected spawnBundle to terminate via osExitFn")
		}
		if _, ok := r.(exitSentinel); !ok {
			t.Fatalf("unexpected panic value: %T", r)
		}
	}()

	execBundle(bundle, nil, t.TempDir(), logger)
}

func TestRunBundleWithCwdUsesValidCache(t *testing.T) {
	cacheRoot := t.TempDir()
	t.Setenv("FLAVOR_CACHE_DIR", cacheRoot)
	t.Setenv(EnvValidation, "none")
	t.Setenv(EnvWorkenvCache, "true")

	bundle := buildSingleSlotBundleForTests(t, []byte("cached"), []byte("cached"), nil, SlotMetadata{
		ID:     "cached-slot",
		Target: "{workenv}/bin/app.txt",
	}, 0o644, false)

	logger := hclog.NewNullLogger()
	reader, err := NewReaderWithLogger(bundle, logger)
	if err != nil {
		t.Fatalf("NewReaderWithLogger() error = %v", err)
	}
	index, err := reader.ReadIndex()
	if err != nil {
		t.Fatalf("ReadIndex() error = %v", err)
	}
	if err := reader.Close(); err != nil {
		t.Fatalf("Close() error = %v", err)
	}

	paths := NewWorkenvPaths(cacheRoot, bundle)
	if err := os.MkdirAll(paths.Workenv(), 0o755); err != nil {
		t.Fatalf("MkdirAll(workenv) error = %v", err)
	}
	if err := os.MkdirAll(filepath.Join(paths.Workenv(), "bin"), 0o755); err != nil {
		t.Fatalf("MkdirAll(bin) error = %v", err)
	}
	if err := os.WriteFile(filepath.Join(paths.Workenv(), "bin", "app.txt"), []byte("cached"), 0o644); err != nil {
		t.Fatalf("WriteFile(cached payload) error = %v", err)
	}
	if err := os.MkdirAll(filepath.Dir(paths.CompleteFile()), 0o755); err != nil {
		t.Fatalf("MkdirAll(complete dir) error = %v", err)
	}
	if err := os.WriteFile(paths.CompleteFile(), []byte("done"), 0o600); err != nil {
		t.Fatalf("WriteFile(complete) error = %v", err)
	}
	if err := savePackageChecksum(paths, index.IndexChecksum, logger); err != nil {
		t.Fatalf("savePackageChecksum() error = %v", err)
	}

	cmd, err := runBundleWithCwd(bundle, []string{"--flag"}, t.TempDir(), logger)
	if err != nil {
		t.Fatalf("runBundleWithCwd() error = %v", err)
	}
	if cmd == nil {
		t.Fatal("expected exec.Cmd")
	}
	if cmd.Path == "" {
		t.Fatal("expected resolved command path")
	}
}

func TestLaunchWithLogLevelCLIBranches(t *testing.T) {
	bundle := buildSingleSlotBundleForTests(t, []byte("cli"), []byte("cli"), nil, SlotMetadata{
		ID:     "cli-slot",
		Target: "{workenv}",
	}, 0, false)

	cases := []struct {
		name    string
		args    []string
		env     []string
		wantErr bool
	}{
		{name: "help", args: []string{"help"}, env: []string{"FLAVOR_LAUNCHER_CLI=1"}, wantErr: false},
		{name: "unknown command", args: []string{"bogus"}, env: []string{"FLAVOR_LAUNCHER_CLI=1"}, wantErr: true},
		{name: "missing extract args", args: []string{"extract"}, env: []string{"FLAVOR_LAUNCHER_CLI=1"}, wantErr: true},
		{name: "run command", args: []string{"run"}, env: []string{"FLAVOR_LAUNCHER_CLI=1", "FLAVOR_VALIDATION=none", "FLAVOR_EXEC_MODE=spawn"}, wantErr: false},
	}

	for _, tc := range cases {
		tc := tc
		t.Run(tc.name, func(t *testing.T) {
			cmd := exec.Command(os.Args[0], "-test.run=TestLaunchWithLogLevelCLIHelper")
			cmd.Env = filteredEnv(
				append(tc.env,
					"FLAVOR_LAUNCHER_SUBPROCESS=1",
					"FLAVOR_LAUNCHER_BUNDLE="+bundle,
					"FLAVOR_LAUNCHER_ARGS="+strings.Join(tc.args, "\x1f"),
				)...,
			)

			output, err := cmd.CombinedOutput()
			if tc.wantErr {
				if err == nil {
					t.Fatalf("expected %s subprocess to fail\n%s", tc.name, string(output))
				}
				return
			}
			if err != nil {
				t.Fatalf("expected %s subprocess to succeed: %v\n%s", tc.name, err, string(output))
			}
		})
	}
}

func TestLaunchWithLogLevelCLIHelper(t *testing.T) {
	if os.Getenv("FLAVOR_LAUNCHER_SUBPROCESS") != "1" {
		return
	}

	bundle := os.Getenv("FLAVOR_LAUNCHER_BUNDLE")
	args := strings.Split(os.Getenv("FLAVOR_LAUNCHER_ARGS"), "\x1f")
	_ = os.Setenv(EnvValidation, os.Getenv("FLAVOR_VALIDATION"))
	_ = os.Setenv(EnvExecMode, os.Getenv("FLAVOR_EXEC_MODE"))
	LaunchWithLogLevel(bundle, args, "", "")
}

func TestExecutionQuietRemovalHelpers(t *testing.T) {
	t.Parallel()

	logger := hclog.NewNullLogger()
	dir := t.TempDir()
	filePath := filepath.Join(dir, "gone.txt")
	if err := os.WriteFile(filePath, []byte("bye"), 0o600); err != nil {
		t.Fatalf("WriteFile() error = %v", err)
	}

	removeFileQuietly(filePath, "test", logger)
	if _, err := os.Stat(filePath); !os.IsNotExist(err) {
		t.Fatalf("expected file removal, err=%v", err)
	}

	removeAllQuietly(filepath.Join(dir, "missing-dir"), "test", logger)
}
