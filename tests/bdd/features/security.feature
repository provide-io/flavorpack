Feature: PSPF Security Model
  As a security-conscious user
  I want PSPF bundles to be tamper-evident
  So that I can trust the software I run

  Background:
    Given the cryptographic libraries are available
    And the PSPF bundle builder is configured

  Scenario: Ephemeral key generation
    When I build a PSPF bundle
    Then a new key pair should be generated
    And the private key should be used once
    And the private key should be discarded
    And only the public key should be in the bundle

  Scenario: Integrity seal verification
    Given a PSPF bundle with integrity seal
    When the launcher verifies the bundle
    Then the psp.json signature should be checked
    And the signature should match the ephemeral public key
    And tampering should be detected

  Scenario: Tampered metadata detection
    Given a valid PSPF bundle
    When someone modifies the psp.json after building
    Then the launcher should detect tampering
    And refuse to extract slots
    And report "Integrity seal verification failed"

  Scenario: Tampered slot detection
    Given a valid PSPF bundle
    When someone modifies a slot's data
    Then the slot checksum should fail
    And the launcher should refuse to use the slot
    And report which slot was tampered

  Scenario: Trust signature verification
    Given a PSPF bundle with trust signatures
    And a list of allowed signers
    When the launcher verifies trust
    Then it should check each signature
    And accept signatures from allowed signers
    And reject signatures from unknown signers

  Scenario: Missing integrity seal
    Given a PSPF bundle without integrity seal
    When the launcher attempts to load it
    Then it should fail with "Missing required integrity seal"

  Scenario: Corrupted emoji magic
    Given a PSPF bundle
    When the emoji magic is corrupted
    Then the launcher should detect it immediately
    And fail fast with "Invalid PSPF magic"

  Scenario: Index block tampering
    Given a PSPF bundle
    When someone modifies the index block
    Then the CRC32 check should fail
    And the launcher should refuse to proceed
    And report "Index checksum mismatch"

  Scenario: Build reproducibility
    Given the same source files
    When I build PSPF bundles at different times
    Then the bundles should differ only in:
      | component           | reason                    |
      | ephemeral_key       | New key each build        |
      | build_timestamp     | Different build times     |
      | random_emoji        | Build fingerprinting      |
    And the slots should be byte-identical

  Scenario: Signature algorithm negotiation
    Given support for multiple algorithms:
      | algorithm    | status     |
      | ecdsa-p256   | required   |
      | ed25519      | optional   |
      | rsa-pss      | deprecated |
    When I build with algorithm "ed25519"
    Then the seal should use Ed25519
    And compatible launchers should verify it
    And old launchers should report unsupported algorithm