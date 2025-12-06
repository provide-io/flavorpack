#!/bin/bash

set -e

source quality-env/bin/activate
echo "## 📝 Documentation Quality" >> $GITHUB_STEP_SUMMARY
echo "" >> $GITHUB_STEP_SUMMARY

# Pydocstyle - Docstring conventions
echo "### Docstring Conventions" >> $GITHUB_STEP_SUMMARY
pydocstyle src/ --count 2>&1 | tee pydocstyle.log || true

if grep -q "violations" pydocstyle.log; then
  VIOLATIONS=$(grep "violations" pydocstyle.log)
  echo "⚠️ $VIOLATIONS" >> $GITHUB_STEP_SUMMARY
  echo '```' >> $GITHUB_STEP_SUMMARY
  head -30 pydocstyle.log >> $GITHUB_STEP_SUMMARY
  echo '```' >> $GITHUB_STEP_SUMMARY
else
  echo "✅ Documentation conventions followed" >> $GITHUB_STEP_SUMMARY
fi

# Check for missing docstrings
echo "### Missing Docstrings" >> $GITHUB_STEP_SUMMARY
python -c "
import ast
import os
from pathlib import Path

missing = []
for py_file in Path('src').rglob('*.py'):
    with open(py_file) as f:
        try:
            tree = ast.parse(f.read())
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
                    if not ast.get_docstring(node):
                        missing.append(f'{py_file}:{node.lineno} - {node.name}')
        except: pass

if missing:
    print(f'Found {len(missing)} functions/classes without docstrings')
    for m in missing[:20]:
        print(f'  - {m}')
else:
    print('All functions and classes have docstrings')
" | tee docstring-check.log
echo '```' >> $GITHUB_STEP_SUMMARY
cat docstring-check.log >> $GITHUB_STEP_SUMMARY
echo '```' >> $GITHUB_STEP_SUMMARY
