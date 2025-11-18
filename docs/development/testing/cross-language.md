# Cross-Language Tests

Test compatibility across Python, Go, and Rust implementations.

## Coming Soon

Complete cross-language testing guide under development.

## Quick Start

```bash
# Run pretaster tests
make validate-pspf

# Test all combinations
make validate-pspf-combo

# Specific combination
cd tests/pretaster
make test BUILDER=go LAUNCHER=rust
```

## Test Matrix

| Builder | Launcher | Status |
|---------|----------|--------|
| Go | Go | ✅ Tested |
| Go | Rust | ✅ Tested |
| Rust | Go | ✅ Tested |
| Rust | Rust | ✅ Tested |

## Topics to be Covered

- Pretaster test suite
- Format compatibility testing
- Cross-language scenarios
- Test infrastructure
- Adding new tests

---

**See also:** [Testing Guide](index/) | [Pretaster README
