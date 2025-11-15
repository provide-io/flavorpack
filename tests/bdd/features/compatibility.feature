Feature: Cross-Language Compatibility
  As a polyglot developer
  I want PSPF to work across languages and platforms
  So that I can use the best tool for each job

  Scenario: Python builder with Go launcher
    Given I build a bundle with Python builder
    And I use a Go launcher
    When I execute the bundle
    Then it should run correctly
    And all slots should be accessible

  Scenario: Go builder with Rust launcher
    Given I build a bundle with Go builder
    And I use a Rust launcher
    When I execute the bundle
    Then it should run correctly
    And checksums should verify

  Scenario: Rust builder with Python launcher
    Given I build a bundle with Rust builder
    And I use a Python launcher
    When I execute the bundle
    Then it should run correctly
    And emoji magic should be parsed correctly

  Scenario Outline: Checksum compatibility
    Given a slot with checksum algorithm <algorithm>
    When processed by <language> implementation
    Then the checksum should compute to <expected>

    Examples:
      | algorithm | language | expected    |
      | sha256    | python   | abc123...   |
      | sha256    | go       | abc123...   |
      | sha256    | rust     | abc123...   |

  Scenario: Compression compatibility
    Given slots compressed with different algorithms:
      | slot    | algorithm | language |
      | slot-0  | gzip      | python   |
      | slot-1  | zstd      | go       |
      | slot-2  | none      | rust     |
    When each language reads all slots
    Then all should decompress correctly

  Scenario: UTF-8 emoji handling
    Given emoji magic 📦🐍🌮🪄
    When read by different languages:
      | language | library        |
      | python   | standard       |
      | go       | standard       |
      | rust     | standard       |
      | node     | standard       |
    Then all should read identical bytes

  Scenario: Platform path handling
    Given slots with paths:
      | platform | path_style              |
      | windows  | C:\cache\slots\myapp    |
      | unix     | /cache/slots/myapp      |
    When building cross-platform
    Then paths should be normalized
    And work on all platforms

  Scenario: Binary parsing compatibility
    Given a PSPF bundle
    When parsed by different implementations:
      | language | parser_type     |
      | python   | struct.unpack   |
      | go       | binary.Read     |
      | rust     | byteorder       |
    Then all should read identical values

  Scenario: Metadata JSON compatibility
    Given complex metadata with:
      | feature          | test_case              |
      | unicode          | "hello 世界 🌍"         |
      | numbers          | 1.23e-10               |
      | special_chars    | "quote\" and \n"       |
    When parsed by each language
    Then values should be preserved exactly

  Scenario: Large file handling
    Given a 2GB slot
    When processed by each language
    Then all should handle it correctly
    And not hit 32-bit limitations

  Scenario: Endianness handling
    Given binary data in the index block
    When read on different architectures:
      | architecture | endianness |
      | x86_64       | little     |
      | s390x        | big        |
    Then values should be consistent
    Because PSPF mandates little-endian