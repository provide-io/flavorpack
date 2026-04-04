#!/bin/sh
# Policy enforcement test payload.
# This script should NEVER execute if platform policy is working correctly,
# because the package declares platforms: ["mars_amd64"].
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

echo "policy test: this should never print if platform policy works"
exit 0
