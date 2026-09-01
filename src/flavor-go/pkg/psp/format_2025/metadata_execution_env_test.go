package format_2025

import (
	"encoding/json"
	"testing"
)

// The package environment is written under "env" by both the Rust and the
// Python implementations, and Python's executor reads it from there. Go used to
// declare the field as `json:"environment"`, so it silently dropped an env
// block written by either of the others -- a package that sets MODE=prod ran
// with no MODE at all under the Go launcher, with no error to say so. Worse,
// Go re-emitted what it did read as "environment", converting a block the other
// two could see into one they could not. See #36.
func TestExecutionInfoReadsEnvKey(t *testing.T) {
	t.Parallel()

	for _, tc := range []struct {
		name string
		in   string
		want map[string]string
	}{
		{
			name: "env is the key the other implementations write",
			in:   `{"primary_slot":0,"command":"true","env":{"MODE":"prod"}}`,
			want: map[string]string{"MODE": "prod"},
		},
		{
			name: "environment is still accepted from packages Go built before",
			in:   `{"primary_slot":0,"command":"true","environment":{"MODE":"prod"}}`,
			want: map[string]string{"MODE": "prod"},
		},
		{
			name: "env wins when a package somehow carries both",
			in:   `{"command":"true","env":{"MODE":"new"},"environment":{"MODE":"old"}}`,
			want: map[string]string{"MODE": "new"},
		},
		{
			name: "neither key present",
			in:   `{"command":"true"}`,
			want: nil,
		},
	} {
		t.Run(tc.name, func(t *testing.T) {
			t.Parallel()

			var got ExecutionInfo
			if err := json.Unmarshal([]byte(tc.in), &got); err != nil {
				t.Fatalf("Unmarshal(%s) error = %v", tc.in, err)
			}
			if len(got.Environment) != len(tc.want) {
				t.Fatalf("Environment = %v, want %v", got.Environment, tc.want)
			}
			for k, v := range tc.want {
				if got.Environment[k] != v {
					t.Errorf("Environment[%q] = %q, want %q", k, got.Environment[k], v)
				}
			}
		})
	}
}

// Whatever Go reads, it must write back under the key the others read.
func TestExecutionInfoWritesEnvKey(t *testing.T) {
	t.Parallel()

	for _, in := range []string{
		`{"command":"true","env":{"MODE":"prod"}}`,
		`{"command":"true","environment":{"MODE":"prod"}}`,
	} {
		var e ExecutionInfo
		if err := json.Unmarshal([]byte(in), &e); err != nil {
			t.Fatalf("Unmarshal(%s) error = %v", in, err)
		}

		out, err := json.Marshal(e)
		if err != nil {
			t.Fatalf("Marshal error = %v", err)
		}

		var round struct {
			Env    map[string]string `json:"env"`
			Legacy map[string]string `json:"environment"`
		}
		if err := json.Unmarshal(out, &round); err != nil {
			t.Fatalf("Unmarshal(%s) error = %v", out, err)
		}
		if round.Env["MODE"] != "prod" {
			t.Errorf("re-emitted %s, want the environment under \"env\"", out)
		}
		if round.Legacy != nil {
			t.Errorf("re-emitted %s, which the Rust and Python readers ignore", out)
		}
	}
}

// A missing primary_slot is valid -- Rust now defaults it too (#36).
func TestExecutionInfoPrimarySlotDefaultsToZero(t *testing.T) {
	t.Parallel()

	var e ExecutionInfo
	if err := json.Unmarshal([]byte(`{"command":"true"}`), &e); err != nil {
		t.Fatalf("Unmarshal error = %v", err)
	}
	if e.PrimarySlot != 0 {
		t.Errorf("PrimarySlot = %d, want 0", e.PrimarySlot)
	}
}

// The same key disagreement existed one level up, in the manifest the builder
// reads. Python writes "env" into the manifest it hands to flavor-go-builder,
// and ExecutionConfig was tagged "environment" -- so an execution environment
// set by the caller was dropped at build time, before it ever reached a bundle.
func TestExecutionConfigReadsEnvKey(t *testing.T) {
	t.Parallel()

	for _, tc := range []struct {
		name string
		in   string
	}{
		{"env, as Python writes it", `{"command":"true","env":{"MODE":"prod"}}`},
		{"environment, as older manifests have it", `{"command":"true","environment":{"MODE":"prod"}}`},
	} {
		t.Run(tc.name, func(t *testing.T) {
			t.Parallel()

			var got ExecutionConfig
			if err := json.Unmarshal([]byte(tc.in), &got); err != nil {
				t.Fatalf("Unmarshal(%s) error = %v", tc.in, err)
			}
			if got.Environment["MODE"] != "prod" {
				t.Errorf("Environment = %v, want MODE=prod", got.Environment)
			}
		})
	}
}

// Both custom unmarshalers must still surface a malformed document rather than
// swallowing the error and leaving a zero value behind.
func TestExecutionUnmarshalRejectsMalformedJSON(t *testing.T) {
	t.Parallel()

	for _, tc := range []struct {
		name string
		into json.Unmarshaler
	}{
		{"ExecutionInfo", &ExecutionInfo{}},
		{"ExecutionConfig", &ExecutionConfig{}},
	} {
		t.Run(tc.name, func(t *testing.T) {
			t.Parallel()

			if err := tc.into.UnmarshalJSON([]byte(`{"command":`)); err == nil {
				t.Error("expected an error from truncated JSON, got nil")
			}
			if err := tc.into.UnmarshalJSON([]byte(`{"env":"not-a-map"}`)); err == nil {
				t.Error("expected an error when env is not an object, got nil")
			}
		})
	}
}
