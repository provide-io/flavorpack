package format_2025

import "testing"

func TestValidationLevelParsing(t *testing.T) {
	t.Run("environment override", func(t *testing.T) {
		cases := []struct {
			name string
			env  string
			want ValidationLevel
		}{
			{name: "strict", env: "strict", want: ValidationStrict},
			{name: "standard", env: "standard", want: ValidationStandard},
			{name: "relaxed", env: "relaxed", want: ValidationRelaxed},
			{name: "minimal", env: "minimal", want: ValidationMinimal},
			{name: "none", env: "none", want: ValidationNone},
			{name: "uppercase", env: "STRICT", want: ValidationStrict},
		}

		for _, tc := range cases {
			tc := tc
			t.Run(tc.name, func(t *testing.T) {
				t.Setenv(EnvValidation, tc.env)
				if got := getValidationLevel(); got != tc.want {
					t.Fatalf("getValidationLevel() = %v, want %v", got, tc.want)
				}
			})
		}
	})

	t.Run("default and invalid fallback", func(t *testing.T) {
		t.Setenv(EnvValidation, "")
		if got := getValidationLevel(); got != ValidationStrict {
			t.Fatalf("getValidationLevel() default = %v, want %v", got, ValidationStrict)
		}

		t.Setenv(EnvValidation, "not-a-level")
		if got := getValidationLevel(); got != ValidationStrict {
			t.Fatalf("getValidationLevel() invalid fallback = %v, want %v", got, ValidationStrict)
		}
	})
}

func TestIsEnvTrue(t *testing.T) {
	cases := []struct {
		name string
		val  string
		want bool
	}{
		{name: "empty", val: "", want: false},
		{name: "on", val: "on", want: true},
		{name: "yes", val: "yes", want: true},
		{name: "true", val: "true", want: true},
		{name: "uppercase true", val: "TRUE", want: true},
		{name: "one", val: "1", want: true},
		{name: "false", val: "false", want: false},
		{name: "off", val: "off", want: false},
		{name: "zero", val: "0", want: false},
	}

	for _, tc := range cases {
		tc := tc
		t.Run(tc.name, func(t *testing.T) {
			t.Setenv("FLAVOR_TEST_BOOL", tc.val)
			if got := isEnvTrue("FLAVOR_TEST_BOOL"); got != tc.want {
				t.Fatalf("isEnvTrue(%q) = %v, want %v", tc.val, got, tc.want)
			}
		})
	}
}
