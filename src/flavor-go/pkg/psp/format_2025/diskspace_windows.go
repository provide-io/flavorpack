//go:build windows

package format_2025

import (
	"syscall"
	"unsafe"
)

var (
	kernel32                = syscall.NewLazyDLL("kernel32.dll")
	procGetDiskFreeSpaceExW = kernel32.NewProc("GetDiskFreeSpaceExW")
)

// getAvailableDiskSpace returns available disk space in bytes for Windows
func getAvailableDiskSpace(path string) (int64, error) {
	var freeBytesAvailable int64
	var totalNumberOfBytes int64
	var totalNumberOfFreeBytes int64

	pathPtr, err := syscall.UTF16PtrFromString(path)
	if err != nil {
		return 0, err
	}

	ret, _, err := procGetDiskFreeSpaceExW.Call(
		uintptr(unsafe.Pointer(pathPtr)),
		uintptr(unsafe.Pointer(&freeBytesAvailable)),
		uintptr(unsafe.Pointer(&totalNumberOfBytes)),
		uintptr(unsafe.Pointer(&totalNumberOfFreeBytes)),
	)

	if ret == 0 {
		return 0, err
	}

	return freeBytesAvailable, nil
}
