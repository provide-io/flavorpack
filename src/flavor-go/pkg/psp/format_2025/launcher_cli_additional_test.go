package format_2025

import (
	"os"
	"os/exec"
	"path/filepath"
	"runtime"
	"strings"
	"testing"

	"github.com/hashicorp/go-hclog"
)

func runLauncherCLIAdditionalScenario(t *testing.T, mode, bundle string, args []string) (string, error) {
	t.Helper()

	cmd := exec.Command(os.Args[0], "-test.run=TestLauncherCLIAdditionalHelper")
	cmd.Env = filteredEnv(
		"FLAVOR_LAUNCHER_HELPER=1",
		"FLAVOR_LAUNCHER_MODE="+mode,
		"FLAVOR_LAUNCHER_BUNDLE="+bundle,
		"FLAVOR_LAUNCHER_ARGS="+strings.Join(args, "\x1f"),
		"FLAVOR_LAUNCHER_CLI=1",
	)

	output, err := cmd.CombinedOutput()
	return string(output), err
}

func TestLauncherCLIAdditionalHelper(t *testing.T) {
	if os.Getenv("FLAVOR_LAUNCHER_HELPER") != "1" {
		return
	}

	bundle := os.Getenv("FLAVOR_LAUNCHER_BUNDLE")
	rawArgs := os.Getenv("FLAVOR_LAUNCHER_ARGS")
	var args []string
	if rawArgs != "" {
		args = strings.Split(rawArgs, "\x1f")
	}

	logger := hclog.NewNullLogger()
	switch os.Getenv("FLAVOR_LAUNCHER_MODE") {
	case "launch":
		LaunchWithLogLevel(bundle, args, "", "")
	case "show-metadata":
		showMetadata(bundle, logger)
	case "verify":
		verifyBundle(bundle, logger)
	case "show-info":
		showBundleInfo(bundle, logger)
	case "extract":
		if len(args) < 2 {
			t.Fatal("missing extract arguments")
		}
		extractSlot(bundle, args[0], args[1], logger)
	default:
		t.Fatalf("unsupported launcher CLI helper mode %q", os.Getenv("FLAVOR_LAUNCHER_MODE"))
	}
}

func TestLaunchWithLogLevelCLIDispatchBranches(t *testing.T) {
	bundle := buildLauncherTestBundle(t)

	cases := []struct {
		name      string
		args      []string
		want      string
		wantExit  int
		wantError bool
	}{
		{
			name:     "default info with no args",
			args:     nil,
			want:     "demo v1.0.0",
			wantExit: 0,
		},
		{
			name:     "help command",
			args:     []string{"help"},
			want:     "Available commands:",
			wantExit: 0,
		},
		{
			name:      "unknown command",
			args:      []string{"bogus"},
			want:      "Error: Unknown command 'bogus'",
			wantExit:  ExitInvalidArgs,
			wantError: true,
		},
		{
			name:      "extract command needs output dir",
			args:      []string{"extract", "0"},
			want:      "Error: extract requires slot index and output directory",
			wantExit:  ExitInvalidArgs,
			wantError: true,
		},
	}

	for _, tc := range cases {
		tc := tc
		t.Run(tc.name, func(t *testing.T) {
			output, err := runLauncherCLIAdditionalScenario(t, "launch", bundle, tc.args)
			if tc.wantError {
				if err == nil {
					t.Fatalf("expected %s to fail", tc.name)
				}
				exitErr, ok := err.(*exec.ExitError)
				if !ok {
					t.Fatalf("expected ExitError, got %T", err)
				}
				if got := exitErr.ExitCode(); got != tc.wantExit {
					t.Fatalf("exit code = %d, want %d", got, tc.wantExit)
				}
			} else if err != nil {
				t.Fatalf("expected %s to succeed, got err=%v\n%s", tc.name, err, output)
			}

			if !strings.Contains(output, tc.want) {
				t.Fatalf("output = %q, want substring %q", output, tc.want)
			}
		})
	}
}

func TestLauncherCLIAdditionalErrorPaths(t *testing.T) {
	missingBundle := filepath.Join(t.TempDir(), "missing.psp")
	bundle := buildLauncherTestBundle(t)
	extractDir := t.TempDir()

	cases := []struct {
		name      string
		mode      string
		bundle    string
		args      []string
		want      string
		wantExit  int
		wantError bool
	}{
		{
			// showBundleInfo writes via logger.Error (null logger → no output); just verify exit 1.
			name:      "show info missing bundle",
			mode:      "show-info",
			bundle:    missingBundle,
			want:      "",
			wantExit:  1,
			wantError: true,
		},
		{
			// showMetadata writes to os.Stderr directly.
			// Windows reports "The system cannot find the file specified."
			// Unix reports "no such file or directory" — accept either.
			name:   "show metadata missing bundle",
			mode:   "show-metadata",
			bundle: missingBundle,
			want: func() string {
				if runtime.GOOS == "windows" {
					return "cannot find the file"
				}
				return "no such file"
			}(),
			wantExit:  1,
			wantError: true,
		},
		{
			// verifyBundle prints a structured failure report to stdout.
			name:      "verify missing bundle",
			mode:      "verify",
			bundle:    missingBundle,
			want:      "Bundle verification failed",
			wantExit:  1,
			wantError: true,
		},
		{
			// extractSlot writes via logger.Error (null logger → no output); just verify exit 1.
			name:      "extract rejects out of range index",
			mode:      "extract",
			bundle:    bundle,
			args:      []string{"99", extractDir},
			want:      "",
			wantExit:  1,
			wantError: true,
		},
	}

	for _, tc := range cases {
		tc := tc
		t.Run(tc.name, func(t *testing.T) {
			output, err := runLauncherCLIAdditionalScenario(t, tc.mode, tc.bundle, tc.args)
			if tc.wantError {
				if err == nil {
					t.Fatalf("expected %s to fail", tc.name)
				}
				exitErr, ok := err.(*exec.ExitError)
				if !ok {
					t.Fatalf("expected ExitError, got %T", err)
				}
				if got := exitErr.ExitCode(); got != tc.wantExit {
					t.Fatalf("exit code = %d, want %d", got, tc.wantExit)
				}
			} else if err != nil {
				t.Fatalf("expected %s to succeed, got err=%v\n%s", tc.name, err, output)
			}

			if !strings.Contains(output, tc.want) {
				t.Fatalf("output = %q, want substring %q", output, tc.want)
			}
		})
	}
}
