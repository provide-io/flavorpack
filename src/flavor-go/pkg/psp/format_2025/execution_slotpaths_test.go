package format_2025

import (
	"path/filepath"
	"strings"
	"testing"

	"github.com/provide-io/flavor/go/flavor/pkg/logging"
)

func TestBuildSlotPathsResolvesTargetsUnderTheWorkenv(t *testing.T) {
	t.Parallel()

	workenv := filepath.Join(string(filepath.Separator), "cache", "workenv", "demo")
	metadata := &Metadata{Slots: []SlotMetadata{
		{Slot: 0, ID: "script", Target: "bin/show.sh"},
		{Slot: 1, ID: "payload", Target: "{workenv}/data/payload.txt"},
	}}

	got := buildSlotPaths(metadata, workenv, logging.NewNullLogger())

	want := map[int]string{
		0: filepath.Join(workenv, "bin", "show.sh"),
		1: filepath.Join(workenv, "data", "payload.txt"),
	}
	for idx, path := range want {
		if got[idx] != path {
			t.Errorf("slot %d = %q, want %q", idx, got[idx], path)
		}
	}
	if len(got) != len(want) {
		t.Errorf("got %d paths, want %d: %v", len(got), len(want), got)
	}
}

// A path is only usable if it names the slot's file. Neither of the values the
// command previously received did: extraction reports a temporary directory
// that is removed before the command runs, and the cached branch assigned every
// slot the workenv root.
func TestBuildSlotPathsNamesFilesNotTheWorkenvRoot(t *testing.T) {
	t.Parallel()

	workenv := filepath.Join(string(filepath.Separator), "cache", "workenv", "demo")
	metadata := &Metadata{Slots: []SlotMetadata{{Slot: 0, ID: "script", Target: "bin/show.sh"}}}

	got := buildSlotPaths(metadata, workenv, logging.NewNullLogger())

	if got[0] == workenv {
		t.Fatalf("slot 0 resolved to the workenv root %q", got[0])
	}
	if strings.Contains(got[0], string(filepath.Separator)+"tmp"+string(filepath.Separator)) {
		t.Errorf("slot 0 resolved into a temporary directory: %q", got[0])
	}
	if !strings.HasSuffix(got[0], filepath.Join("bin", "show.sh")) {
		t.Errorf("slot 0 = %q, want it to end at the slot's target", got[0])
	}
}

func TestBuildSlotPathsDropsATargetThatEscapes(t *testing.T) {
	t.Parallel()

	workenv := filepath.Join(string(filepath.Separator), "cache", "workenv", "demo")
	metadata := &Metadata{Slots: []SlotMetadata{{Slot: 0, ID: "escape", Target: "../../etc/passwd"}}}

	got := buildSlotPaths(metadata, workenv, logging.NewNullLogger())

	if _, present := got[0]; present {
		t.Errorf("a target escaping the workenv must not resolve, got %q", got[0])
	}
}
