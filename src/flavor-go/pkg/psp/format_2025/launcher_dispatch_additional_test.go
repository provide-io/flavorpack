package format_2025

import (
	"encoding/json"
	"errors"
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"runtime"
	"strings"
	"testing"

	"github.com/provide-io/flavor/go/flavor/pkg/logging"
)

func buildLauncherTestBundle(t *testing.T) string {
	t.Helper()

	dir := t.TempDir()
	launcherPath := filepath.Join(dir, "launcher.sh")
	if err := os.WriteFile(launcherPath, []byte("#!/bin/sh\nexit 0\n"), 0o700); err != nil {
		t.Fatalf("WriteFile(launcher) error = %v", err)
	}

	manifestPath := filepath.Join(dir, "manifest.json")
	manifest := BuildOptions{
		Package: PackageConfig{
			Name:    "demo",
			Version: "1.0.0",
		},
		Execution: ExecutionConfig{
			Command: "/bin/true",
		},
	}
	manifestJSON, err := json.MarshalIndent(manifest, "", "  ")
	if err != nil {
		t.Fatalf("MarshalIndent() error = %v", err)
	}
	if err := os.WriteFile(manifestPath, manifestJSON, 0o600); err != nil {
		t.Fatalf("WriteFile(manifest) error = %v", err)
	}

	outputPath := testBundlePath(t, ".psp")
	BuildWithOptions(manifestPath, outputPath, launcherPath, "", "", "")
	if _, err := os.Stat(outputPath); err != nil {
		t.Fatalf("expected built bundle to exist: %v", err)
	}
	return outputPath
}

func filteredEnv(extra ...string) []string {
	exclude := map[string]struct{}{
		EnvLauncherCLI:      {},
		EnvExecMode:         {},
		EnvValidation:       {},
		EnvLauncherLogLevel: {},
		EnvLogLevel:         {},
		EnvLogPath:          {},
	}

	var env []string
	for _, kv := range os.Environ() {
		key, _, ok := strings.Cut(kv, "=")
		if !ok {
			continue
		}
		if _, skipped := exclude[key]; skipped {
			continue
		}
		env = append(env, kv)
	}
	return append(env, extra...)
}

func TestLaunchAndCLIHelpers(t *testing.T) {
	bundle := buildLauncherTestBundle(t)
	logPath := filepath.Join(t.TempDir(), "launcher.log")

	t.Setenv(EnvLauncherCLI, "1")
	t.Setenv(EnvLogPath, logPath)

	t.Run("default info path", func(t *testing.T) {
		Launch(bundle, nil)
	})

	t.Run("launcher env log level", func(t *testing.T) {
		t.Setenv(EnvLauncherLogLevel, "trace")
		LaunchWithLogLevel(bundle, []string{"info"}, "", "")
	})

	t.Run("global env log level", func(t *testing.T) {
		t.Setenv(EnvLogLevel, "debug")
		LaunchWithLogLevel(bundle, []string{"info"}, "", "")
	})

	t.Run("json metadata path", func(t *testing.T) {
		LaunchWithLogLevel(bundle, []string{"metadata"}, "json:debug", "cli")
	})

	if _, err := os.Stat(logPath); err != nil {
		t.Fatalf("expected launcher log file to be created: %v", err)
	}
}

func TestLaunchCLIPathsInSubprocess(t *testing.T) {
	bundle := buildLauncherTestBundle(t)

	cases := []struct {
		name    string
		args    []string
		wantErr bool
	}{
		{name: "verify", args: []string{"verify"}, wantErr: false},
		{name: "extract", args: []string{"extract", "0", filepath.Join(t.TempDir(), "extract")}, wantErr: true},
	}

	for _, tc := range cases {
		tc := tc
		t.Run(tc.name, func(t *testing.T) {
			cmd := exec.Command(os.Args[0], "-test.run=TestLaunchCLIErrorHelper")
			cmd.Env = filteredEnv(
				EnvLauncherSubprocess+"=1",
				EnvLauncherBundle+"="+bundle,
				EnvLauncherCLI+"=1",
				EnvLauncherArgs+"="+strings.Join(tc.args, "\x1f"),
			)

			output, err := cmd.CombinedOutput()
			if tc.wantErr {
				if err == nil {
					t.Fatalf("expected subprocess %s to fail", tc.name)
				}
				return
			}
			if err != nil {
				t.Fatalf("expected subprocess %s to succeed, got err=%v\n%s", tc.name, err, string(output))
			}
		})
	}
}

func TestLaunchCLIErrorHelper(t *testing.T) {
	if os.Getenv(EnvLauncherSubprocess) != "1" {
		return
	}

	bundle := os.Getenv(EnvLauncherBundle)
	args := strings.Split(os.Getenv(EnvLauncherArgs), "\x1f")
	LaunchWithLogLevel(bundle, args, "", "")
}

func TestLaunchExecModesInSubprocess(t *testing.T) {
	bundle := buildLauncherTestBundle(t)

	cases := []struct {
		name string
		mode string
	}{
		{name: "exec", mode: ""},
		{name: "spawn", mode: "spawn"},
	}

	for _, tc := range cases {
		tc := tc
		t.Run(tc.name, func(t *testing.T) {
			cmd := exec.Command(os.Args[0], "-test.run=TestLaunchExecModesHelper")
			cmd.Env = filteredEnv(
				EnvLauncherSubprocess+"=1",
				EnvLauncherBundle+"="+bundle,
				EnvValidation+"=none",
				EnvExecMode+"="+tc.mode,
			)

			output, err := cmd.CombinedOutput()
			if err != nil {
				t.Fatalf("subprocess %s failed: %v\n%s", tc.name, err, string(output))
			}
		})
	}
}

func TestLaunchExecModesHelper(t *testing.T) {
	if os.Getenv(EnvLauncherSubprocess) != "1" {
		return
	}

	bundle := os.Getenv(EnvLauncherBundle)
	_ = os.Unsetenv(EnvLauncherCLI)
	_ = os.Setenv(EnvValidation, os.Getenv(EnvValidation))
	_ = os.Setenv(EnvExecMode, os.Getenv(EnvExecMode))

	Launch(bundle, nil)
}

func TestLaunchSpawnExitHelper(t *testing.T) {
	if os.Getenv(EnvLauncherSpawnExitHelper) != "1" {
		return
	}

	os.Exit(7)
}

func TestExecBundleReplaceWithStubbedSyscallExec(t *testing.T) {
	bundle := buildLauncherTestBundle(t)
	logger := logging.NewNullLogger()

	oldSyscallExecFn := syscallExecFn
	t.Cleanup(func() {
		syscallExecFn = oldSyscallExecFn
	})

	called := false
	syscallExecFn = func(binary string, argv []string, envv []string) error {
		called = true
		if binary == "" {
			t.Fatal("expected binary to be resolved")
		}
		if len(argv) == 0 {
			t.Fatal("expected argv to be populated")
		}
		if len(envv) == 0 {
			t.Fatal("expected environment to be populated")
		}
		return errors.New("stub exec")
	}

	err := execBundleReplace(bundle, []string{"alpha"}, t.TempDir(), logger)
	if err == nil || !strings.Contains(err.Error(), "stub exec") {
		t.Fatalf("execBundleReplace() error = %v, want stub exec", err)
	}
	if !called {
		t.Fatal("expected stub syscall.Exec hook to be called")
	}
}

func TestExecBundleReplaceResolvesBinaryFromWorkenvPath(t *testing.T) {
	if runtime.GOOS == "windows" {
		t.Skip("exec mode path re-resolution is only exercised on non-Windows hosts")
	}

	t.Setenv(EnvValidation, "none")
	t.Setenv(EnvWorkenvCache, "false")
	t.Setenv(EnvCacheDir, t.TempDir())

	toolTar := buildTarArchiveWithDirAndFile(t, "bin", "tool", 0o755, []byte("#!/bin/sh\nexit 0\n"))
	bundle := buildMultiSlotBundleForTests(t, []multiSlotBundleSpec{
		{
			meta: SlotMetadata{
				ID:     "tool-slot",
				Target: "{workenv}",
			},
			storedData:   gzipDataForExecutionTests(t, toolTar),
			originalData: toolTar,
			operations:   []uint8{OP_TAR, OP_GZIP},
			permissions:  0o755,
		},
	}, Metadata{
		Format:        "PSPF/2025",
		FormatVersion: "2025.0",
		Package:       PackageInfo{Name: "demo", Version: "1.0.0"},
		Execution:     &ExecutionInfo{PrimarySlot: 0, Command: "tool"},
		Build:         &BuildInfo{Tool: "flavor-go"},
	})

	logger := logging.NewNullLogger()
	oldSyscallExecFn := syscallExecFn
	t.Cleanup(func() {
		syscallExecFn = oldSyscallExecFn
	})

	var gotBinary string
	syscallExecFn = func(binary string, argv []string, envv []string) error {
		gotBinary = binary
		return errors.New("stub exec")
	}

	err := execBundleReplace(bundle, nil, t.TempDir(), logger)
	if err == nil || !strings.Contains(err.Error(), "stub exec") {
		t.Fatalf("execBundleReplace() error = %v, want stub exec", err)
	}
	if gotBinary == "" {
		t.Fatal("expected syscallExecFn to receive a binary path")
	}
	if !filepath.IsAbs(gotBinary) {
		t.Fatalf("expected resolved binary path, got %q", gotBinary)
	}
	if filepath.Base(gotBinary) != "tool" {
		t.Fatalf("expected resolved tool binary, got %q", gotBinary)
	}
}

func TestLaunchWithLogLevelRunPropagatesSpawnExitCode(t *testing.T) {
	t.Setenv(EnvLauncherCLI, "1")
	t.Setenv(EnvValidation, "none")
	t.Setenv(EnvExecMode, "spawn")

	bundle := buildMultiSlotBundleForTests(t, []multiSlotBundleSpec{
		{
			meta: SlotMetadata{
				ID:     "run-slot",
				Target: "{workenv}",
			},
			storedData:   []byte("ok"),
			originalData: []byte("ok"),
			permissions:  0o644,
		},
	}, Metadata{
		Format:        "PSPF/2025",
		FormatVersion: "2025.0",
		Package:       PackageInfo{Name: "demo", Version: "1.0.0"},
		Execution: &ExecutionInfo{
			PrimarySlot: 0,
			Command:     fmt.Sprintf("%q -test.run=TestLaunchSpawnExitHelper", os.Args[0]),
			Environment: map[string]string{
				EnvLauncherSpawnExitHelper: "1",
			},
		},
		Build: &BuildInfo{Tool: "flavor-go"},
	})

	oldExitFn := osExitFn
	osExitFn = func(code int) {
		panic(struct{ code int }{code: code})
	}
	t.Cleanup(func() {
		osExitFn = oldExitFn
	})

	defer func() {
		r := recover()
		if r == nil {
			t.Fatal("expected LaunchWithLogLevel to terminate via osExitFn")
		}
		got, ok := r.(struct{ code int })
		if !ok {
			t.Fatalf("unexpected panic value: %#v", r)
		}
		if got.code != 7 {
			t.Fatalf("exit code = %d, want 7", got.code)
		}
	}()

	LaunchWithLogLevel(bundle, []string{"run"}, "", "")
}

func TestSpawnBundleReturnsStartFailure(t *testing.T) {
	t.Setenv(EnvValidation, "none")
	t.Setenv(EnvWorkenvCache, "false")

	bundle := buildMultiSlotBundleForTests(t, []multiSlotBundleSpec{
		{
			meta: SlotMetadata{
				ID:     "spawn-slot",
				Target: "{workenv}",
			},
			storedData:   []byte("ok"),
			originalData: []byte("ok"),
			permissions:  0o644,
		},
	}, Metadata{
		Format:        "PSPF/2025",
		FormatVersion: "2025.0",
		Package:       PackageInfo{Name: "demo", Version: "1.0.0"},
		Execution:     &ExecutionInfo{PrimarySlot: 0, Command: "/definitely/missing/binary"},
		Build:         &BuildInfo{Tool: "flavor-go"},
	})

	logger := logging.NewNullLogger()
	err := spawnBundle(bundle, []string{"arg1"}, t.TempDir(), logger)
	if err == nil {
		t.Fatal("expected spawnBundle() to fail when command cannot be started")
	}
	if !strings.Contains(err.Error(), "failed to start process") {
		t.Fatalf("spawnBundle() error = %v", err)
	}
}

func TestDetectLauncherAndBuilderTypes(t *testing.T) {
	oldArgs0 := os.Args[0]
	t.Cleanup(func() {
		os.Args[0] = oldArgs0
	})

	os.Args[0] = "/tmp/test-cli.pspf"
	if got := detectLauncherType("/tmp/anything.psp"); got != "go" {
		t.Fatalf("detectLauncherType() special case = %q, want go", got)
	}

	os.Args[0] = "/tmp/go-rust.pspf"
	if got := detectLauncherType("/tmp/anything.psp"); got != "rust" {
		t.Fatalf("detectLauncherType() special case = %q, want rust", got)
	}

	if got := detectBuilderType(&Metadata{}); got != "unknown/flavor-builder" {
		t.Fatalf("detectBuilderType() default = %q", got)
	}

	if got := detectBuilderType(&Metadata{Build: &BuildInfo{Tool: "flavor-go"}}); got != "flavor-go" {
		t.Fatalf("detectBuilderType() tool = %q", got)
	}
}
