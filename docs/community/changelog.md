# Changelog

All notable changes to Flavorpack are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Fixed

- **Windows packages reach the release.** A Windows package is written `.exe` so it is
  directly runnable, and the release pipeline globbed `*.psp` at four separate points:
  the collected-packages upload, checksum generation, the extraction step that fed the
  release directory, and the asset list attached to the release. Both Windows `flavor`
  packages were built, collected, uploaded, and then discarded, with every step reporting
  success. The taster build compounded it by writing `.psp` on Windows while the flavor
  build wrote `.exe`, so the two disagreed about what a Windows package is called.
- **`checksums.txt` covers every attached asset.** Checksum generation skipped `.exe`
  packages, so the file the release notes tell users to verify against did not mention
  them. Its section headings are also gone: `sha256sum -c` skips `#` comments but the
  `shasum` macOS ships does not, and reported three improperly formatted lines against a
  wholly correct file.

### Added

- **The release pipeline's shell scripts are linted and tested.** ShellCheck runs as a
  blocking quality gate, and 68 tests cover the ten scripts that assemble and publish a
  release — package and wheel collection, version validation, tag creation, release-run
  selection, checksum generation, release assembly, release notes, and the naming
  contract shared by the two build scripts.
- **The release notes derive their asset list from one platform table**, so they cannot
  advertise a filename the pipeline does not attach.

### Changed

- The Go launcher moves to `provide-telemetry` v0.9.0.

## [0.5.0] - 2026-09-02

### Added

- **The builder asks the launcher it embedded to read the package back** before reporting
  a successful build. A package whose own launcher cannot open it now fails the build
  instead of shipping.
- **Cross-version compatibility fixtures**, committed, so a format change that breaks an
  older launcher is caught by the test suite rather than by a user.
- **A build fails when a wheel outruns the bundled interpreter**, rather than producing a
  package that cannot run what it contains.
- FEP-0002 specifies the JSON metadata document all three implementations read.

### Fixed

- **A launcher no longer releases an extraction lock it never took.** `ReleaseLock`
  removes the lock file without checking ownership, so a process that waited for another
  process's extraction would delete that process's lock on the way out.
- **The three implementations agree on the execution block.** Rust required
  `execution.primary_slot` where Go and Python defaulted it, so a package built without
  that field failed on every Rust launcher; the field is gone. `{slot:N}` now resolves to
  where the slot actually is, and `{primary}` is dropped in favour of the placeholder set
  the launchers share.
- The Rust launcher reads a package that declares no execution block, honours an absolute
  executable path, and never treats an impossible pid as a running process.
- A workenv whose setup never finished is no longer reused.
- Each environment variable is set once during launch.
- The Python launcher's logger no longer holds its mutex while writing to stderr.
- `pip` is asked for every manylinux tag a build accepts.

### Changed

- **CI checks can fail.** The quality gate, License Compliance, and three pretaster suites
  each reported success while verifying nothing — a missing tool, a policy the check could
  not read, and suites whose assertions never ran. Complexity limits are enforced as
  ratchets, and six of the seven `# noqa: C901` suppressions are gone, with the code they
  covered decomposed instead.
- The Go and Rust dependencies move within their majors, and the Rust crypto majors are
  taken now that the compatibility fixtures can catch a break.

## [0.4.6] - 2026-08-23

### Fixed

- Launcher type detection accepts decoded stdout, with a regression suite covering it.

### Added

- `detect-private-key` runs as a pre-commit hook, with the taster's signing fixtures
  exempted and generated signing keys ignored.

## [0.4.5] - 2026-08-16

### Fixed

- The Go launcher follows `provide-telemetry`'s `go/logger` module consolidation.
- `VERSION` keeps its trailing newline.

## [0.4.4] - 2026-05-04

### Fixed

- The FreeBSD helper jobs are opt-in by platform input.
- The release tag check is safe to rerun: it validates the commit rather than failing on
  a tag that already exists.

## [0.4.3] - 2026-05-04

### Changed

- `ci/create-release-tag.sh` is simplified.

## [0.4.2] - 2026-05-04

### Added

- `ci/create-release-tag.sh` creates the release tag idempotently, so rerunning a partial
  release does not fail on a tag that is already there.
- The orchestrator detects the launcher type, with tests covering it.

## [0.4.1] - 2026-04-24

### Fixed

- Helper test JSON aggregation.
- Release artifact selection for the `flavor` package.

## [0.4.0] - 2026-04-20

### Added

- REUSE-compliant licensing: `REUSE.toml` and `LICENSES/Apache-2.0.txt`.
- `CONTRIBUTING.md`.
- An experimental FreeBSD workflow.

### Changed

- The `.provide/foundry` build-tooling directory is no longer tracked.

## [0.3.25] - 2026-04-12

### Fixed

- **Windows system environment variables survive isolation.** The launcher strips the host
  environment, but Windows itself needs `SYSTEMROOT`, `COMSPEC`, `PATHEXT`, `TEMP` and the
  rest for DLL loading, process creation and user-profile resolution. They are added to
  the manifest's `pass` list when building on Windows, in both isolation modes.

## [0.3.24] - 2026-04-10

Tagged, and not published to PyPI.

### Added

- Documentation site styling and scripts.
- `tastesh` builds for Windows.

## [0.3.23] - 2026-04-06

### Removed

- A 640-line generated coverage test file.

## [0.3.22] - 2026-04-06

### Added

- **`tastesh` on Windows** — a pure-Go POSIX `sh` interpreter, so the cross-language test
  payloads run without MSYS2.
- `flavor pack` defaults to `.exe` output on Windows.
- Rust integration tests covering PSPF bundle roundtrips.

### Changed

- The launch policy moves to JSON, with enforcement modes and a version field.
- The pretaster payloads are `tastesh` and `sh` rather than Python.
- The pretaster pipeline builds through the Makefile instead of duplicating the build
  inline.

### Fixed

- Go launcher TAR slots extract to the destination directory, which was double-nesting
  wheels on Windows.
- The taster recognises a Flavor PSP named `.exe`.
- FreeBSD CI: `gmake` for GNU Makefile syntax, `ca_root_nss` for crates.io TLS, and
  `-std=gnu11` for K&R C incompatibility on macOS and FreeBSD.

## [0.3.21] - 2026-03-31

### Added

- Integrity checks across PSPF verification and extraction.
- Pre-commit hooks, with the linter and type-checker findings they surfaced fixed.
- A design specification for trusted keys, SBOM, and launch policy.

### Fixed

- Cross-platform correctness across all three languages: workenv root normalization,
  lifecycle enum and operation chain agreement, slot metadata, and strict type checking.
- Windows compatibility: UTF-8 encoding, entry-point module invocation, `uv` resolution
  next to the Python executable, and arm64 support.
- Rust launcher diagnostics warn on silent failures and match exit codes
  case-insensitively.

## [0.3.0] - 2026-01-11

The first tag under this versioning scheme, covering the system as it then stood.

### Added

- The Progressive Secure Package Format (PSPF/2025) and its specification.
- Go and Rust launchers alongside the Python builder, either able to run any package.
- Ed25519 signing and signature verification, with deterministic key generation, and the
  runtime security model in FEP-0003.
- Work environment management and slot lifecycle, with caching.
- The `flavor` CLI.
- Platform matrix builds, cross-language testing through the pretaster, static musl
  binaries for Linux, and MkDocs documentation.

---

Releases before 0.3.21 were development snapshots published under `0.0.x` version numbers.

For release assets and checksums, see the
[GitHub Releases](https://github.com/provide-io/flavorpack/releases) page.
