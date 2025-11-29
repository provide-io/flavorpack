// SPDX-License-Identifier: Apache-2.0
// Package format_2025 implements PSPF/2025 package format support
package format_2025

import (
	"fmt"
	"os"
	"os/exec"
	"syscall"

	"github.com/hashicorp/go-hclog"
)

// executeCommand executes the command, handling both exec and spawn modes.
// Returns error if execution fails in spawn mode; exec mode never returns.
func executeCommand(cmd *exec.Cmd, useExec bool, logger hclog.Logger) error {
	if useExec {
		return executeViaExec(cmd, logger)
	}
	return executeViaSpawn(cmd, logger)
}

// executeViaExec replaces the current process with the command using syscall.Exec.
// This mode never returns on success.
func executeViaExec(cmd *exec.Cmd, logger hclog.Logger) error {
	logger.Debug("🔄 Using exec mode - process will be replaced")

	binary, err := exec.LookPath(cmd.Path)
	if err != nil {
		return fmt.Errorf("failed to find command %s: %w", cmd.Path, err)
	}

	argv := []string{binary}
	if len(cmd.Args) > 1 {
		argv = append(argv, cmd.Args[1:]...)
	}

	envv := cmd.Env
	if envv == nil {
		envv = os.Environ()
	}

	logger.Debug("🔍 Checking if executable is script",
		"path", binary,
		"First line", getFirstLine(binary),
		"Has shebang", hasShebang(binary))
	logger.Info("🚀 Executing script", "path", binary)
	logger.Debug("🚀 Full command with args", "args", argv[1:])
	logger.Info("🔄 Replacing process via exec()")

	// This replaces the current process and never returns on success
	err = syscall.Exec(binary, argv, envv)
	return fmt.Errorf("exec failed: %w", err)
}

// executeViaSpawn spawns a child process and waits for it to complete.
func executeViaSpawn(cmd *exec.Cmd, logger hclog.Logger) error {
	logger.Debug("🔄 Using spawn mode - child process will be created")
	logger.Info("🚀 Executing command", "path", cmd.Path)
	logger.Debug("🚀 Full command with args", "args", cmd.Args[1:])

	if err := cmd.Start(); err != nil {
		return fmt.Errorf("failed to start process: %w", err)
	}

	if err := cmd.Wait(); err != nil {
		// Check for exit code
		if exitErr, ok := err.(*exec.ExitError); ok {
			logger.Info("⏹️ Process exited", "code", exitErr.ExitCode())
			return fmt.Errorf("exit code %d", exitErr.ExitCode())
		}
		return fmt.Errorf("process error: %w", err)
	}

	logger.Info("✅ Process completed successfully")
	return nil
}

// getFirstLine returns the first line of a file for checking shebangs.
func getFirstLine(path string) string {
	data, err := os.ReadFile(path)
	if err != nil {
		return ""
	}
	if len(data) > 50 {
		return string(data[:50])
	}
	return string(data)
}

// hasShebang checks if a file starts with a shebang.
func hasShebang(path string) bool {
	data, err := os.ReadFile(path)
	if err != nil || len(data) < 2 {
		return false
	}
	return data[0] == '#' && data[1] == '!'
}

// 🌶️📦🖥️🪄
