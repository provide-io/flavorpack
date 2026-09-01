package format_2025

import (
	"os"
	"testing"
)

// helperSubprocessMarkers are the environment variables the tests in this
// package use to mark their own re-executions of the test binary. A process
// carrying one of these is standing in for the real launcher, and its exit code
// is what the parent is measuring -- so it keeps the real os.Exit.
//
// A new re-exec harness that forgets to list its marker here will see its
// expected exit code arrive as 2 (Go's code for an unrecovered panic).
var helperSubprocessMarkers = []string{
	EnvLauncherHelper,
	EnvLauncherSubprocess,
	EnvLauncherSpawnExitHelper,
}

func isHelperSubprocess() bool {
	for _, name := range helperSubprocessMarkers {
		if os.Getenv(name) == "1" {
			return true
		}
	}
	return false
}

// TestMain stops a stray exit from taking the test binary with it.
//
// The CLI entry points call osExitFn on their error paths, and osExitFn is
// os.Exit in production. Left as os.Exit in the parent test process, a single
// test that reaches one of those paths terminates the whole binary mid-run: the
// framework never prints --- FAIL:, `go test -json` reports no failing test, and
// every test that had already finished is recorded as PASS. The package goes red
// with nothing to point at, which is how a real regression in verifyBundle went
// unattributed until it was bisected by hand with -run.
//
// Panicking instead keeps the failure attached to the test that caused it. Tests
// that assert on exit codes still install their own osExitFn; this only changes
// what happens to the ones that never expected to exit at all.
func TestMain(m *testing.M) {
	if !isHelperSubprocess() {
		osExitFn = func(code int) {
			panic(launcherExitCode{code: code})
		}
	}
	os.Exit(m.Run())
}
