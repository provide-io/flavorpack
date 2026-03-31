//go:build !windows

package format_2025

import (
	"fmt"
	"syscall"
)

// getAvailableDiskSpace returns available disk space in bytes for Unix systems
func getAvailableDiskSpace(path string) (int64, error) {
	var stat syscall.Statfs_t
	if err := syscall.Statfs(path, &stat); err != nil {
		return 0, err
	}
	availableBlocks, err := uint64ToInt64Checked(stat.Bavail, "available disk blocks")
	if err != nil {
		return 0, err
	}
	blockSize := int64(stat.Bsize)
	if blockSize <= 0 {
		return 0, fmt.Errorf("invalid filesystem block size: %d", blockSize)
	}
	available := availableBlocks * blockSize
	return available, nil
}
