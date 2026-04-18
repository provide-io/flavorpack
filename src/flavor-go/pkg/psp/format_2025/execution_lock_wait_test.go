// SPDX-FileCopyrightText: Copyright (c) 2026 provide.io llc. All rights reserved.
// SPDX-License-Identifier: Apache-2.0

package format_2025

import (
	"errors"
	"log/slog"
	"os"
	"testing"

	"github.com/provide-io/flavor/go/flavor/pkg/logging"
)

// TestRunBundleWaitForExtractionFails covers execution.go:415-417
// (WaitForExtraction returns error when !acquiredLock → error returned from runBundleWithCwd).
func TestRunBundleWaitForExtractionFails(t *testing.T) {
	cacheRoot := t.TempDir()
	t.Setenv(EnvCacheDir, cacheRoot)
	t.Setenv(EnvWorkenvCache, "false")
	t.Setenv(EnvValidation, "none")

	bundle := buildMultiSlotBundleForTests(t, []multiSlotBundleSpec{
		{
			meta:       SlotMetadata{ID: "main", Target: "{workenv}"},
			storedData: []byte("hello"),
		},
	}, Metadata{
		Execution: &ExecutionInfo{PrimarySlot: 0, Command: "/bin/true"},
		Build:     &BuildInfo{Tool: "test"},
	})

	// Inject tryAcquireLockFn to return (false, nil) — lock held by another process
	oldAcquire := tryAcquireLockFn
	t.Cleanup(func() { tryAcquireLockFn = oldAcquire })
	tryAcquireLockFn = func(_ *WorkenvPaths, _ *slog.Logger) (bool, error) {
		return false, nil
	}

	// Inject waitForExtractionFn to return an error
	oldWait := waitForExtractionFn
	t.Cleanup(func() { waitForExtractionFn = oldWait })
	waitForExtractionFn = func(_ *WorkenvPaths, _ int, _ *slog.Logger) error {
		return errors.New("injected WaitForExtraction timeout")
	}

	logger := logging.NewNullLogger()
	_, err := runBundleWithCwd(bundle, nil, t.TempDir(), logger)
	if err == nil {
		t.Fatal("expected error from runBundleWithCwd when WaitForExtraction fails")
	}
}

// TestRunBundleCheckWorkenvValidityAfterWaitFails covers execution.go:420-422
// (checkWorkenvValidity returns error after WaitForExtraction succeeds → error returned).
func TestRunBundleCheckWorkenvValidityAfterWaitFails(t *testing.T) {
	cacheRoot := t.TempDir()
	t.Setenv(EnvCacheDir, cacheRoot)
	t.Setenv(EnvWorkenvCache, "false")
	t.Setenv(EnvValidation, "none")

	bundle := buildMultiSlotBundleForTests(t, []multiSlotBundleSpec{
		{
			meta:       SlotMetadata{ID: "main", Target: "{workenv}"},
			storedData: []byte("hello"),
		},
	}, Metadata{
		Execution: &ExecutionInfo{PrimarySlot: 0, Command: "/bin/true"},
		Build:     &BuildInfo{Tool: "test"},
	})

	// Inject tryAcquireLockFn to return (false, nil) — lock held
	oldAcquire := tryAcquireLockFn
	t.Cleanup(func() { tryAcquireLockFn = oldAcquire })
	tryAcquireLockFn = func(_ *WorkenvPaths, _ *slog.Logger) (bool, error) {
		return false, nil
	}

	// Inject waitForExtractionFn to succeed
	oldWait := waitForExtractionFn
	t.Cleanup(func() { waitForExtractionFn = oldWait })
	waitForExtractionFn = func(_ *WorkenvPaths, _ int, _ *slog.Logger) error {
		return nil
	}

	// Inject checkWorkenvValidityAfterWaitFn to fail
	oldCheck := checkWorkenvValidityAfterWaitFn
	t.Cleanup(func() { checkWorkenvValidityAfterWaitFn = oldCheck })
	checkWorkenvValidityAfterWaitFn = func(_ *WorkenvPaths, _ *PSPFIndex, _ *Metadata, _ *slog.Logger) (bool, error) {
		return false, errors.New("injected checkWorkenvValidity failure after wait")
	}

	logger := logging.NewNullLogger()
	_, err := runBundleWithCwd(bundle, nil, t.TempDir(), logger)
	if err == nil {
		t.Fatal("expected error from runBundleWithCwd when checkWorkenvValidity fails after wait")
	}
}

// TestRunBundleChmodValidatedFails covers execution.go:367-369
// (chmodValidated returns error for workenv.directories entry — debug log only).
func TestRunBundleChmodValidatedFails(t *testing.T) {
	cacheRoot := t.TempDir()
	t.Setenv(EnvCacheDir, cacheRoot)
	t.Setenv(EnvWorkenvCache, "false")
	t.Setenv(EnvValidation, "none")

	bundle := buildMultiSlotBundleForTests(t, []multiSlotBundleSpec{
		{
			meta:       SlotMetadata{ID: "main", Target: "{workenv}"},
			storedData: []byte("hello"),
		},
	}, Metadata{
		Execution: &ExecutionInfo{PrimarySlot: 0, Command: "/bin/true"},
		Build:     &BuildInfo{Tool: "test"},
		Workenv: &WorkenvInfo{
			Directories: []DirectorySpec{
				{Path: "{workenv}/mydir", Mode: "0700"},
			},
		},
	})

	// Inject chmodValidatedFn to fail
	old := chmodValidatedFn
	t.Cleanup(func() { chmodValidatedFn = old })
	chmodValidatedFn = func(_ string, _ os.FileMode) error {
		return errors.New("injected chmodValidated failure")
	}

	// chmodValidated failure is a debug log only, not fatal
	logger := logging.NewNullLogger()
	cmd, err := runBundleWithCwd(bundle, nil, t.TempDir(), logger)
	if err != nil {
		t.Fatalf("runBundleWithCwd() error = %v (chmodValidated failure should be non-fatal)", err)
	}
	if cmd == nil {
		t.Fatal("expected non-nil cmd")
	}
}
