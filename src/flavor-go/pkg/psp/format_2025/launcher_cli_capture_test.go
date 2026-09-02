package format_2025

import (
	"fmt"
	"io"
	"os"
	"strings"
	"sync"

	"github.com/provide-io/flavor/go/flavor/pkg/logging"
	"testing"
)

// TestCaptureCLIOutputIsolatesConcurrentCaptures pins the property that made
// captureCLIOutput replace the old os.Stdout-swapping helper.
//
// The interleave below is the one a save/restore of a process global cannot
// survive: A opens its capture first and closes it first, while B's capture is
// still open. Restoring "the previous os.Stdout" then hands B's writes to the
// real terminal, and B reads back an empty string. Under the old helper this
// test fails with outB == "" and a stray BBB on stdout.
func TestCaptureCLIOutputIsolatesConcurrentCaptures(t *testing.T) {
	t.Parallel()

	bOpened := make(chan struct{})
	aClosed := make(chan struct{})

	var outA, outB string
	var wg sync.WaitGroup
	wg.Add(2)

	go func() {
		defer wg.Done()
		outA = captureCLIOutput(func(out io.Writer) {
			_, _ = fmt.Fprintln(out, "AAA")
			<-bOpened // hold A's window open until B's has started
		})
		close(aClosed)
	}()

	go func() {
		defer wg.Done()
		outB = captureCLIOutput(func(out io.Writer) {
			close(bOpened)
			<-aClosed // write only after A has finished and "restored"
			_, _ = fmt.Fprintln(out, "BBB")
		})
	}()

	wg.Wait()

	for _, tc := range []struct {
		name, got, want, unwanted string
	}{
		{"A", outA, "AAA", "BBB"},
		{"B", outB, "BBB", "AAA"},
	} {
		if !strings.Contains(tc.got, tc.want) {
			t.Errorf("capture %s lost its own output: got %q, want it to contain %q", tc.name, tc.got, tc.want)
		}
		if strings.Contains(tc.got, tc.unwanted) {
			t.Errorf("capture %s stole the other capture's output: got %q", tc.name, tc.got)
		}
	}
}

// TestCLIFunctionsWriteOnlyToTheWriterTheyAreGiven is the other half: the CLI
// functions must not reach for os.Stdout on their own, or threading a writer
// through them buys nothing.
func TestCLIFunctionsWriteOnlyToTheWriterTheyAreGiven(t *testing.T) {
	t.Parallel()

	logger := logging.NewNullLogger()
	bundle := buildSingleSlotBundleForTests(t, []byte("cli file content"), []byte("cli file content"), nil, SlotMetadata{
		ID:     "cli-slot",
		Target: "{workenv}/bin/app.txt",
	}, 0, false)

	for _, tc := range []struct {
		name string
		call func(io.Writer)
	}{
		{"info", func(w io.Writer) { showBundleInfo(w, bundle, logger) }},
		{"verify", func(w io.Writer) { verifyBundle(w, bundle, logger) }},
		{"metadata", func(w io.Writer) { showMetadata(w, bundle, logger) }},
		{"extract", func(w io.Writer) { extractSlot(w, bundle, "0", t.TempDir(), logger) }},
	} {
		got := captureCLIOutput(func(w io.Writer) {
			// Some of these exit on this fixture -- it is unsigned, so verify
			// fails. They write their output before doing so, and the exit is
			// not what is under test here.
			defer func() { _ = recover() }()
			tc.call(w)
		})
		if got == "" {
			t.Errorf("%s wrote nothing to the writer it was given", tc.name)
		}
	}
}

// TestLauncherCLIHasNoProcessGlobalWrites is the guard that makes the two tests
// above meaningful. They only detect the fault when the writer resolves
// os.Stdout lazily -- which is exactly what fmt.Printf does. So rather than try
// to catch that dynamically, refuse it at the source: launcher_cli.go must route
// everything it prints through the writer it was handed.
//
// The one permitted os.Stdout is the child process's, in spawnBundle. That has
// to be a real file descriptor and cannot be a buffer.
func TestLauncherCLIHasNoProcessGlobalWrites(t *testing.T) {
	t.Parallel()

	src, err := os.ReadFile("launcher_cli.go")
	if err != nil {
		t.Fatalf("read launcher_cli.go: %v", err)
	}

	const allowed = "cmd.Stdout = os.Stdout"
	banned := []string{"fmt.Print(", "fmt.Printf(", "fmt.Println("}

	for i, line := range strings.Split(string(src), "\n") {
		code, _, _ := strings.Cut(line, "//")
		for _, b := range banned {
			if strings.Contains(code, b) {
				t.Errorf("launcher_cli.go:%d writes to process stdout via %s -- write to the out writer instead:\n\t%s",
					i+1, b, strings.TrimSpace(line))
			}
		}
		if strings.Contains(code, "os.Stdout") && !strings.Contains(code, allowed) {
			t.Errorf("launcher_cli.go:%d reaches for os.Stdout -- write to the out writer instead:\n\t%s",
				i+1, strings.TrimSpace(line))
		}
	}
}
