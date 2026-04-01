package format_2025

import (
	"bytes"
	"io"
	"os"
	"path/filepath"
	"strings"
	"testing"

	"github.com/hashicorp/go-hclog"
)

type launcherExitCode struct {
	code int
}

func TestDetectLauncherType(t *testing.T) {
	t.Parallel()

	dir := t.TempDir()
	cases := []struct {
		name    string
		content []byte
		want    string
	}{
		{name: "go", content: []byte("go.buildid\x00runtime.main"), want: "go"},
		{name: "rust", content: []byte("rust_panic and _ZN"), want: "rust"},
		{name: "python", content: []byte("#!/usr/bin/env python3\n"), want: "python"},
		{name: "node", content: []byte("#!/usr/bin/env node\n"), want: "node"},
		{name: "unknown", content: []byte("plain bytes"), want: "unknown"},
	}

	for _, tc := range cases {
		tc := tc
		t.Run(tc.name, func(t *testing.T) {
			t.Parallel()

			path := filepath.Join(dir, tc.name+".bin")
			if err := os.WriteFile(path, tc.content, 0o600); err != nil {
				t.Fatalf("WriteFile() error = %v", err)
			}

			if got := detectLauncherType(path); got != tc.want {
				t.Fatalf("detectLauncherType() = %q, want %q", got, tc.want)
			}
		})
	}
}

func TestDetectLauncherTypeSpecialCases(t *testing.T) {
	oldArgs0 := os.Args[0]
	t.Cleanup(func() {
		os.Args[0] = oldArgs0
	})

	largeDir := t.TempDir()
	largePath := filepath.Join(largeDir, "large.bin")
	largeContent := strings.Repeat("A", 70000)
	if err := os.WriteFile(largePath, []byte(largeContent+"go.buildid"), 0o600); err != nil {
		t.Fatalf("WriteFile(large) error = %v", err)
	}

	cases := []struct {
		name    string
		args0   string
		exePath string
		want    string
	}{
		{name: "test-cli path shortcut", args0: "/tmp/test-cli.pspf", exePath: "/tmp/anything.psp", want: "go"},
		{name: "rust-go path shortcut", args0: "/tmp/launcher", exePath: "/tmp/rust-go.pspf", want: "go"},
		{name: "go-rust path shortcut", args0: "/tmp/launcher", exePath: "/tmp/go-rust.pspf", want: "rust"},
		{name: "rust-rust path shortcut", args0: "/tmp/launcher", exePath: "/tmp/rust-rust.pspf", want: "rust"},
		{name: "missing file falls back to unknown", args0: "/tmp/launcher", exePath: "/tmp/does-not-exist.bin", want: "unknown"},
		{name: "large file truncation", args0: "/tmp/launcher", exePath: largePath, want: "unknown"},
	}

	for _, tc := range cases {
		tc := tc
		t.Run(tc.name, func(t *testing.T) {
			os.Args[0] = tc.args0
			if got := detectLauncherType(tc.exePath); got != tc.want {
				t.Fatalf("detectLauncherType(%q) = %q, want %q", tc.exePath, got, tc.want)
			}
		})
	}
}

func captureStdout(t *testing.T, fn func()) string {
	t.Helper()

	oldStdout := os.Stdout
	r, w, err := os.Pipe()
	if err != nil {
		t.Fatalf("os.Pipe() error = %v", err)
	}
	os.Stdout = w
	defer func() {
		os.Stdout = oldStdout
	}()

	outC := make(chan string, 1)
	go func() {
		var buf bytes.Buffer
		_, _ = io.Copy(&buf, r)
		outC <- buf.String()
	}()

	fn()

	if err := w.Close(); err != nil {
		t.Fatalf("Close(writer) error = %v", err)
	}
	out := <-outC
	if err := r.Close(); err != nil {
		t.Fatalf("Close(reader) error = %v", err)
	}
	return out
}

func TestCLIMetadataAndVerificationPaths(t *testing.T) {
	logger := hclog.NewNullLogger()
	bundle := buildSingleSlotBundleForTests(t, []byte("cli file content"), []byte("cli file content"), nil, SlotMetadata{
		ID:     "cli-slot",
		Target: "{workenv}/bin/app.txt",
	}, 0, false)

	infoOutput := captureStdout(t, func() {
		showBundleInfo(bundle, logger)
	})
	if !strings.Contains(infoOutput, "demo v1.0.0") || !strings.Contains(infoOutput, "Slots: 1 (none) | Verified: ✓") {
		t.Fatalf("showBundleInfo() output = %q", infoOutput)
	}

	metadataOutput := captureStdout(t, func() {
		showMetadata(bundle, logger)
	})
	if !strings.Contains(metadataOutput, "\"name\": \"demo\"") {
		t.Fatalf("showMetadata() output = %q", metadataOutput)
	}

	extractDest := filepath.Join(t.TempDir(), "extract")
	extractOutput := captureStdout(t, func() {
		extractSlot(bundle, "0", extractDest, logger)
	})
	if !strings.Contains(extractOutput, "Extracted slot 0 (cli-slot) to") {
		t.Fatalf("extractSlot() output = %q", extractOutput)
	}
	if _, err := os.Stat(filepath.Join(extractDest, "bin", "app.txt")); err != nil {
		t.Fatalf("expected extracted file to exist: %v", err)
	}
}

func TestVerifyBundleDirectSuccess(t *testing.T) {
	t.Parallel()

	logger := hclog.NewNullLogger()
	bundle := buildSingleSlotBundleForTests(t, []byte("verify file content"), []byte("verify file content"), nil, SlotMetadata{
		ID:     "verify-slot",
		Target: "{workenv}/bin/app.txt",
	}, 0, false)

	output := captureStdout(t, func() {
		verifyBundle(bundle, logger)
	})
	if !strings.Contains(output, "✓ Magic sequence valid") || !strings.Contains(output, "✓ Bundle verification passed") {
		t.Fatalf("verifyBundle() output = %q", output)
	}
}

func TestCLIHelpersExitOnInvalidInputs(t *testing.T) {
	logger := hclog.NewNullLogger()

	bundle := buildSingleSlotBundleForTests(t, []byte("cli file content"), []byte("cli file content"), nil, SlotMetadata{
		ID:     "cli-slot",
		Target: "{workenv}/bin/app.txt",
	}, 0, false)

	cases := []struct {
		name     string
		fn       func()
		wantCode int
	}{
		{
			name: "show info invalid bundle",
			fn: func() {
				showBundleInfo(filepath.Join(t.TempDir(), "missing.psp"), logger)
			},
			wantCode: 1,
		},
		{
			name: "show metadata invalid bundle",
			fn: func() {
				showMetadata(filepath.Join(t.TempDir(), "missing.psp"), logger)
			},
			wantCode: 1,
		},
		{
			name: "verify invalid bundle",
			fn: func() {
				verifyBundle(filepath.Join(t.TempDir(), "missing.psp"), logger)
			},
			wantCode: 1,
		},
		{
			name: "extract invalid index",
			fn: func() {
				extractSlot(bundle, "nope", t.TempDir(), logger)
			},
			wantCode: 1,
		},
		{
			name: "extract out of range",
			fn: func() {
				extractSlot(bundle, "9", t.TempDir(), logger)
			},
			wantCode: 1,
		},
	}

	for _, tc := range cases {
		tc := tc
		t.Run(tc.name, func(t *testing.T) {
			oldExitFn := osExitFn
			osExitFn = func(code int) {
				panic(launcherExitCode{code: code})
			}
			t.Cleanup(func() {
				osExitFn = oldExitFn
			})

			defer func() {
				r := recover()
				if r == nil {
					t.Fatal("expected helper to terminate via osExitFn")
				}
				got, ok := r.(launcherExitCode)
				if !ok {
					t.Fatalf("unexpected panic value: %#v", r)
				}
				if got.code != tc.wantCode {
					t.Fatalf("exit code = %d, want %d", got.code, tc.wantCode)
				}
			}()

			tc.fn()
		})
	}
}

func TestVerifyBundleDirectFailure(t *testing.T) {
	logger := hclog.NewNullLogger()
	bundle := filepath.Join(t.TempDir(), "invalid.psp")
	if err := os.WriteFile(bundle, bytes.Repeat([]byte{0}, MagicTrailerSize), 0o600); err != nil {
		t.Fatalf("WriteFile() error = %v", err)
	}

	oldExitFn := osExitFn
	osExitFn = func(code int) {
		panic(launcherExitCode{code: code})
	}
	t.Cleanup(func() {
		osExitFn = oldExitFn
	})

	output := captureStdout(t, func() {
		defer func() {
			r := recover()
			if r == nil {
				t.Fatal("expected verifyBundle to terminate via osExitFn")
			}
			got, ok := r.(launcherExitCode)
			if !ok {
				t.Fatalf("unexpected panic value: %#v", r)
			}
			if got.code != 1 {
				t.Fatalf("exit code = %d, want 1", got.code)
			}
		}()
		verifyBundle(bundle, logger)
	})

	if !strings.Contains(output, "Bundle verification failed") {
		t.Fatalf("verifyBundle() output = %q", output)
	}
}
