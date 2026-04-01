package format_2025

import (
	"encoding/json"
	"errors"
	"os"
	"path/filepath"
	"testing"

	"github.com/hashicorp/go-hclog"
)

type launcherExitPanic struct {
	code int
}

func TestLaunchDelegates(t *testing.T) {
	bundlePath := buildLauncherBundle(t)
	t.Setenv("FLAVOR_LAUNCHER_CLI", "1")
	Launch(bundlePath, []string{"info"})
}

func TestLauncherCliHappyPaths(t *testing.T) {
	bundlePath := buildLauncherBundle(t)
	logger := hclog.NewNullLogger()

	t.Run("info", func(t *testing.T) {
		t.Setenv("FLAVOR_LAUNCHER_CLI", "1")
		LaunchWithLogLevel(bundlePath, []string{"info"}, "trace", "test")
	})

	t.Run("metadata", func(t *testing.T) {
		t.Setenv("FLAVOR_LAUNCHER_CLI", "1")
		LaunchWithLogLevel(bundlePath, []string{"metadata"}, "trace", "test")
	})

	t.Run("show-bundle-info", func(t *testing.T) {
		showBundleInfo(bundlePath, logger)
	})

	t.Run("show-metadata", func(t *testing.T) {
		showMetadata(bundlePath, logger)
	})
}

func TestLaunchWithLogLevelUsesEnvSettings(t *testing.T) {
	bundlePath := buildLauncherBundle(t)
	logPath := filepath.Join(t.TempDir(), "launcher.log")

	t.Setenv(EnvLauncherLogLevel, "json:debug")
	t.Setenv(EnvLogPath, logPath)
	t.Setenv("FLAVOR_LAUNCHER_CLI", "1")

	LaunchWithLogLevel(bundlePath, []string{"info"}, "", "")

	if data, err := os.ReadFile(logPath); err != nil {
		t.Fatalf("ReadFile(log path) error = %v", err)
	} else if len(data) == 0 {
		t.Fatal("expected log file to be written")
	}
}

func TestLaunchWithLogLevelCliArgumentErrors(t *testing.T) {
	bundlePath := buildLauncherBundle(t)

	t.Run("extract-missing-args", func(t *testing.T) {
		t.Setenv("FLAVOR_LAUNCHER_CLI", "1")
		launchWithExitStub(t, func() {
			LaunchWithLogLevel(bundlePath, []string{"extract"}, "", "")
		}, ExitInvalidArgs)
	})

	t.Run("unknown-command", func(t *testing.T) {
		t.Setenv("FLAVOR_LAUNCHER_CLI", "1")
		launchWithExitStub(t, func() {
			LaunchWithLogLevel(bundlePath, []string{"nope"}, "", "")
		}, ExitInvalidArgs)
	})
}

func TestLaunchWithLogLevelExecErrorClassification(t *testing.T) {
	bundlePath := buildLauncherBundle(t)
	logger := hclog.NewNullLogger()
	cwd := t.TempDir()

	tests := []struct {
		name  string
		err   error
		want  int
	}{
		{name: "pspf", err: errors.New("magic mismatch"), want: ExitPSPFError},
		{name: "extract", err: errors.New("slot issue"), want: ExitExtractionError},
		{name: "io", err: errors.New("file problem"), want: ExitIOError},
	}

	for _, tc := range tests {
		tc := tc
		t.Run(tc.name, func(t *testing.T) {
			oldExec := syscallExecFn
			syscallExecFn = func(string, []string, []string) error {
				return tc.err
			}
			t.Cleanup(func() {
				syscallExecFn = oldExec
			})

			launchWithExitStub(t, func() {
				if err := execBundleReplace(bundlePath, nil, cwd, logger); err == nil {
					t.Fatal("expected execBundleReplace to return an error when exec is stubbed")
				}
				LaunchWithLogLevel(bundlePath, nil, "", "")
			}, tc.want)
		})
	}
}

func TestExecBundleReplaceNilErrorBranch(t *testing.T) {
	bundlePath := buildLauncherBundle(t)
	logger := hclog.NewNullLogger()
	cwd := t.TempDir()

	oldExec := syscallExecFn
	syscallExecFn = func(string, []string, []string) error {
		return nil
	}
	t.Cleanup(func() {
		syscallExecFn = oldExec
	})

	if err := execBundleReplace(bundlePath, nil, cwd, logger); err == nil {
		t.Fatal("expected execBundleReplace to fail when syscall.Exec returns nil")
	}
}

func TestLaunchWithLogLevelSpawnMode(t *testing.T) {
	bundlePath := buildLauncherBundle(t)

	t.Setenv(EnvExecMode, "spawn")
	launchWithExitStub(t, func() {
		LaunchWithLogLevel(bundlePath, nil, "", "")
	}, 0)
}

func TestSpawnBundlePropagatesChildFailure(t *testing.T) {
	bundlePath := buildLauncherBundleWithCommand(t, "/bin/false")
	logger := hclog.NewNullLogger()
	cwd := t.TempDir()

	t.Setenv(EnvExecMode, "spawn")
	launchWithExitStub(t, func() {
		if err := execBundle(bundlePath, nil, cwd, logger); err != nil {
			t.Fatalf("execBundle() error = %v", err)
		}
	}, 1)
}

func TestLauncherCliExitPaths(t *testing.T) {
	bundlePath := buildLauncherBundle(t)
	logger := hclog.NewNullLogger()

	t.Run("verify", func(t *testing.T) {
		launchWithExitStub(t, func() {
			verifyBundle(bundlePath, logger)
		}, 1)
	})

	t.Run("extract", func(t *testing.T) {
		launchWithExitStub(t, func() {
			extractSlot(bundlePath, "0", t.TempDir(), logger)
		}, 1)
	})
}

func TestLauncherExecutionBranches(t *testing.T) {
	bundlePath := buildLauncherBundle(t)
	logger := hclog.NewNullLogger()
	cwd := t.TempDir()

	t.Run("exec-replace", func(t *testing.T) {
		oldExec := syscallExecFn
		syscallExecFn = func(string, []string, []string) error {
			return errors.New("stub exec")
		}
		t.Cleanup(func() {
			syscallExecFn = oldExec
		})

		if err := execBundleReplace(bundlePath, nil, cwd, logger); err == nil {
			t.Fatal("expected execBundleReplace to return an error when exec is stubbed")
		}
	})

	t.Run("spawn", func(t *testing.T) {
		launchWithExitStub(t, func() {
			t.Setenv(EnvExecMode, "spawn")
			if err := execBundle(bundlePath, nil, cwd, logger); err != nil {
				t.Fatalf("execBundle() error = %v", err)
			}
		}, 0)
	})
}

func TestDetectBuilderTypeFallback(t *testing.T) {
	if got := detectBuilderType(&Metadata{}); got != "unknown/flavor-builder" {
		t.Fatalf("detectBuilderType() = %q, want unknown/flavor-builder", got)
	}
}

func launchWithExitStub(t *testing.T, fn func(), wantCode int) {
	t.Helper()

	oldExit := exitFn
	exitFn = func(code int) {
		panic(launcherExitPanic{code: code})
	}
	t.Cleanup(func() {
		exitFn = oldExit
	})

	defer func() {
		r := recover()
		if r == nil {
			t.Fatalf("expected exit code %d, got no panic", wantCode)
		}
		panicValue, ok := r.(launcherExitPanic)
		if !ok {
			t.Fatalf("unexpected panic type: %T %#v", r, r)
		}
		if panicValue.code != wantCode {
			t.Fatalf("unexpected exit code: got %d want %d", panicValue.code, wantCode)
		}
	}()

	fn()
	t.Fatalf("expected exit code %d, got normal return", wantCode)
}

func buildLauncherBundle(t *testing.T) string {
	t.Helper()
	return buildLauncherBundleWithCommand(t, "/bin/true")
}

func buildLauncherBundleWithCommand(t *testing.T, command string) string {
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
			Command: command,
		},
	}
	manifestJSON, err := json.MarshalIndent(manifest, "", "  ")
	if err != nil {
		t.Fatalf("MarshalIndent() error = %v", err)
	}
	if err := os.WriteFile(manifestPath, manifestJSON, 0o600); err != nil {
		t.Fatalf("WriteFile(manifest) error = %v", err)
	}

	outputPath := filepath.Join(dir, "bundle.psp")
	BuildWithOptions(manifestPath, outputPath, launcherPath, "", "", "")

	if _, err := os.Stat(outputPath); err != nil {
		t.Fatalf("expected built bundle to exist: %v", err)
	}

	return outputPath
}

func TestDetectBuilderTypeWithValue(t *testing.T) {
	if got := detectBuilderType(&Metadata{Build: &BuildInfo{Tool: "go"}}); got != "go" {
		t.Fatalf("detectBuilderType() = %q, want go", got)
	}
}

func TestShowBundleInfoAndMetadataDoNotExit(t *testing.T) {
	bundlePath := buildLauncherBundle(t)
	logger := hclog.NewNullLogger()

	showBundleInfo(bundlePath, logger)
	showMetadata(bundlePath, logger)
}
