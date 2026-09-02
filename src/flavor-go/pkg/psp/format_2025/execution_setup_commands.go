// SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
// SPDX-License-Identifier: Apache-2.0

package format_2025

import (
	"fmt"
	"log/slog"
	"os"
	"os/exec"
	"path/filepath"
	"runtime"
	"strings"

	"github.com/provide-io/flavor/go/flavor/pkg/utils/shellparse"
)

// substituteSetupPlaceholders fills the three placeholders every setup-command
// field accepts.
//
// Callers pass either workenvDir or its forward-slash form: a path used as a
// filesystem path keeps the platform separator, and one embedded in a command
// string does not, because the shell parser reads a backslash as an escape.
func substituteSetupPlaceholders(text, workenv string, pkg PackageInfo) string {
	text = strings.ReplaceAll(text, "{workenv}", workenv)
	text = strings.ReplaceAll(text, "{package_name}", pkg.Name)
	return strings.ReplaceAll(text, "{version}", pkg.Version)
}

// resolveEnumerateAndExecute expands a glob into the command's arguments.
//
// With no matches, or a command that is empty, the command runs as written --
// enumerating nothing is not an error.
func resolveEnumerateAndExecute(
	cmd map[string]any,
	command string,
	workenvDir string,
	logger *slog.Logger,
) (string, []string, error) {
	enumerate, ok := cmd["enumerate"].(map[string]any)
	if !ok {
		return "", nil, nil
	}

	path, _ := enumerate["path"].(string)
	pattern, _ := enumerate["pattern"].(string)

	path = strings.ReplaceAll(path, "{workenv}", workenvDir)
	if err := ensurePathWithinWorkenv(path, workenvDir, path); err != nil {
		logger.Error("❌ Enumerate path escapes work environment directory", "path", path, "error", err)
		return "", nil, err
	}

	matches, err := filepath.Glob(filepath.Join(path, pattern))
	if err != nil {
		logger.Warn("⚠️ Failed to enumerate files", "error", err)
	}

	parts := strings.Fields(command)
	if len(parts) > 0 && len(matches) > 0 {
		return parts[0], append(parts[1:], matches...), nil
	}
	return command, nil, nil
}

// applyWriteFileCommand writes a file and reports that there is nothing to run.
func applyWriteFileCommand(
	cmd map[string]any,
	metadata *Metadata,
	workenvDir string,
	workenvDirForCmd string,
	logger *slog.Logger,
) error {
	path, _ := cmd["path"].(string)
	content, _ := cmd["content"].(string)

	path = substituteSetupPlaceholders(path, workenvDir, metadata.Package)
	if err := ensurePathWithinWorkenv(path, workenvDir, path); err != nil {
		logger.Error("❌ Write-file path escapes work environment directory", "path", path, "error", err)
		return err
	}

	content = substituteSetupPlaceholders(content, workenvDirForCmd, metadata.Package)

	mode := os.FileMode(0o644)
	if modeFloat, ok := cmd["mode"].(float64); ok {
		modeChecked, err := float64ToFileModeChecked(modeFloat, "setup command mode")
		if err != nil {
			logger.Error("❌ Invalid setup file mode", "mode", modeFloat, "error", err)
			return err
		}
		mode = modeChecked
	}

	if err := writeFileValidated(path, []byte(content+"\n"), mode); err != nil {
		logger.Error("❌ Failed to write file", "path", path, "error", err)
		return fmt.Errorf("failed to write file %s: %w", path, err)
	}

	return nil
}

// resolveSetupCommand turns one metadata.SetupCommands entry into a command
// and its arguments.
//
// An empty command name means there is nothing left to run: the entry did its
// work directly, as write_file does, or nothing could be made of it.
func resolveSetupCommand(
	entry any,
	metadata *Metadata,
	workenvDir string,
	workenvDirForCmd string,
	logger *slog.Logger,
) (string, []string, error) {
	switch cmd := entry.(type) {
	case string:
		return cmd, nil, nil

	case map[string]any:
		cmdType, _ := cmd["type"].(string)
		command, _ := cmd["command"].(string)
		command = substituteSetupPlaceholders(command, workenvDirForCmd, metadata.Package)

		switch cmdType {
		case "enumerate_and_execute":
			return resolveEnumerateAndExecute(cmd, command, workenvDir, logger)
		case "write_file":
			return "", nil, applyWriteFileCommand(cmd, metadata, workenvDir, workenvDirForCmd, logger)
		default:
			return command, nil, nil
		}

	default:
		logger.Warn("⚠️ Unknown setup command type", "type", fmt.Sprintf("%T", entry))
		return "", nil, nil
	}
}

// newSetupExecCommand builds the process for one setup command, with the work
// environment's bin directory ahead of the inherited PATH.
func newSetupExecCommand(
	cmdToRun string,
	cmdArgs []string,
	userCwd string,
	workenvDir string,
	logger *slog.Logger,
) (*exec.Cmd, error) {
	var setupExec *exec.Cmd

	if len(cmdArgs) > 0 {
		setupExec = execCommandValidated(resolveExecutable(cmdToRun, logger), cmdArgs...)
	} else {
		// Shell-aware so quoted arguments survive.
		parts, err := shellparse.Split(cmdToRun)
		if err != nil {
			logger.Error("❌ Failed to parse setup command", "command", cmdToRun, "error", err)
			return nil, fmt.Errorf("failed to parse setup command %q: %w", cmdToRun, err)
		}
		if len(parts) == 0 {
			return nil, nil
		}
		setupExec = execCommandValidated(resolveExecutable(parts[0], logger), parts[1:]...)
	}

	setupExec.Dir = userCwd
	setupExec.Env = setEnv(os.Environ(), EnvWorkenv, workenvDir)

	binDir := "bin"
	if runtime.GOOS == "windows" {
		binDir = "Scripts"
	}
	for i, env := range setupExec.Env {
		if strings.HasPrefix(env, "PATH=") {
			setupExec.Env[i] = fmt.Sprintf("PATH=%s%s%s",
				filepath.Join(workenvDir, binDir),
				string(os.PathListSeparator),
				strings.TrimPrefix(env, "PATH="))
			break
		}
	}

	return setupExec, nil
}

// runSetupCommands runs every setup command the metadata declares, then clears
// the init-lifecycle slots they consumed.
func runSetupCommands(
	metadata *Metadata,
	workenvDir string,
	workenvDirForCmd string,
	userCwd string,
	slotPaths map[int]string,
	logger *slog.Logger,
) error {
	logger.Info("🔧 Running setup commands", "count", len(metadata.SetupCommands))

	metadataDir := filepath.Join(workenvDir, "metadata")
	if err := mkdirAllValidated(metadataDir, os.FileMode(DirPerms)); err != nil {
		logger.Error("❌ Failed to create metadata directory", "error", err)
		return fmt.Errorf("failed to create metadata directory: %w", err)
	}

	for i, entry := range metadata.SetupCommands {
		logger.Debug("🔧 Processing setup command", "index", i)

		cmdToRun, cmdArgs, err := resolveSetupCommand(entry, metadata, workenvDir, workenvDirForCmd, logger)
		if err != nil {
			return err
		}
		if cmdToRun == "" {
			continue
		}

		if len(cmdArgs) == 0 {
			cmdToRun = substituteSetupPlaceholders(cmdToRun, workenvDirForCmd, metadata.Package)
		}

		setupExec, err := newSetupExecCommand(cmdToRun, cmdArgs, userCwd, workenvDir, logger)
		if err != nil {
			return err
		}
		if setupExec == nil {
			continue
		}

		logger.Debug("🏃 Running setup command", "command", cmdToRun, "args", cmdArgs, "cwd", userCwd)
		if output, err := setupExec.CombinedOutput(); err != nil {
			logger.Error("❌ Setup command failed", "command", cmdToRun, "output", string(output))
			return fmt.Errorf("setup command %s failed: %w", cmdToRun, err)
		}
	}

	logger.Info("🧹 Cleaning up lifecycle slots...")
	cleanupLifecycleSlots(workenvDir, metadata, slotPaths, logger)

	return nil
}
