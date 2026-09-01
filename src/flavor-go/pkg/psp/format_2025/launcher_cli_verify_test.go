package format_2025

import (
	"errors"
	"io"
	"strings"
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
	output := captureCLIOutput(func(out io.Writer) {
		defer func() { _ = recover() }()
		showBundleInfo(out, bundle, logging.NewNullLogger())
	})

	// This used to end at "_ = exitCalled", so the branch it names was set up
	// and then never checked -- showBundleInfo could have printed anything, or
	// nothing. Asserting on the report is what makes it a test.
	if exitCalled {
		t.Error("a failed magic trailer is non-fatal to info; showBundleInfo must not exit")
	}
	if !strings.Contains(output, "Verified: ✗") {
		t.Errorf("expected the report to mark the bundle unverified, got %q", output)
	}
}
