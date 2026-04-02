package pkg

import (
	"errors"
	"testing"

	"github.com/hashicorp/go-hclog"
	"github.com/provide-io/flavor/go/flavor/pkg/psp/format_2025"
)

// TestVerifyBundleWithLoggerReaderCloseFails covers verification.go:19-21
// (verifyReaderCloseFn returns error → error logged, execution continues).
// The deferred reader.Close is always executed, so injecting an error exercises the path.
func TestVerifyBundleWithLoggerReaderCloseFails(t *testing.T) {
	bundle := writeValidBundle(t)

	old := verifyReaderCloseFn
	t.Cleanup(func() { verifyReaderCloseFn = old })
	verifyReaderCloseFn = func(r *format_2025.Reader) error {
		_ = r.Close() // close for real to avoid FD leak
		return errors.New("injected reader close failure")
	}

	// VerifyBundleWithLogger should succeed (the close error is just logged, not fatal)
	logger := hclog.NewNullLogger()
	VerifyBundleWithLogger(bundle, logger)
}
