// SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
// SPDX-License-Identifier: Apache-2.0

package format_2025

import (
	"errors"
	"fmt"
	"log/slog"
	"os"
	"os/exec"
	"path/filepath"
	"runtime"
	"strings"

	"github.com/provide-io/flavor/go/flavor/pkg/logging"
	"github.com/provide-io/flavor/go/flavor/pkg/utils/shellparse"
)

// substituteSlotPlaceholders replaces {slot:N} with the slot's path, in the
// forward-slash form a shell parser will not read as escapes.
func substituteSlotPlaceholders(text string, slotPaths map[int]string) string {
	for idx, path := range slotPaths {
		text = strings.ReplaceAll(text, fmt.Sprintf("{slot:%d}", idx), filepath.ToSlash(path))
	}
	return text
}

// resolveCommandPlaceholders fills every placeholder the execution command
// accepts, and refuses a command still naming a slot afterwards.
//
// An unresolved {slot:N} means the command refers to a slot the package does
// not carry. Running it would substitute nothing and pass the literal text to
// the shell.
func resolveCommandPlaceholders(
	metadata *Metadata,
	slotPaths map[int]string,
	workenvDirForCmd string,
	logger *slog.Logger,
) (string, error) {
	command := substituteSlotPlaceholders(metadata.Execution.Command, slotPaths)
	command = substituteSetupPlaceholders(command, workenvDirForCmd, metadata.Package)

	if !strings.Contains(command, "{slot:") {
		return command, nil
	}
	for i := range metadata.Slots {
		if strings.Contains(command, fmt.Sprintf("{slot:%d}", i)) {
			logger.Error("❌ Missing slot reference", "slot", i, "error", ErrMissingSlot)
			return "", fmt.Errorf("%w: slot %d", ErrMissingSlot, i)
		}
	}
	return command, nil
}

// buildExecCommand parses the resolved command and appends the caller's own
// arguments.
func buildExecCommand(command string, args []string, logger *slog.Logger) (*exec.Cmd, []string, error) {
	// Shell-aware so quoted arguments survive.
	parts, err := shellparse.Split(command)
	if err != nil {
		logger.Error("❌ Failed to parse command", "command", command, "error", err)
		return nil, nil, fmt.Errorf("failed to parse command %q: %w", command, err)
	}
	if len(parts) == 0 {
		logger.Error("Empty command")
		return nil, nil, errors.New("empty command")
	}

	cmdArgs := append(parts[1:], args...)
	return execCommandValidated(resolveExecutable(parts[0], logger), cmdArgs...), cmdArgs, nil
}

// workenvBinDir is where a package's executables live, which Windows names
// differently.
func workenvBinDir(workenvDir string) string {
	binDir := "bin"
	if runtime.GOOS == "windows" {
		binDir = "Scripts"
	}
	return filepath.Join(workenvDir, binDir)
}

// prependWorkenvBinToPath puts the package's own executables ahead of the
// host's, so a package runs what it shipped.
func prependWorkenvBinToPath(env []string, workenvDir string) []string {
	binDir := workenvBinDir(workenvDir)

	for i, entry := range env {
		if strings.HasPrefix(entry, "PATH=") {
			env[i] = fmt.Sprintf("PATH=%s%s%s", binDir, string(os.PathListSeparator), strings.TrimPrefix(entry, "PATH="))
			return env
		}
	}
	return setEnv(env, "PATH", binDir)
}

// buildCommandEnvironment layers the environment the package runs with, in the
// order later layers are meant to win: the parent's, then FLAVOR_*, then PATH,
// then the package's declared runtime operations, then its literal variables.
func buildCommandEnvironment(
	metadata *Metadata,
	slotPaths map[int]string,
	workenvDir string,
	originalCmd string,
	binaryName string,
	logger *slog.Logger,
) []string {
	env := os.Environ()
	logger.Debug("🌍 Inheriting parent environment", "vars_count", len(env))

	// Before the workenv variables, which overwrite HOME.
	env = setFlavorCacheBeforeWorkenv(env, logger)

	env = setEnv(env, EnvWorkenv, workenvDir)
	logger.Debug("➕ Added FLAVOR_WORKENV", "path", workenvDir)

	env = setEnv(env, EnvOriginalCommand, originalCmd)
	env = setEnv(env, EnvCommandName, binaryName)
	logger.Debug("🏷️ Added command name environment variables",
		EnvOriginalCommand, originalCmd,
		EnvCommandName, binaryName)

	env = prependWorkenvBinToPath(env, workenvDir)

	if metadata.Runtime != nil && metadata.Runtime.Env != nil {
		logger.Debug("🔄 Processing runtime.env configuration")
		env = processRuntimeEnv(env, metadata.Runtime.Env, logger)
	}

	if metadata.Execution.Environment != nil {
		logger.Debug("➕ Adding package-defined environment variables", "count", len(metadata.Execution.Environment))
		for k, v := range metadata.Execution.Environment {
			v = substituteSlotPlaceholders(v, slotPaths)
			env = setEnv(env, k, v)
			logging.Trace(logger, "➕ Added package env var", "key", k, "value", v)
		}
	}

	return env
}
