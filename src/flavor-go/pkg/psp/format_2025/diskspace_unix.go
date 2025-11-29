//go:build !windows

package format_2025

import "syscall"

// getAvailableDiskSpace returns available disk space in bytes for Unix systems
func getAvailableDiskSpace(path string) (int64, error) {
	var stat syscall.Statfs_t
	if err := syscall.Statfs(path, &stat); err != nil {
		return 0, err
	}
	available := int64(stat.Bavail) * int64(stat.Bsize)
	return available, nil
}
