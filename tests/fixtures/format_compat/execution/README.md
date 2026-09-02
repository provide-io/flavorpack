# The execution block contract

`execution-block.json` is one metadata document that all three implementations
must read the same way. It exists because they did not.

## The environment key

Rust and Python both read and write `env`. Go declared the field as
`environment`, so it silently dropped an environment block written by either of
the others — a package setting `MODE=prod` ran with no `MODE` under the Go
launcher, with nothing said — and re-emitted anything it did read under a key
the other two ignore. Go now uses `env`, and still accepts `environment` when
reading, so packages it built before keep working. See #36.

The document therefore carries a non-empty `env`, and every implementation must
see `MODE=prod` in it.

## What the block contains

`command` and `env`. That is the whole of it: the launchers decide extraction,
the working directory and the command without anything else in the block.

`execution.primary_slot` is not here, and no implementation models it. Packages
built while it was written carry it, and every reader ignores members it does
not declare, so those packages stay readable — `TestCommittedPackagesCarry
UnmodelledExecutionFields` and its counterparts assert exactly that against the
frozen packages in `v1/`, which do carry the field. Adding
`deny_unknown_fields` to the Rust structure, or `DisallowUnknownFields` to the
Go decoder, would make each of those packages unopenable.

## The harnesses that read it

- `tests/format_2025/test_format_compat.py`
- `src/flavor-go/pkg/psp/format_2025/format_compat_test.go`
- `src/flavor-rs/tests/format_compat.rs`

Unlike the `v1/` bundles, this is a plain JSON document rather than a built
package: the disagreement was in how the metadata is parsed, so parsing it is
the whole test. Nothing here needs a builder to reproduce.
