Feature: PSPF 2025 Core Format
  As a package builder
  I want to create valid PSPF bundles
  So that they can be distributed and executed reliably

  Background:
    Given the PSPF 2025 specification is implemented
    And ephemeral keys are available for integrity sealing

  Scenario: Create minimal PSPF bundle
    Given I have a simple executable payload
    When I build a PSPF bundle with default settings
    Then the bundle should have a valid structure
    And the emoji magic should end with 📦??🪄
    And the index block should be at offset launcher_size
    And the index block should be exactly 256 bytes
    And the metadata should be at offset launcher_size + 256

  Scenario: Verify index block structure
    Given I have a valid PSPF bundle
    When I read the index block
    Then the format magic should be "PSPF2025"
    And the format version should be 0x20250001
    And the index checksum should be valid
    And the metadata offset should equal launcher_size + 256
    And the alignment should be 8 bytes

  Scenario: Create bundle with multiple slots
    Given I have the following slots:
      | name          | purpose   | compression | lifecycle  |
      | python-3.13   | runtime   | zstd        | persistent |
      | myapp.whl     | payload   | gzip        | install    |
      | models.data   | asset     | none        | persistent |
    When I build a PSPF bundle
    Then each slot should be aligned to 8 bytes
    And the metadata should list all 3 slots
    And each slot should have a valid checksum

  Scenario Outline: Emoji magic variations
    Given I have a launcher of type <launcher_type>
    When I build a PSPF bundle with emoji seed <seed>
    Then the emoji magic should be <expected_magic>

    Examples:
      | launcher_type | seed | expected_magic |
      | go            | 1    | 📦🐹🦄🪄        |
      | rust          | 2    | 📦🦀🍕🪄        |
      | python        | 3    | 📦🐍🌈🪄        |
      | native        | 4    | 📦⚡🎸🪄        |

  Scenario: Verify ephemeral integrity seal
    Given I have a PSPF bundle with integrity seal
    When I extract the metadata
    Then the integrity directory should contain:
      | file            | description                    |
      | seal.sig        | ECDSA signature of psp.json    |
      | seal.pem        | Ephemeral public key           |
      | metadata.json   | Key generation metadata        |
    And the seal signature should verify against psp.json
    And the key should be marked as ephemeral

  Scenario: Bundle size limits
    Given I have slots totaling 100MB
    When I build a PSPF bundle
    Then the index block overhead should be exactly 256 bytes
    And the emoji magic overhead should be exactly 16 bytes
    And the total overhead should be less than 1% of package size

  Scenario: Invalid bundle detection
    Given I have a file that is not a PSPF bundle
    When I attempt to read it as PSPF
    Then it should fail with "Missing package emoji"
    
  Scenario: Corrupted index block
    Given I have a PSPF bundle with corrupted index
    When I attempt to read the bundle
    Then it should fail with "Index checksum mismatch"