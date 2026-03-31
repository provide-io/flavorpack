#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
"""Trivial payload for policy enforcement test.

This script should never execute if platform policy is working correctly,
because the package declares platforms: ["mars_amd64"] which no real host matches.
"""

import sys

print("policy test: this should never print if platform policy works")
sys.exit(0)

# 🌶️📦🔚
