# Release Process

Process for releasing new versions of FlavorPack.

## Coming Soon

Complete release documentation under development.

## Quick Reference

### Version Bumping

```bash
# Update version in pyproject.toml
# Update CHANGELOG.md
# Create git tag
git tag v0.4.0
git push --tags
```

### Release Checklist

- [ ] All tests passing
- [ ] Documentation updated
- [ ] CHANGELOG.md updated
- [ ] Version bumped
- [ ] Helpers built for all platforms
- [ ] Wheels built
- [ ] Git tag created
- [ ] GitHub release created
- [ ] PyPI upload

## Topics to be Covered

- Semantic versioning
- Changelog management
- Building releases
- Publishing to PyPI
- GitHub releases
- Release automation

---

**See also:** [CI/CD](ci-cd.md) | [Contributing](contributing.md)
