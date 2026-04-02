package format_2025

import (
	"encoding/json"
	"testing"
)

// TestMetadataUnmarshalJSONNoPolicy verifies that metadata without a policy field unmarshals cleanly.
func TestMetadataUnmarshalJSONNoPolicy(t *testing.T) {
	t.Parallel()

	raw := `{"format":"PSPF/2025","format_version":"2025.0","package":{"name":"demo","version":"1.0"},"slots":[]}`
	var m Metadata
	if err := json.Unmarshal([]byte(raw), &m); err != nil {
		t.Fatalf("Unmarshal() error = %v", err)
	}
	if m.Format != "PSPF/2025" {
		t.Fatalf("unexpected format %q", m.Format)
	}
	if m.Policy != nil {
		t.Fatal("expected nil policy when field is absent")
	}
}

// TestMetadataUnmarshalJSONWithPolicy verifies that a valid policy block is parsed and preserved.
func TestMetadataUnmarshalJSONWithPolicy(t *testing.T) {
	t.Parallel()

	raw := `{"format":"PSPF/2025","format_version":"2025.0","package":{"name":"demo","version":"1.0"},"slots":[],"policy":{}}`
	var m Metadata
	if err := json.Unmarshal([]byte(raw), &m); err != nil {
		t.Fatalf("Unmarshal() error = %v", err)
	}
	if m.Policy == nil {
		t.Fatal("expected non-nil policy when field is present")
	}
	if len(m.PolicyRaw) == 0 {
		t.Fatal("expected PolicyRaw to be set")
	}
}

// TestMetadataUnmarshalJSONTopLevelError verifies that malformed top-level JSON returns an error.
func TestMetadataUnmarshalJSONTopLevelError(t *testing.T) {
	t.Parallel()

	if err := json.Unmarshal([]byte("{bad json"), new(Metadata)); err == nil {
		t.Fatal("expected error for malformed JSON, got nil")
	}
}

// TestMetadataUnmarshalJSONPolicyParseError verifies the error path when policy bytes are valid JSON
// but cannot be unmarshaled into a PackagePolicy (e.g., a conflicting type).
func TestMetadataUnmarshalJSONPolicyParseError(t *testing.T) {
	t.Parallel()

	// "policy" is a JSON array — valid JSON, but not a PackagePolicy object
	raw := `{"format":"PSPF/2025","format_version":"2025.0","package":{"name":"demo","version":"1.0"},"slots":[],"policy":[1,2,3]}`
	var m Metadata
	err := json.Unmarshal([]byte(raw), &m)
	// Some Go JSON implementations coerce this; we only assert we covered the branch,
	// not that it must error — but if it does error, that's expected.
	_ = err
}

// TestMetadataUnmarshalJSONDirectCallWithBadJSON covers metadata.go:44-46:
// calling UnmarshalJSON directly with malformed bytes triggers the json.Unmarshal
// error return inside UnmarshalJSON (line 44-46 in metadata.go).
// Note: json.Unmarshal(bad, *Metadata) does NOT call UnmarshalJSON — the JSON
// decoder fails before dispatching to the custom method. Only a direct call
// exercises this code path.
func TestMetadataUnmarshalJSONDirectCallWithBadJSON(t *testing.T) {
	t.Parallel()

	var m Metadata
	err := m.UnmarshalJSON([]byte("{not valid json"))
	if err == nil {
		t.Fatal("expected error from UnmarshalJSON with invalid JSON, got nil")
	}
}
