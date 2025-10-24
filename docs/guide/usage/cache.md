# Cache Management

Manage FlavorPack's work environment cache.

## Coming Soon

This page is under development. In the meantime, see:

- **[Work Environments](../concepts/workenv.md)** - How caching works

## Quick Reference

```bash
# View cache location
flavor cache info

# Clean cache
flavor cache clean

# Verify cache integrity
flavor cache verify

# Clear specific package cache
flavor cache clean --package myapp.psp
```

## Cache Location

Default cache locations:
- **Linux/macOS**: `~/.cache/flavor/`
- **Windows**: `%LOCALAPPDATA%\flavor\cache\`

Override with: `FLAVOR_WORKENV=/custom/path`

## Topics to be Covered

- Cache structure
- Cache validation
- Cache cleanup strategies
- Troubleshooting cache issues
- Cache size management

---

**See also:** [Work Environments](../concepts/workenv.md) | [Environment Variables](environment.md)
