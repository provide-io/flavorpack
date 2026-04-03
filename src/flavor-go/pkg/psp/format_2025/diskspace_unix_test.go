//go:build !windows

package format_2025

import (
	"errors"
	"syscall"
	"testing"
)

func TestGetAvailableDiskSpaceReturnsError(t *testing.T) {
	old := syscallStatfsFn
	t.Cleanup(func() { syscallStatfsFn = old })
	syscallStatfsFn = func(path string, stat *syscall.Statfs_t) error {
		return errors.New("statfs failed")
	}

	_, err := getAvailableDiskSpace(t.TempDir())
	if err == nil {
		t.Fatal("expected error when syscall.Statfs fails, got nil")
	}
}

func TestGetAvailableDiskSpaceSucceeds(t *testing.T) {
	// Verify the real syscall works on this platform
	available, err := getAvailableDiskSpace(t.TempDir())
	if err != nil {
		t.Fatalf("getAvailableDiskSpace() error = %v", err)
	}
	if available <= 0 {
		t.Fatalf("expected positive disk space, got %d", available)
	}
}
