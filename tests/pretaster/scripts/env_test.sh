#!/usr/bin/env bash
# Environment test script (Windows-compatible bash version of env_test.py)
# Prints environment variables that were passed through
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

echo "Environment test"
echo "PRETASTER_MODE=${PRETASTER_MODE:-unset}"
echo "PATH is set: ${PATH:+yes}"
