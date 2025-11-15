Feature: PSPF 2025 CLI Cross-Language Support
  As a developer
  I want to use the PSPF CLI with any language
  So that I can build, inspect, and execute bundles regardless of implementation language

  Scenario Outline: Build PSPF bundle with different languages
    Given I have a <language> project "test_app"
    And I have a PSPF manifest for <language>
    When I build the <language> bundle using the CLI
    Then the build succeeds
    And the bundle contains the correct launcher emoji
    
    Examples:
      | language |
      | Python   |
      | Go       |
      | Rust     |
      | Node.js  |

  Scenario Outline: Cross-language builder and launcher combinations
    Given I have a Python project "cross_test"
    When I build with <builder> builder and <launcher> launcher
    Then the build succeeds
    And the bundle contains the correct launcher emoji
    
    Examples:
      | builder | launcher |
      | Python  | Go       |
      | Python  | Rust     |
      | Go      | Python   |
      | Go      | Node.js  |
      | Rust    | Python   |
      | Rust    | Go       |

  Scenario: Inspect PSPF bundle using CLI
    Given I have a Python project "inspect_test"
    And I have a PSPF manifest for Python
    When I build the Python bundle using the CLI
    And I inspect the bundle using the CLI
    Then the inspection shows 1 slot(s)

  Scenario: Execute PSPF bundle using CLI
    Given I have a Go project "exec_test"
    And I have a PSPF manifest for Go
    When I build the Go bundle using the CLI
    And I execute the bundle using the CLI
    Then I can execute the bundle successfully

  Scenario: Verify PSPF bundle signatures using CLI
    Given I have a Rust project "verify_test"
    And I have a PSPF manifest for Rust
    When I build the Rust bundle using the CLI
    And I verify the bundle signatures using the CLI
    Then the bundle is valid and verified

  Scenario: Test all language combinations
    Given I have bundles built with all language combinations
    When I test all builder/launcher combinations
    Then all combinations work correctly