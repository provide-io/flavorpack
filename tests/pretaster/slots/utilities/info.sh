#!/usr/bin/env bash
# SPDX-FileCopyrightText: Copyright (c) 2026 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

echo "ℹ️ System Info Utility"
echo "  Kernel: $(uname -r)"
echo "  Load: $(uptime | awk -F'load average:' '{print $2}')"
echo "  Memory: $(free -h 2>/dev/null | grep Mem | awk '{print $3 " / " $2}' || echo 'N/A on macOS')"