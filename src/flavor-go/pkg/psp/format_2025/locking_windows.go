//go:build windows

package format_2025

import (
	"golang.org/x/sys/windows"
)

// IsProcessRunning checks if a process with given PID is still running.
// On Windows, we use OpenProcess with PROCESS_QUERY_LIMITED_INFORMATION
// because Signal(0) does not work reliably on Windows.
func IsProcessRunning(pid int) bool {
	handle, err := windows.OpenProcess(windows.PROCESS_QUERY_LIMITED_INFORMATION, false, uint32(pid))
	if err != nil {
		return false
	}
	windows.CloseHandle(handle)
	return true
}
