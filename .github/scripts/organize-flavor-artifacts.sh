#!/bin/bash

set -e

mkdir -p flavor-psp
# Move all PSP and EXE files from subdirectories to flavor-psp
find flavor-artifacts -type f \( -name "*.psp" -o -name "*.exe" \) -exec mv {} flavor-psp/ \;
ls -la flavor-psp/
