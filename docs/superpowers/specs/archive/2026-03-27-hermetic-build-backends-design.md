# Hermetic Build Backends

**Date:** 2026-03-27
**Status:** Approved

## Context

`--no-build-isolation` was added to all `pip wheel` calls to prevent a Windows GHA SSL crash. When pip runs with build isolation (the default), it spawns a subprocess to install `[build-system].requires` from PyPI; that subprocess reinitializes `truststore`, which crashes with `ssl.SSLError: [SSL] unknown error` on Windows GHA runners. Disabling build isolation eliminates the subprocess entirely.

This works because setuptools and wheel are pre-installed in the flavorpack workenv. However, those tools are only version-constrained (`>=68.0.0`), not pinned — so builds are not reproducible across environments, and `_ensure_no_isolation_build_backend()` still hits PyPI on a cache miss.

**Goal:** Full hermeticity for build backends — network isolation (no PyPI calls during builds) and reproducibility (same versions always) — without containers or OS-specific features.

## Design

### 1. Declaration — `pyproject.toml`

Add a `build-backends` dependency group with exact pinned versions:

```toml
[dependency-groups]
build-backends = [
  "setuptools==75.8.2",
  "wheel==0.45.1",
]
```

Run `uv lock` once to pin both packages with `sha256:` hashes in `uv.lock`. This is the single source of truth — same file, same tooling, same update path as all other deps. Version bumps are a one-line edit + `uv lock` re-run.

### 2. Slot Assembly

During flavorpack's own build (CI), export and download the pinned build backend wheels into the workenv slot's `wheels/` directory:

```bash
uv export --frozen --only-group build-backends --no-emit-project -o build-backends-requirements.txt
pip download --require-hashes -r build-backends-requirements.txt -d <slot_wheels_dir>
```

No new slot structure needed. The wheels land in the same `wheels/` directory as runtime wheels and travel with the workenv to every machine that installs flavorpack.

### 3. `_ensure_no_isolation_build_backend()` — assertion only

The function changes from "install if missing (via network)" to "verify or fail hard":

```python
def _ensure_no_isolation_build_backend():
    """Assert that pinned build backends are present. Never installs."""
    for pkg, expected in [("setuptools", "75.8.2"), ("wheel", "0.45.1")]:
        installed = importlib.metadata.version(pkg)
        if installed != expected:
            raise RuntimeError(
                f"Build backend mismatch: {pkg}=={installed} present, "
                f"expected {pkg}=={expected}. Rebuild the workenv slot."
            )
```

Hard fail with a clear message pointing at the right fix. No network call, no silent install, no version drift.

### 4. `--no-build-isolation` — unchanged

The flag stays as-is in `pypapip_manager.py`. Its justification is now stronger: build tools are guaranteed present at known versions, not just "probably there."

## Files to Modify

| File | Change |
|------|--------|
| `pyproject.toml` | Add `[dependency-groups] build-backends` |
| `uv.lock` | Regenerated via `uv lock` (not hand-edited) |
| Workenv slot builder (`environment_builder.py` or `slot_builder.py`) | Add build-backends export + `pip download --require-hashes` step |
| `src/flavor/packaging/python/wheel_builder.py` | Replace `_ensure_no_isolation_build_backend()` with version assertion |

## Verification

1. Run `uv lock` — confirm setuptools and wheel appear with `sha256:` hashes in `uv.lock`
2. Build the workenv slot — confirm setuptools and wheel `.whl` files are present in `wheels/`
3. Exercise `_ensure_no_isolation_build_backend()` in a clean env — should pass silently
4. Install a mismatched setuptools version — should raise `RuntimeError` with the mismatch message
5. Run `pytest tests/packaging/python/`
6. CI build on Windows — confirm no SSL crash and no PyPI network calls during wheel building
