### Verifying Installation

After installation, verify everything works correctly:

**1. Check Python Version:**
```bash
python --version  # Should show 3.11+
```

**2. Verify Package Installation:**
```bash
# Check package can be imported
python -c "import {{PACKAGE_NAME}}; print('✅ Package installed')"

# Check version (if available)
python -c "import {{PACKAGE_NAME}}; print({{PACKAGE_NAME}}.__version__)"
```

**3. Verify Environment:**
```bash
# Check which Python is being used
which python

# Verify it's in your virtual environment
python -c "import sys; print(sys.prefix)"
```

**4. Run Smoke Tests:**
```bash
# Run quick sanity tests
uv run pytest tests/ -k "test_smoke or test_basic" --tb=short

# Or run a small subset
uv run pytest tests/ -x --maxfail=3
```
