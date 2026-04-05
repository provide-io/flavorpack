#!/bin/sh
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
# POSIX sh combo test script — no host dependencies beyond tastesh.

CMD="${1:-}"
shift || true

case "$CMD" in
    info)
        echo "  Package: pretaster-combination"
        echo "  Version: 1.0.0"
        echo "  Shell: $BASH"
        echo "  Workenv: ${FLAVOR_WORKENV:-Not set}"
        exit 0
        ;;
    env)
        env | sort | head -10
        echo "  ... ($(env | wc -l) total)"
        exit 0
        ;;
    argv)
        echo "📝 Arguments received:"
        i=0
        for arg in "$@"; do
            echo "  [$i]: $arg"
            i=$((i+1))
        done
        exit 0
        ;;
    echo)
        echo "$@"
        exit 0
        ;;
    file)
        if [ "${1:-}" = "workenv-test" ]; then
            echo "Test content" > "${TEMP:-/tmp}/workenv-test.txt"
            exit 0
        fi
        echo "❌ Unknown file command"
        exit 1
        ;;
    exit)
        code="${1:-0}"
        echo "🚪 Exiting with code $code"
        exit "$code"
        ;;
    --help|-h)
        echo "Usage: combo_test.sh <command> [args...]"
        echo "Commands: info, env, argv, echo, file, exit"
        exit 0
        ;;
    "")
        echo "Usage: combo_test.sh <command> [args...]"
        exit 1
        ;;
    *)
        echo "❌ Unknown command: $CMD"
        exit 1
        ;;
esac
