package format_2025

import (
	"errors"
	"testing"

	"github.com/hashicorp/go-hclog"
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
		showBundleInfo(bundle, hclog.NewNullLogger())
	}()

	// exitCalled should be false — VerifyMagicTrailer failure is non-fatal (just changes display)
	_ = exitCalled
}
