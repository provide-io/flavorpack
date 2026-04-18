// SPDX-FileCopyrightText: Copyright (c) 2026 provide.io llc. All rights reserved.
// SPDX-License-Identifier: Apache-2.0

package format_2025

import (
	"bytes"
	"path/filepath"
	"strings"
	"testing"

	"github.com/provide-io/flavor/go/flavor/pkg/logging"
)

func TestSetFlavorCacheBeforeWorkenvSetsHostCache(t *testing.T) {
	cacheRoot := t.TempDir()
	t.Setenv(EnvCacheDir, cacheRoot)
	logger := logging.NewNullLogger()

	got := setFlavorCacheBeforeWorkenv([]string{"PATH=/usr/bin"}, logger)

	if !hasEnv(got, EnvCache) {
		t.Fatalf("expected FLAVOR_CACHE to be set")
	}
	want := filepath.Join(cacheRoot, "workenv")
	if value := getenv(got, EnvCache, ""); value != want {
		t.Fatalf("unexpected FLAVOR_CACHE value %q", value)
	}
}

func TestSetFlavorCacheBeforeWorkenvPreservesExistingValue(t *testing.T) {
	logger := logging.NewNullLogger()
	env := []string{EnvCache + "=/already/set"}

	got := setFlavorCacheBeforeWorkenv(env, logger)

	if value := getenv(got, EnvCache, ""); value != "/already/set" {
		t.Fatalf("expected existing FLAVOR_CACHE to be preserved, got %q", value)
	}
}

func TestGetenvAndHasEnv(t *testing.T) {
	env := []string{"PATH=/usr/bin", "HOME=/tmp/home"}

	if !hasEnv(env, "PATH") {
		t.Fatalf("expected PATH to exist")
	}
	if hasEnv(env, "MISSING") {
		t.Fatalf("did not expect MISSING to exist")
	}
	if got := getenv(env, "HOME", "fallback"); got != "/tmp/home" {
		t.Fatalf("unexpected HOME value %q", got)
	}
	if got := getenv(env, "MISSING", "fallback"); got != "fallback" {
		t.Fatalf("unexpected fallback value %q", got)
	}
}

func TestLogEnvironmentTraceRedactsSensitiveValues(t *testing.T) {
	var output bytes.Buffer
	logger := logging.NewBufferLogger(&output, logging.LevelTrace)

	logEnvironmentTrace([]string{
		"OPENAI_API_KEY=secret",
		"PATH=/usr/bin",
	}, logger)

	logged := output.String()
	if !strings.Contains(logged, "OPENAI_API_KEY") {
		t.Fatalf("expected sensitive key name in trace output: %s", logged)
	}
	if strings.Contains(logged, "secret") {
		t.Fatalf("expected sensitive value to be redacted: %s", logged)
	}
	if !strings.Contains(logged, "***") {
		t.Fatalf("expected redaction marker in trace output: %s", logged)
	}
}

func TestIsSensitiveKey(t *testing.T) {
	if !isSensitiveKey("OPENAI_API_KEY") {
		t.Fatalf("expected OPENAI_API_KEY to be treated as sensitive")
	}
	if isSensitiveKey("PATH") {
		t.Fatalf("expected PATH to be treated as non-sensitive")
	}
}
