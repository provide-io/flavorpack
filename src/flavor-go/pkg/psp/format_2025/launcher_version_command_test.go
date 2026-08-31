package format_2025

import (
	"os"
	"os/exec"
	"strings"
	"testing"
)

// The builder probes the launcher for its version. That probe runs against a
// standalone launcher binary, which carries no PSPF trailer, so the version
// command must answer without touching the bundle.
func TestCLIVersionCommandReportsVersionWithoutReadingBundle(t *testing.T) {
	cmd := exec.Command(os.Args[0], "-test.run=TestLauncherVersionCommandHelper")
	cmd.Env = filteredEnv(
		EnvLauncherHelper+"=1",
		EnvLauncherMode+"=launch",
		// A path that is not a bundle: the version command must not read it.
		EnvLauncherBundle+"="+"/nonexistent/not-a-bundle",
		EnvLauncherArgs+"=version",
		EnvLauncherCLI+"=1",
	)

	output, err := cmd.CombinedOutput()
	if err != nil {
		t.Fatalf("version command failed: %v\noutput: %s", err, output)
	}
	if !strings.Contains(string(output), LauncherVersion) {
		t.Fatalf("expected output to contain %q, got: %s", LauncherVersion, output)
	}
}

// Outside CLI mode the launcher must never intercept an argument -- every
// argument belongs to the packaged application. "version" is no exception.
func TestVersionArgIsNotInterceptedOutsideCLIMode(t *testing.T) {
	cmd := exec.Command(os.Args[0], "-test.run=TestLauncherVersionCommandHelper")
	cmd.Env = filteredEnv(
		EnvLauncherHelper+"=1",
		EnvLauncherMode+"=launch",
		EnvLauncherBundle+"="+"/nonexistent/not-a-bundle",
		EnvLauncherArgs+"=version",
		// FLAVOR_LAUNCHER_CLI deliberately unset.
	)

	output, _ := cmd.CombinedOutput()
	if strings.Contains(string(output), "\n"+LauncherVersion) || strings.HasPrefix(string(output), LauncherVersion) {
		t.Fatalf("launcher intercepted 'version' outside CLI mode: %s", output)
	}
}

func TestLauncherVersionCommandHelper(t *testing.T) {
	if os.Getenv(EnvLauncherHelper) != "1" {
		return
	}

	bundle := os.Getenv(EnvLauncherBundle)
	rawArgs := os.Getenv(EnvLauncherArgs)
	var args []string
	if rawArgs != "" {
		args = strings.Split(rawArgs, "\x1f")
	}

	if os.Getenv(EnvLauncherMode) == "launch" {
		LaunchWithLogLevel(bundle, args, "", "")
	}
}
