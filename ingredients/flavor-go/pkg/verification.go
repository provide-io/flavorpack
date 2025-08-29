package pkg

import (
	"fmt"
	"os"

	"github.com/provide-io/flavor/go/flavor/pkg/psp/format_2025"
)

func VerifyBundle(exePath string) {
	reader, err := format_2025.NewReader(exePath)
	if err != nil {
		fmt.Printf("❌ Failed to create reader: %v\n", err)
		os.Exit(1)
	}
	defer func() {
		if err := reader.Close(); err != nil {
			fmt.Printf("Failed to close reader: %v\n", err)
		}
	}()

	fmt.Println("Verifying bundle integrity...")

	errors := []string{}

	_, err = reader.VerifyMagic()
	if err != nil {
		errors = append(errors, fmt.Sprintf("Magic verification failed: %v", err))
	} else {
		fmt.Println("✓ Magic sequence valid")
	}

	_, err = reader.ReadIndex()
	if err != nil {
		errors = append(errors, fmt.Sprintf("Index verification failed: %v", err))
	} else {
		fmt.Println("✓ Index checksum valid")
	}

	metadata, err := reader.ReadMetadata()
	if err != nil {
		errors = append(errors, fmt.Sprintf("Metadata verification failed: %v", err))
	} else {
		fmt.Println("✓ Metadata checksum valid")

		for i, slot := range metadata.Slots {
			_, err := reader.ReadSlot(i)
			if err != nil {
				errors = append(errors, fmt.Sprintf("Slot %d (%s) read failed: %v", i, slot.ID, err))
			} else {
				fmt.Printf("✓ Slot %d (%s) checksum valid\n", i, slot.ID)
			}
		}
	}

	if len(errors) == 0 {
		fmt.Println("\n✓ Bundle verification passed")
	} else {
		fmt.Println("\n✗ Bundle verification failed:")
		for _, err := range errors {
			fmt.Printf("  - %s\n", err)
		}
		os.Exit(1)
	}
}
