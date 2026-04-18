// SPDX-FileCopyrightText: Copyright (c) 2026 provide.io llc. All rights reserved.
// SPDX-License-Identifier: Apache-2.0

package format_2025

import (
	"crypto/ed25519"
	"errors"
	"io"
	"log/slog"
	"os"
	"testing"

	"github.com/provide-io/flavor/go/flavor/pkg/logging"
)

// TestDoBuildExitsProcessLauncherFails covers the processLauncherFn error path
// in doBuild (line 176-179).
func TestDoBuildExitsProcessLauncherFails(t *testing.T) {
	dir := t.TempDir()
	slotSource := minimalSlot(t, dir)
	manifestPath := minimalManifest(t, dir, slotSource)
	launcherPath := minimalLauncher(t, dir)

	old := processLauncherFn
	t.Cleanup(func() { processLauncherFn = old })
	processLauncherFn = func(data []byte, logger *slog.Logger) ([]byte, error) {
		return nil, errors.New("injected process launcher failure")
	}

	_, cleanup := withBuildExitTrap(t)
	defer cleanup()
	defer assertBuilderExited(t, 1)

	doBuild(logging.NewNullLogger(), manifestPath, launcherPath+".pspf", launcherPath, "", "", "")
}

// TestDoBuildExitsEd25519GenerateKeyFails covers the ed25519GenerateKeyFn
// error path in doBuild (line 251-254).
func TestDoBuildExitsEd25519GenerateKeyFails(t *testing.T) {
	dir := t.TempDir()
	slotSource := minimalSlot(t, dir)
	manifestPath := minimalManifest(t, dir, slotSource)
	launcherPath := minimalLauncher(t, dir)

	old := ed25519GenerateKeyFn
	t.Cleanup(func() { ed25519GenerateKeyFn = old })
	ed25519GenerateKeyFn = func(rand io.Reader) (ed25519.PublicKey, ed25519.PrivateKey, error) {
		return nil, nil, errors.New("injected key generation failure")
	}

	_, cleanup := withBuildExitTrap(t)
	defer cleanup()
	defer assertBuilderExited(t, 1)

	// No key files, no seed -> ephemeral key generation -> injected failure
	doBuild(logging.NewNullLogger(), manifestPath, launcherPath+".pspf", launcherPath, "", "", "")
}

// TestDoBuildSuccessWithHostnameFailure covers the hostnameFunc error path
// in doBuild (line 280-282) where hostname resolution fails but build continues.
func TestDoBuildSuccessWithHostnameFailure(t *testing.T) {
	dir := t.TempDir()
	slotSource := minimalSlot(t, dir)
	manifestPath := minimalManifest(t, dir, slotSource)
	launcherPath := minimalLauncher(t, dir)
	outputPath := dir + "/out.pspf"

	old := hostnameFunc
	t.Cleanup(func() { hostnameFunc = old })
	hostnameFunc = func() (string, error) {
		return "", errors.New("hostname unavailable")
	}

	// No SOURCE_DATE_EPOCH set, so hostnameFunc path is taken.
	t.Setenv("SOURCE_DATE_EPOCH", "")

	doBuild(logging.NewNullLogger(), manifestPath, outputPath, launcherPath, "", "", "seed")

	// Build should succeed despite hostname failure.
	if _, err := statValidated(outputPath); err != nil {
		t.Fatalf("expected output file to exist: %v", err)
	}
}

// TestDoBuildExitsOpenOutputFileFails covers the openOutputFileFn error path
// in doBuild (line 192-196).
func TestDoBuildExitsOpenOutputFileFails(t *testing.T) {
	dir := t.TempDir()
	slotSource := minimalSlot(t, dir)
	manifestPath := minimalManifest(t, dir, slotSource)
	launcherPath := minimalLauncher(t, dir)

	old := openOutputFileFn
	t.Cleanup(func() { openOutputFileFn = old })
	openOutputFileFn = func(_ string, _ int, _ os.FileMode) (*os.File, error) {
		return nil, errors.New("injected open output file failure")
	}

	_, cleanup := withBuildExitTrap(t)
	defer cleanup()
	defer assertBuilderExited(t, 1)

	doBuild(logging.NewNullLogger(), manifestPath, dir+"/out.pspf", launcherPath, "", "", "seed")
}
