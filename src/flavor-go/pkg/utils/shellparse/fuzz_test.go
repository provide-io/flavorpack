package shellparse

import "testing"

// FuzzSplit verifies Split never panics on arbitrary input.
func FuzzSplit(f *testing.F) {
	// Seed corpus from interesting edge cases
	seeds := []string{
		"",
		"cmd",
		"cmd arg",
		`"quoted arg"`,
		`'single'`,
		`cmd "arg with spaces"`,
		`a\nb`,
		`cmd "unclosed`,
		`trailing\`,
		"/usr/bin/python3 {slot:0}",
		`echo "hello 'world'"`,
		`bash -c "echo $HOME"`,
	}
	for _, s := range seeds {
		f.Add(s)
	}

	f.Fuzz(func(t *testing.T, s string) {
		// Must never panic; errors are acceptable
		_, _ = Split(s)
	})
}

// FuzzSplitJoinIdempotent verifies that a successful Split→Join→Split
// round-trip produces identical results (idempotency of the joined form).
func FuzzSplitJoinIdempotent(f *testing.F) {
	seeds := []string{
		"cmd arg1 arg2",
		`python3 -c "print('hi')"`,
		`/usr/bin/env bash -c "echo hello"`,
	}
	for _, s := range seeds {
		f.Add(s)
	}

	f.Fuzz(func(t *testing.T, s string) {
		first, err := Split(s)
		if err != nil {
			return // parse errors are fine
		}
		joined := Join(first)
		second, err := Split(joined)
		if err != nil {
			t.Fatalf("Split(Join(Split(%q))) error: %v", s, err)
		}
		if len(first) != len(second) {
			t.Fatalf("length mismatch after round-trip: %d != %d\n  first:  %v\n  second: %v",
				len(first), len(second), first, second)
		}
		for i := range first {
			if first[i] != second[i] {
				t.Fatalf("element %d differs after round-trip: %q != %q", i, first[i], second[i])
			}
		}
	})
}
