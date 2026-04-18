// SPDX-FileCopyrightText: Copyright (c) 2026 provide.io llc. All rights reserved.
// SPDX-License-Identifier: Apache-2.0

package format_2025

import (
	"testing"

	"github.com/provide-io/flavor/go/flavor/pkg/logging"
)

// TestExecBundleSpawnModeWithEnv covers the spawn-mode branch in execBundle
// (line 203-204) when FLAVOR_EXEC_MODE=spawn is set explicitly.
func TestExecBundleSpawnModeWithEnv(t *testing.T) {
	bundle := buildLauncherTestBundle(t)
	logger := logging.NewNullLogger()

	// Inject osExitFn to prevent actual os.Exit.
	oldExit := osExitFn
	t.Cleanup(func() { osExitFn = oldExit })
	osExitFn = func(code int) {}

	cacheRoot := t.TempDir()
	t.Setenv(EnvCacheDir, cacheRoot)
	t.Setenv(EnvWorkenvCache, "false")
	t.Setenv(EnvValidation, "none")
	t.Setenv(EnvExecMode, "spawn")

	// spawnBundle will attempt to run the extracted command as a child process.
	// It may fail because the extracted bundle has a dummy payload, but the
	// spawn-mode branch is exercised.
	_ = execBundle(bundle, nil, t.TempDir(), logger)
}
