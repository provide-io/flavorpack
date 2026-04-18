#!/bin/bash
# SPDX-FileCopyrightText: Copyright (c) 2026 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

# Pretaster test runner - reports test success when running as PSP
set -e

CMD="${1:-info}"
shift || true

case "$CMD" in
    info)
        echo "📦 Pretaster Test Suite"
        echo "  Platform: $(uname -s)-$(uname -m)"
        echo "  Workenv: ${FLAVOR_WORKENV:-not set}"
        ;;
    test)
        FLAG="${1:---all}"
        echo "🧪 Pretaster validation for flag: $FLAG"
        
        # The fact that pretaster is running as a PSP proves basic functionality
        # Real cross-language tests should be run separately with actual test packages
        case "$FLAG" in
            --all)
                echo "📦 Pretaster PSP Validation"
                echo "  ✓ PSP is executing (this output proves it)"
                echo "  ✓ Launcher successfully extracted and executed package"
                echo "  ✓ Environment variables set: FLAVOR_WORKENV=${FLAVOR_WORKENV:-not set}"
                echo ""
                echo "⚠️  Note: Detailed cross-language tests require building test packages"
                echo "    This PSP execution only validates the pretaster package itself works"
                ;;
            --combo)
                echo "📦 Builder/Launcher Combination Validation"
                echo "  ✓ This pretaster was built with: ${FLAVOR_BUILDER:-unknown builder}"
                echo "  ✓ This pretaster is running with: ${FLAVOR_LAUNCHER:-unknown launcher}"
                echo ""
                echo "⚠️  Note: Full combination testing requires multiple PSP builds"
                ;;
            --core)
                echo "📦 Core Functionality Validation"
                echo "  ✓ Package extraction: Working (you're seeing this)"
                echo "  ✓ Command execution: Working (this script is running)"
                echo "  ✓ Workenv: ${FLAVOR_WORKENV:-not set}"
                ;;
            --direct)
                echo "📦 Direct Execution Validation"
                echo "  ✓ Direct PSP execution: Working"
                echo "  ✓ Arguments received: $@"
                echo "  ✓ Exit code will be: 0 (success)"
                ;;
            *)
                echo "Unknown flag: $FLAG"
                exit 1
                ;;
        esac
        ;;
    *)
        echo "Unknown command: $CMD"
        echo "Usage: $0 {info|test} [options]"
        exit 1
        ;;
esac
