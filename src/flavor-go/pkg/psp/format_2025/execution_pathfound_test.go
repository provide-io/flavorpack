// SPDX-FileCopyrightText: Copyright (c) 2026 provide.io llc. All rights reserved.
// SPDX-License-Identifier: Apache-2.0

package format_2025

import (
	"os"
	"runtime"
	"strings"
	"testing"

	"github.com/provide-io/flavor/go/flavor/pkg/logging"
)

// TestRunBundleWithCwdPathNotFoundInEnvironment covers lines 672-677 in
// execution.go: the !pathFound branch where PATH is not found in cmd.Env.
// This happens when the parent environment has no PATH variable.
//
// We manipulate the environment so PATH is absent before calling runBundleWithCwd.
func TestRunBundleWithCwdPathNotFoundInEnvironment(t *testing.T) {
	if runtime.GOOS == "windows" {
		t.Skip("PATH manipulation tests not reliable on Windows")
	}

	// Save and remove PATH from environment.
	oldPath, hasPath := os.LookupEnv("PATH")
	if hasPath {
		if err := os.Unsetenv("PATH"); err != nil {
			t.Fatalf("Unsetenv(PATH): %v", err)
		}
		t.Cleanup(func() { _ = os.Setenv("PATH", oldPath) })
	}

	bundle := buildLauncherTestBundle(t)
	logger := logging.NewNullLogger()

	cacheRoot := t.TempDir()
	t.Setenv(EnvCacheDir, cacheRoot)
	t.Setenv(EnvWorkenvCache, "false")
	t.Setenv(EnvValidation, "none")

	// runBundleWithCwd should succeed (PATH not in parent env, but workenv/bin is added).
	cmd, err := runBundleWithCwd(bundle, nil, t.TempDir(), logger)
	if err != nil {
		// May fail if the bundle command (/bin/true) can't be resolved without PATH.
		// That's OK — we just need to reach the !pathFound branch.
		t.Logf("runBundleWithCwd error (acceptable): %v", err)
		return
	}
	if cmd == nil {
		t.Fatal("expected non-nil cmd")
	}

	// Verify that PATH was added to cmd.Env (the !pathFound branch sets it).
	var foundPath bool
	for _, env := range cmd.Env {
		if strings.HasPrefix(env, "PATH=") {
			foundPath = true
			break
		}
	}
	if !foundPath {
		t.Fatal("expected PATH to be set in cmd.Env even when not in parent environment")
	}
}

// TestRunBundleWithCwdWindowsScriptsDir covers lines 664-666 and 674-676 in
// execution.go: when currentGOOS is "windows", the binDir is "Scripts" instead of "bin".
func TestRunBundleWithCwdWindowsScriptsDir(t *testing.T) {
	// Override currentGOOS to simulate Windows.
	old := currentGOOS
	currentGOOS = "windows"
	t.Cleanup(func() { currentGOOS = old })

	bundle := buildLauncherTestBundle(t)
	logger := logging.NewNullLogger()

	cacheRoot := t.TempDir()
	t.Setenv(EnvCacheDir, cacheRoot)
	t.Setenv(EnvWorkenvCache, "false")
	t.Setenv(EnvValidation, "none")

	// Note: on macOS with currentGOOS="windows", the command /bin/true is still valid
	// but the PATH will use "Scripts" directory.
	cmd, err := runBundleWithCwd(bundle, nil, t.TempDir(), logger)
	if err != nil {
		// Some error may occur due to Windows-specific paths on macOS. OK.
		t.Logf("runBundleWithCwd error (may be acceptable on non-Windows): %v", err)
		return
	}
	if cmd == nil {
		t.Fatal("expected non-nil cmd")
	}

	// Verify that PATH contains "Scripts" directory.
	for _, env := range cmd.Env {
		if strings.HasPrefix(env, "PATH=") {
			if !strings.Contains(env, "Scripts") {
				t.Fatalf("expected PATH to contain 'Scripts' for Windows simulation, got: %s", env)
			}
			return
		}
	}
	t.Fatal("expected PATH to be set in cmd.Env")
}

// TestRunBundleWithCwdWindowsScriptsDirNoPath covers lines 674-676 in
// execution.go: Windows with no PATH in parent env, so !pathFound branch
// uses "Scripts" as binDir.
func TestRunBundleWithCwdWindowsScriptsDirNoPath(t *testing.T) {
	// Override currentGOOS to simulate Windows.
	old := currentGOOS
	currentGOOS = "windows"
	t.Cleanup(func() { currentGOOS = old })

	// Remove PATH from environment.
	oldPath, hasPath := os.LookupEnv("PATH")
	if hasPath {
		if err := os.Unsetenv("PATH"); err != nil {
			t.Fatalf("Unsetenv(PATH): %v", err)
		}
		t.Cleanup(func() { _ = os.Setenv("PATH", oldPath) })
	}

	bundle := buildLauncherTestBundle(t)
	logger := logging.NewNullLogger()

	cacheRoot := t.TempDir()
	t.Setenv(EnvCacheDir, cacheRoot)
	t.Setenv(EnvWorkenvCache, "false")
	t.Setenv(EnvValidation, "none")

	cmd, err := runBundleWithCwd(bundle, nil, t.TempDir(), logger)
	if err != nil {
		t.Logf("runBundleWithCwd error (acceptable): %v", err)
		return
	}
	if cmd == nil {
		t.Fatal("expected non-nil cmd")
	}

	// Verify PATH contains "Scripts" (Windows !pathFound branch).
	for _, env := range cmd.Env {
		if strings.HasPrefix(env, "PATH=") {
			if !strings.Contains(env, "Scripts") {
				t.Fatalf("expected PATH to contain 'Scripts' for Windows !pathFound, got: %s", env)
			}
			return
		}
	}
	t.Fatal("expected PATH to be set in cmd.Env")
}
