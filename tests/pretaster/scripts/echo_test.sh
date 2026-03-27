#!/bin/bash
# Echo test script (Windows-compatible bash version of echo_test.py)
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

if [ $# -gt 0 ]; then
    echo "$@"
else
    echo "Echo test ready"
fi
