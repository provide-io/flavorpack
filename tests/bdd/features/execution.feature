Feature: Bundle Execution
  As a PSPF user
  I want to execute bundled applications
  So that they run with the correct environment

  Background:
    Given a valid PSPF bundle is available
    And all required slots are extracted

  Scenario: Simple command execution
    Given the execution command is "./myapp"
    When I run the bundle
    Then the primary slot should be executed
    And the process should start successfully

  Scenario: Slot substitution in commands
    Given the execution command is "{slot:0}/bin/python -m {slot:1}/app"
    And slot 0 is extracted to "/cache/python-runtime"
    And slot 1 is extracted to "/cache/myapp"
    When the command is prepared
    Then it should become "/cache/python-runtime/bin/python -m /cache/myapp/app"

  Scenario: Environment variable injection
    Given the execution environment includes:
      | key                | value             |
      | MYAPP_VERSION      | 1.2.3             |
      | MYAPP_CONFIG       | {slot:2}/config   |
    When the bundle executes
    Then the process should have environment:
      | key                | value                |
      | MYAPP_VERSION      | 1.2.3                |
      | MYAPP_CONFIG       | /cache/config/config |

  Scenario: Multi-platform execution
    Given a bundle with platform-specific slots:
      | slot | platform      | selected |
      | 0    | darwin-arm64  | yes      |
      | 1    | darwin-amd64  | no       |
      | 2    | linux-amd64   | no       |
    When executed on "darwin-arm64"
    Then only the matching slot should be used

  Scenario: Missing slot handling
    Given the execution command references {slot:3}
    But slot 3 does not exist
    When I attempt to run the bundle
    Then it should fail with "Referenced slot 3 not found"

  Scenario: Execution with arguments
    Given the bundle is invoked with arguments "–-help --version"
    When the command executes
    Then the arguments should be passed to the primary slot
    And the slot should receive ["--help", "--version"]

  Scenario: Working directory setup
    Given a slot with assets needing relative paths
    When the bundle executes
    Then the working directory should be set correctly
    And relative paths should resolve within the slot

  Scenario: Signal handling
    Given a running PSPF bundle
    When I send SIGTERM
    Then the signal should propagate to the child process
    And cleanup should happen gracefully
    And temporary slots should be removed

  Scenario: Exit code propagation
    Given a slot that exits with code 42
    When the bundle executes
    Then the launcher should exit with code 42
    And the exit code should propagate to the caller

  Scenario: Resource limits
    Given execution limits in metadata:
      | resource     | limit    |
      | memory       | 1GB      |
      | cpu          | 2 cores  |
      | timeout      | 300s     |
    When the bundle executes
    Then resource limits should be applied
    And exceeding limits should terminate the process