package format_2025

import (
	"testing"

	"github.com/provide-io/flavor/go/flavor/pkg/logging"
)

// TestShowMetadataSuccess covers the happy path of showMetadata:
// reads metadata from a valid bundle and encodes it to stdout without error.
func TestShowMetadataSuccess(t *testing.T) {
	bundle := buildLauncherTestBundle(t)
	logger := logging.NewNullLogger()

	// Should not panic or call osExitFn.
	oldExit := osExitFn
	t.Cleanup(func() { osExitFn = oldExit })
	osExitFn = func(code int) {
		t.Fatalf("unexpected osExitFn(%d) called during showMetadata success path", code)
	}

	showMetadata(bundle, logger)
}

// TestShowBundleInfoSuccess covers the happy path of showBundleInfo with a valid bundle.
func TestShowBundleInfoSuccess(t *testing.T) {
	bundle := buildLauncherTestBundle(t)
	logger := logging.NewNullLogger()

	oldExit := osExitFn
	t.Cleanup(func() { osExitFn = oldExit })
	osExitFn = func(code int) {
		t.Fatalf("unexpected osExitFn(%d) called during showBundleInfo success path", code)
	}

	showBundleInfo(bundle, logger)
}

// TestLaunchWithLogLevelMetadataCommand exercises the "metadata" CLI command path.
func TestLaunchWithLogLevelMetadataCommand(t *testing.T) {
	bundle := buildLauncherTestBundle(t)

	t.Setenv(EnvLauncherCLI, "1")
	LaunchWithLogLevel(bundle, []string{"metadata"}, "warn", "test")
}
