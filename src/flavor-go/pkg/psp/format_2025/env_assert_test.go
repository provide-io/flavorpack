package format_2025

import (
	"os"
	"strings"
	"testing"
)

// envEntry returns the `KEY=value` entry for key, and fails the test naming only
// the key when there is none.
//
// The environment a launcher hands a package inherits the one the tests run in,
// so it holds whatever the developer or the CI runner has set. Reporting a
// missing variable by printing all of them puts every one of those values into
// the failure output, which on CI is a build log. Report the entry under test
// and the number of entries; that is what the assertion is about.
func envEntry(t *testing.T, env []string, key string) string {
	t.Helper()

	prefix := key + "="
	var found []string
	for _, entry := range env {
		if strings.HasPrefix(entry, prefix) {
			found = append(found, entry)
		}
	}

	if len(found) == 0 {
		t.Fatalf("no %s entry among the %d environment entries", key, len(env))
		return ""
	}

	// exec.Cmd deduplicates before starting the process and keeps the last
	// occurrence, so that is the value the package receives.
	return found[len(found)-1]
}

// envValue returns the value of key, failing the test if it is absent.
func envValue(t *testing.T, env []string, key string) string {
	t.Helper()
	return strings.TrimPrefix(envEntry(t, env, key), key+"=")
}

// TestNoTestFormatsTheWholeEnvironment refuses the pattern envEntry exists to
// replace.
//
// A failure message built from the whole of cmd.Env or os.Environ() prints
// every variable the test process holds. That reads as harmless until the test
// fails on a machine with credentials in the environment, or on CI, where the
// output is a build log. It is the failing case that leaks, which is the case
// nobody rehearses.
func TestNoTestFormatsTheWholeEnvironment(t *testing.T) {
	t.Parallel()

	entries, err := os.ReadDir(".")
	if err != nil {
		t.Fatalf("read package directory: %v", err)
	}

	// Joining the environment into one string is the shape that reaches a
	// format verb; anything narrower names a single variable.
	banned := []string{
		"strings.Join(cmd.Env",
		"strings.Join(os.Environ()",
	}

	checked := 0
	for _, entry := range entries {
		name := entry.Name()
		if entry.IsDir() || !strings.HasSuffix(name, "_test.go") || name == "env_assert_test.go" {
			continue
		}

		src, err := os.ReadFile(name) //nolint:gosec // fixture path is a directory entry
		if err != nil {
			t.Fatalf("read %s: %v", name, err)
		}
		checked++

		for lineNo, line := range strings.Split(string(src), "\n") {
			code, _, _ := strings.Cut(line, "//")
			for _, pattern := range banned {
				if strings.Contains(code, pattern) {
					t.Errorf("%s:%d builds a failure message from the whole environment via %s -- use envValue(t, cmd.Env, key) instead:\n\t%s",
						name, lineNo+1, pattern, strings.TrimSpace(line))
				}
			}
		}
	}

	if checked == 0 {
		t.Fatal("no test files scanned; this guard is checking nothing")
	}
}

// assertNoDuplicateEnvKeys fails when a key appears more than once in the
// environment handed to a package.
//
// exec.Cmd deduplicates before starting the process and keeps the last
// occurrence, so a duplicate is survivable — but only because of that rule.
// Anything reading the slice directly sees the first entry, and a launcher that
// grew a direct execve path would inherit neither the rule nor the intent.
func assertNoDuplicateEnvKeys(t *testing.T, env []string) {
	t.Helper()

	seen := make(map[string]int, len(env))
	for _, entry := range env {
		key, _, found := strings.Cut(entry, "=")
		if !found {
			continue
		}
		seen[key]++
	}

	for key, count := range seen {
		if count > 1 {
			// The key is named; the values are not, since they are whatever the
			// environment held.
			t.Errorf("%s appears %d times in the environment handed to the package", key, count)
		}
	}
}
