//go:build !windows

package format_2025

import (
	"os"
	"syscall"
)

var osFindProcessFn = os.FindProcess

// IsProcessRunning checks if a process with given PID is still running.
// On Unix, Signal(0) checks if process exists without actually sending a signal.
func IsProcessRunning(pid int) bool {
	process, err := osFindProcessFn(pid)
	if err != nil {
		return false
	}
	err = process.Signal(syscall.Signal(0))
	return err == nil
}
