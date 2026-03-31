//go:build !windows
// +build !windows

package format_2025

import (
	"os"
	"testing"
)

func TestIsPrivilegedUserMatchesEUID(t *testing.T) {
	t.Parallel()

	got := isPrivilegedUser()
	want := os.Getuid() == 0
	if got != want {
		t.Fatalf("isPrivilegedUser() = %v, want %v", got, want)
	}
}
