Feature: Slot Lifecycle Management
  As a PSPF launcher
  I want to manage slot extraction and cleanup
  So that disk space is used efficiently

  Background:
    Given a PSPF bundle is loaded
    And the cache directory is empty

  Scenario: Persistent slot extraction
    Given a slot with lifecycle "persistent"
    When the launcher extracts the slot
    Then the slot should be cached
    And subsequent runs should use the cached version
    And the cache should persist between executions

  Scenario: Volatile slot extraction
    Given a slot with lifecycle "volatile"
    When the launcher extracts the slot
    Then the slot should be extracted fresh
    And any cached version should be ignored
    And the extraction should happen on every run

  Scenario: Temporary slot cleanup
    Given a slot with lifecycle "temporary"
    When the launcher extracts the slot
    And the execution completes
    Then the slot should be removed from disk
    And the cleanup should happen automatically

  Scenario: Install slot behavior
    Given a slot with lifecycle "install" and cleanup "after_install"
    When the launcher extracts the slot
    And the installation completes
    Then the slot archive should be removed
    But the installed files should remain

  Scenario: Conditional slot extraction
    Given slots with platform conditions:
      | name            | condition                        |
      | darwin-runtime  | os == 'darwin'                   |
      | linux-runtime   | os == 'linux'                    |
      | arm64-lib       | arch == 'arm64'                  |
    When the launcher evaluates conditions on "darwin" with "arm64"
    Then only these slots should be extracted:
      | name            |
      | darwin-runtime  |
      | arm64-lib       |

  Scenario: Slot alignment verification
    Given a bundle with multiple slots
    When I verify the slot positions
    Then each slot offset should be divisible by 8
    And padding between slots should be zero bytes

  Scenario: Parallel slot extraction
    Given a bundle with 5 large slots
    And parallel extraction is enabled
    When the launcher extracts all slots
    Then multiple slots should extract simultaneously
    And the total time should be less than sequential extraction

  Scenario: Slot checksum verification
    Given a slot with SHA-256 checksum
    When the launcher extracts the slot
    Then the checksum should be verified
    And extraction should fail if checksum mismatches

  Scenario: Cache corruption recovery
    Given a cached slot with corrupted data
    When the launcher verifies the cache
    Then the corruption should be detected
    And the slot should be re-extracted
    And the fresh extraction should succeed

  Scenario: Cleanup timing
    Given slots with different cleanup timings:
      | name       | lifecycle | cleanup          |
      | installer  | install   | after_install    |
      | temp-tool  | temporary | after_run        |
      | old-lib    | persistent| on_update        |
    When the respective trigger occurs
    Then each slot should be cleaned up at the right time