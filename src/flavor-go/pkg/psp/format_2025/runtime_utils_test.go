package format_2025

import (
	"sort"
	"testing"

	"github.com/hashicorp/go-hclog"
)

func TestProcessRuntimeEnvAppliesPassUnsetMapAndSet(t *testing.T) {
	t.Parallel()

	env := []string{
		"KEEP_ONE=1",
		"KEEP_TWO=2",
		"DROP_ME=3",
		"MAP_ME=4",
		"EXACT=5",
	}
	runtimeEnv := map[string]interface{}{
		"pass":  []interface{}{"KEEP_*", "EXACT"},
		"unset": []interface{}{"*", "EXACT"},
		"map": map[string]interface{}{
			"MAP_ME": "RENAMED",
		},
		"set": map[string]interface{}{
			"ADDED": "6",
		},
	}

	got := processRuntimeEnv(env, runtimeEnv, hclog.NewNullLogger())
	sort.Strings(got)

	want := []string{
		"ADDED=6",
		"EXACT=5",
		"KEEP_ONE=1",
		"KEEP_TWO=2",
	}
	sort.Strings(want)

	if len(got) != len(want) {
		t.Fatalf("unexpected env length: got=%v want=%v", got, want)
	}
	for i := range want {
		if got[i] != want[i] {
			t.Fatalf("unexpected env entry at %d: got=%v want=%v", i, got, want)
		}
	}
}

func TestGetLauncherPathAndAlignOffset(t *testing.T) {
	t.Setenv(EnvLauncherBin, "/custom/launcher")
	if got := getLauncherPath(""); got != "/custom/launcher" {
		t.Fatalf("getLauncherPath() = %q, want /custom/launcher", got)
	}

	if got := AlignOffset(13, 8); got != 16 {
		t.Fatalf("AlignOffset(13, 8) = %d, want 16", got)
	}
	if got := AlignOffset(16, 8); got != 16 {
		t.Fatalf("AlignOffset(16, 8) = %d, want 16", got)
	}
}
