// SPDX-FileCopyrightText: Copyright (c) 2026 provide.io llc. All rights reserved.
// SPDX-License-Identifier: Apache-2.0

package main

import (
	"errors"
	"os"
	"os/exec"
	"strings"
	"testing"

	"github.com/provide-io/flavor/go/flavor/pkg/psp/format_2025"
)

func TestLauncherMainExecutablePathFailure(t *testing.T) {
	t.Parallel()

	cmd := exec.Command(os.Args[0], "-test.run=TestLauncherMainHelperProcess")
	cmd.Env = append(os.Environ(), "GO_WANT_LAUNCHER_HELPER=1")

	out, err := cmd.CombinedOutput()
	if err == nil {
		t.Fatalf("expected helper command to fail")
	}
	exitErr, ok := err.(*exec.ExitError)
	if !ok {
		t.Fatalf("expected ExitError, got %T", err)
	}
	if exitErr.ExitCode() != format_2025.ExitIOError {
		t.Fatalf("expected panic exit code 40, got %d\n%s", exitErr.ExitCode(), out)
	}
	if !strings.Contains(string(out), "Failed to get executable path: boom") {
		t.Fatalf("expected executable path failure output, got %q", string(out))
	}
}

func TestLauncherMainHelperProcess(t *testing.T) {
	if os.Getenv("GO_WANT_LAUNCHER_HELPER") != "1" {
		return
	}
	oldExecutablePathFn := executablePathFn
	t.Cleanup(func() {
		executablePathFn = oldExecutablePathFn
	})
	executablePathFn = func() (string, error) {
		return "", errors.New("boom")
	}
	main()
}
