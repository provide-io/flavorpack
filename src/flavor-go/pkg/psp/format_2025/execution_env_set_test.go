package format_2025

import (
	"testing"
)

func TestSetEnvReplacesRatherThanDuplicating(t *testing.T) {
	t.Parallel()

	env := []string{"HOME=/home/tim", "FLAVOR_WORKENV=/old", "PATH=/usr/bin"}
	got := setEnv(env, "FLAVOR_WORKENV", "/new")

	if len(got) != 3 {
		t.Fatalf("len = %d, want 3 — the entry should be replaced, not added: %v", len(got), got)
	}
	if value := envValue(t, got, "FLAVOR_WORKENV"); value != "/new" {
		t.Errorf("FLAVOR_WORKENV = %q, want %q", value, "/new")
	}
	assertNoDuplicateEnvKeys(t, got)
}

func TestSetEnvAppendsWhenAbsent(t *testing.T) {
	t.Parallel()

	env := []string{"HOME=/home/tim"}
	got := setEnv(env, "FLAVOR_WORKENV", "/new")

	if len(got) != 2 {
		t.Fatalf("len = %d, want 2: %v", len(got), got)
	}
	if value := envValue(t, got, "FLAVOR_WORKENV"); value != "/new" {
		t.Errorf("FLAVOR_WORKENV = %q, want %q", value, "/new")
	}
}

// A key is matched whole. FLAVOR_WORKENV_CACHE must not be mistaken for
// FLAVOR_WORKENV, which a prefix test without the "=" would do.
func TestSetEnvMatchesTheWholeKey(t *testing.T) {
	t.Parallel()

	env := []string{"FLAVOR_WORKENV_CACHE=false"}
	got := setEnv(env, "FLAVOR_WORKENV", "/new")

	if len(got) != 2 {
		t.Fatalf("len = %d, want 2 — FLAVOR_WORKENV_CACHE is a different key: %v", len(got), got)
	}
	if value := envValue(t, got, "FLAVOR_WORKENV_CACHE"); value != "false" {
		t.Errorf("FLAVOR_WORKENV_CACHE = %q, want %q", value, "false")
	}
	if value := envValue(t, got, "FLAVOR_WORKENV"); value != "/new" {
		t.Errorf("FLAVOR_WORKENV = %q, want %q", value, "/new")
	}
}

func TestSetEnvKeepsOtherEntriesInOrder(t *testing.T) {
	t.Parallel()

	env := []string{"A=1", "B=2", "C=3"}
	got := setEnv(env, "B", "changed")

	want := []string{"A=1", "B=changed", "C=3"}
	for i := range want {
		if got[i] != want[i] {
			t.Errorf("entry %d = %q, want %q", i, got[i], want[i])
		}
	}
}
