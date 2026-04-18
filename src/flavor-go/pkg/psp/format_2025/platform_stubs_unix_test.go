// SPDX-FileCopyrightText: Copyright (c) 2026 provide.io llc. All rights reserved.
// SPDX-License-Identifier: Apache-2.0

//go:build !windows
// +build !windows

package format_2025

import (
	"strings"
	"testing"

	"github.com/provide-io/flavor/go/flavor/pkg/logging"
)

func TestSetUTF8ConsoleOutputNoopOnUnix(t *testing.T) {
	t.Parallel()

	setUTF8ConsoleOutput()
}

func TestPEResourceStubsReturnUnixErrors(t *testing.T) {
	t.Parallel()

	logger := logging.NewNullLogger()
	if err := EmbedPSPFAsResource("/tmp/app", []byte("pspf"), logger); err == nil || !strings.Contains(err.Error(), "only supported on Windows") {
		t.Fatalf("EmbedPSPFAsResource() error = %v", err)
	}
	if _, err := ReadPSPFFromResource("/tmp/app", logger); err == nil || !strings.Contains(err.Error(), "only supported on Windows") {
		t.Fatalf("ReadPSPFFromResource() error = %v", err)
	}
	if HasPSPFResource("/tmp/app", logger) {
		t.Fatal("expected HasPSPFResource() to be false on non-Windows")
	}
}
