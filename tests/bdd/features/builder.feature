Feature: PSPF Bundle Building
  As a developer
  I want to build PSPF bundles from my applications
  So that I can distribute them easily

  Background:
    Given I have the PSPF builder tools installed
    And I have a project to package

  Scenario: Build from manifest file
    Given a manifest file with:
      """
      name = "myapp"
      version = "1.0.0"
      
      [[slots]]
      path = "dist/myapp.whl"
      purpose = "payload"
      lifecycle = "runtime"
      """
    When I run "pspf build manifest.toml"
    Then a PSPF bundle should be created
    And it should contain the specified slots

  Scenario: Automatic launcher selection
    Given my primary slot is Python code
    When I build without specifying a launcher
    Then the Python launcher should be selected
    And the emoji magic should contain 🐍

  Scenario: Custom emoji selection
    Given I want a specific random emoji
    When I build with "--emoji 🌮"
    Then the emoji magic should be 📦[L]🌮🪄

  Scenario: Compression selection
    Given slots with different content types:
      | file          | type        | best_compression |
      | text.json     | text        | gzip             |
      | binary.so     | binary      | zstd             |
      | random.dat    | random      | none             |
    When I build with auto-compression
    Then each slot should use optimal compression

  Scenario: Build-time validation
    Given a manifest with errors:
      | error                    | message                           |
      | missing_file             | Slot file not found: missing.txt  |
      | invalid_purpose          | Unknown purpose: quantum          |
      | duplicate_slot_index     | Duplicate slot index: 0           |
    When I attempt to build
    Then the build should fail with appropriate errors

  Scenario: Incremental builds
    Given I have built a bundle before
    When I modify only one slot
    And rebuild with "--incremental"
    Then only the changed slot should be recompressed
    And unchanged slots should be reused
    And build time should be faster

  Scenario: Cross-platform building
    Given I am building on "darwin-arm64"
    When I target "linux-amd64"
    Then the launcher should be for linux-amd64
    And the bundle should work on the target platform

  Scenario: Build reproducibility
    Given the same source files
    When I build with "--reproducible"
    Then the output should be deterministic
    And timestamps should be zeroed
    And random emoji should be derived from content

  Scenario: Size optimization
    Given a large bundle
    When I build with "--optimize-size"
    Then aggressive compression should be used
    And duplicate data should be deduplicated
    And the bundle should be smaller

  Scenario: Signing with persistent keys
    Given I have a code signing certificate
    When I build with "--sign-key mykey.pem"
    Then both ephemeral and trust signatures should be created
    And the trust signature should use my key

  Scenario: Multi-slot bundling
    Given a complex application with:
      | component     | slot_type | count |
      | runtimes      | runtime   | 2     |
      | libraries     | library   | 5     |
      | applications  | payload   | 3     |
      | assets        | asset     | 10    |
    When I build the bundle
    Then all 20 slots should be included
    And the metadata should be well-organized
    And slot indices should be sequential