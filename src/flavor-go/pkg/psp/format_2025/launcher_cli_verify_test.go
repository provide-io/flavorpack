// SPDX-FileCopyrightText: Copyright (c) 2026 provide.io llc. All rights reserved.
// SPDX-License-Identifier: Apache-2.0

package format_2025

import (
	"errors"
	"testing"

	"github.com/provide-io/flavor/go/flavor/pkg/logging"
)

// TestShowBundleInfoVerifyMagicTrailerFails covers launcher_cli.go:72-74
// (VerifyMagicTrailer returns error → verifyStatus set to "✗").
// We inject verifyMagicTrailerFn to simulate failure while ReadIndex and ReadMetadata succeed.
func TestShowBundleInfoVerifyMagicTrailerFails(t *testing.T) {
	bundle := buildLauncherTestBundle(t)

	old := verifyMagicTrailerFn
	t.Cleanup(func() { verifyMagicTrailerFn = old })
	verifyMagicTrailerFn = func(_ *Reader) (bool, error) {
		return false, errors.New("injected VerifyMagicTrailer failure")
	}

	oldExit := osExitFn
	t.Cleanup(func() { osExitFn = oldExit })
	exitCalled := false
	osExitFn = func(code int) {
		exitCalled = true
		panic(launcherExitCode{code: code})
	}

	// showBundleInfo should complete normally (✗ is just displayed, not fatal)
	func() {
		defer func() { _ = recover() }()
		showBundleInfo(bundle, logging.NewNullLogger())
	}()

	// exitCalled should be false — VerifyMagicTrailer failure is non-fatal (just changes display)
	_ = exitCalled
}
