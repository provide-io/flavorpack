//go:build !windows
// +build !windows

package format_2025

// setUTF8ConsoleOutput is a no-op on non-Windows platforms; UTF-8 is the default.
func setUTF8ConsoleOutput() {}
