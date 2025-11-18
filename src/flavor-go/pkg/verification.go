package pkg

import (
	"fmt"
	"os"

	"github.com/hashicorp/go-hclog"
	"github.com/provide-io/flavor/go/flavor/pkg/logging"
	"github.com/provide-io/flavor/go/flavor/pkg/psp/format_2025"
)

// VerifyBundleWithLogger verifies a bundle with a provided logger
func VerifyBundleWithLogger(exePath string, logger hclog.Logger) {
	reader, err := format_2025.NewReader(exePath)
	if err != nil {
		logger.Error("Failed to create reader", "error", err)
		os.Exit(1)
	}
	defer func() {
		if err := reader.Close(); err != nil {
			logger.Debug("Failed to close reader", "error", err)
		}
	}()

	logger.Info("Verifying bundle integrity")

	errors := []string{}

	_, err = reader.VerifyMagicTrailer()
	if err != nil {
		errors = append(errors, fmt.Sprintf("MagicTrailer verification failed: %v", err))
		logger.Error("MagicTrailer verification failed", "error", err)
	} else {
		logger.Info("✓ MagicTrailer valid")
	}

	_, err = reader.ReadIndex()
	if err != nil {
		errors = append(errors, fmt.Sprintf("Index verification failed: %v", err))
		logger.Error("Index verification failed", "error", err)
	} else {
		logger.Info("✓ Index checksum valid")
	}

	metadata, err := reader.ReadMetadata()
	if err != nil {
		errors = append(errors, fmt.Sprintf("Metadata verification failed: %v", err))
		logger.Error("Metadata verification failed", "error", err)
	} else {
		logger.Info("✓ Metadata checksum valid")

		for i, slot := range metadata.Slots {
			_, err := reader.ReadSlot(i)
			if err != nil {
				errors = append(errors, fmt.Sprintf("Slot %d (%s) read failed: %v", i, slot.ID, err))
				logger.Error("Slot verification failed", "index", i, "id", slot.ID, "error", err)
			} else {
				logger.Info("✓ Slot checksum valid", "index", i, "id", slot.ID)
			}
		}
	}

	if len(errors) == 0 {
		logger.Info("✓ Bundle verification passed")
	} else {
		logger.Error("✗ Bundle verification failed", "error_count", len(errors))
		for _, err := range errors {
			logger.Error("  Verification error", "details", err)
		}
		os.Exit(1)
	}
}

// VerifyBundle verifies a bundle using default logger settings
func VerifyBundle(exePath string) {
	logger := logging.NewLogger("flavor-verify", logging.GetLogLevel(), nil)
	VerifyBundleWithLogger(exePath, logger)
}
