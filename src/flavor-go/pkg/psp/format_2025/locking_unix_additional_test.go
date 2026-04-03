//go:build !windows

package format_2025

import (
	"errors"
	"os"
	"testing"
)

func TestIsProcessRunningFindProcessError(t *testing.T) {
	old := osFindProcessFn
	t.Cleanup(func() { osFindProcessFn = old })
	osFindProcessFn = func(pid int) (*os.Process, error) {
		return nil, errors.New("no such process")
	}

	if IsProcessRunning(99999) {
		t.Fatal("expected IsProcessRunning to return false when FindProcess fails")
	}
}
