// SPDX-FileCopyrightText: Copyright (c) 2026 provide.io llc. All rights reserved.
// SPDX-License-Identifier: Apache-2.0

package pkg

import (
	"encoding/json"
	"os"
	"path/filepath"
	"testing"

	format_2025 "github.com/provide-io/flavor/go/flavor/pkg/psp/format_2025"
)

func writeAPITestManifest(t *testing.T) (string, string, string) {
	t.Helper()

	dir := t.TempDir()
	launcherPath := filepath.Join(dir, "launcher.sh")
	if err := os.WriteFile(launcherPath, []byte("#!/bin/sh\nexit 0\n"), 0o700); err != nil {
		t.Fatalf("WriteFile(launcher) error = %v", err)
	}

	manifestPath := filepath.Join(dir, "manifest.json")
	manifest := format_2025.BuildOptions{
		Package: format_2025.PackageConfig{
			Name:    "api-demo",
			Version: "1.0.0",
		},
		Execution: format_2025.ExecutionConfig{
			Command: "/bin/true",
		},
	}
	manifestJSON, err := json.MarshalIndent(manifest, "", "  ")
	if err != nil {
		t.Fatalf("MarshalIndent() error = %v", err)
	}
	if err := os.WriteFile(manifestPath, manifestJSON, 0o600); err != nil {
		t.Fatalf("WriteFile(manifest) error = %v", err)
	}

	outputPath := filepath.Join(dir, "bundle.psp")
	return manifestPath, launcherPath, outputPath
}

func TestBuildPackageAPIsProduceBundles(t *testing.T) {
	t.Parallel()

	tests := []struct {
		name  string
		build func(manifestPath, outputPath, launcherPath string)
	}{
		{
			name: "BuildPackage",
			build: func(manifestPath, outputPath, launcherPath string) {
				BuildPackage(manifestPath, outputPath, launcherPath)
			},
		},
		{
			name: "BuildPackageWithOptions",
			build: func(manifestPath, outputPath, launcherPath string) {
				BuildPackageWithOptions(manifestPath, outputPath, launcherPath, "", "", "")
			},
		},
		{
			name: "BuildPackageWithLogLevel",
			build: func(manifestPath, outputPath, launcherPath string) {
				BuildPackageWithLogLevel(manifestPath, outputPath, launcherPath, "", "", "", "json:debug")
			},
		},
	}

	for _, tc := range tests {
		tc := tc
		t.Run(tc.name, func(t *testing.T) {
			manifestPath, launcherPath, outputPath := writeAPITestManifest(t)
			tc.build(manifestPath, outputPath, launcherPath)

			info, err := os.Stat(outputPath)
			if err != nil {
				t.Fatalf("expected built bundle to exist: %v", err)
			}
			if info.Size() == 0 {
				t.Fatal("expected built bundle to be non-empty")
			}
		})
	}
}
