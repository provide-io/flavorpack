package format_2025

import (
	"encoding/json"
	"errors"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"testing"

	"github.com/hashicorp/go-hclog"
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
		"FLAVOR_LAUNCHER_CLI":       {},
		"FLAVOR_EXEC_MODE":          {},
		"FLAVOR_VALIDATION":         {},
		"FLAVOR_LAUNCHER_LOG_LEVEL": {},
		"FLAVOR_LOG_LEVEL":          {},
		"FLAVOR_LOG_PATH":           {},
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

	t.Setenv("FLAVOR_LAUNCHER_CLI", "1")
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
				"FLAVOR_LAUNCHER_SUBPROCESS=1",
				"FLAVOR_LAUNCHER_BUNDLE="+bundle,
				"FLAVOR_LAUNCHER_CLI=1",
				"FLAVOR_LAUNCHER_ARGS="+strings.Join(tc.args, "\x1f"),
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
	if os.Getenv("FLAVOR_LAUNCHER_SUBPROCESS") != "1" {
		return
	}

	bundle := os.Getenv("FLAVOR_LAUNCHER_BUNDLE")
	args := strings.Split(os.Getenv("FLAVOR_LAUNCHER_ARGS"), "\x1f")
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
				"FLAVOR_LAUNCHER_SUBPROCESS=1",
				"FLAVOR_LAUNCHER_BUNDLE="+bundle,
				"FLAVOR_VALIDATION=none",
				"FLAVOR_EXEC_MODE="+tc.mode,
			)

			output, err := cmd.CombinedOutput()
			if err != nil {
				t.Fatalf("subprocess %s failed: %v\n%s", tc.name, err, string(output))
			}
		})
	}
}

func TestLaunchExecModesHelper(t *testing.T) {
	if os.Getenv("FLAVOR_LAUNCHER_SUBPROCESS") != "1" {
		return
	}

	bundle := os.Getenv("FLAVOR_LAUNCHER_BUNDLE")
	_ = os.Unsetenv("FLAVOR_LAUNCHER_CLI")
	_ = os.Setenv(EnvValidation, os.Getenv("FLAVOR_VALIDATION"))
	_ = os.Setenv(EnvExecMode, os.Getenv("FLAVOR_EXEC_MODE"))

	Launch(bundle, nil)
}

func TestExecBundleReplaceWithStubbedSyscallExec(t *testing.T) {
	bundle := buildLauncherTestBundle(t)
	logger := hclog.NewNullLogger()

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
