# The execution block contract

`omits-primary-slot.json` is one metadata document that all three
implementations must read the same way. It exists because they did not.

Two disagreements, both found in #36:

**`primary_slot` was required by Rust and optional everywhere else.** Go leaves
a missing field at its zero value and Python's executor reads it with
`.get("primary_slot", 0)`, so a package without the field is ordinary to both.
Rust rejected the whole document — `missing field primary_slot` — so the same
bytes were a package to two implementations and unopenable to the third. The
field is only ever read to resolve `{primary}` and to print a debug line, and
every construction site in the Rust tree sets it to 0. It is optional, and Rust
now defaults it.

**The environment was written under two different keys.** Rust and Python both
read and write `env`. Go declared the field as `environment`. So Go silently
dropped an environment block written by either of the others — a package setting
`MODE=prod` ran with no `MODE` under the Go launcher, with nothing said — and
re-emitted anything it did read under a key the other two ignore. Go now uses
`env`, and still accepts `environment` when reading, so packages it built before
keep working.

This document therefore omits `primary_slot` and sets a non-empty `env`. Every
implementation must parse it, resolve `primary_slot` to 0, and see `MODE=prod`.

The harnesses that read it:

- `tests/format_2025/test_format_compat.py`
- `src/flavor-go/pkg/psp/format_2025/format_compat_test.go`
- `src/flavor-rs/tests/format_compat.rs`

Unlike the `v1/` bundles, this is a plain JSON document rather than a built
package: the disagreement was in how the metadata was parsed, so parsing it is
the whole test. Nothing here needs a builder to reproduce.
