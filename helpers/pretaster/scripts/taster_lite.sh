#!/bin/bash
# Taster-lite: Simple shell implementations of core taster commands

set -e

COMMAND="${1:-help}"
shift || true

case "$COMMAND" in
    help|--help)
        echo "🍷 Pretaster - Shell implementation of core taster commands"
        echo ""
        echo "Commands:"
        echo "  info        Show package and system information"
        echo "  env         Display environment variables"
        echo "  argv        Show command-line arguments"
        echo "  exit        Exit with specific code and message"
        echo "  file        Test file operations in workenv"
        echo "  echo        Echo text with formatting"
        echo "  signals     Test signal handling"
        echo ""
        echo "Usage: taster_lite.sh <command> [args...]"
        ;;
        
    info)
        echo "📦 Package Information"
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        echo "  Script: $(basename "$0")"
        echo "  Workenv: ${FLAVOR_WORKENV:-not set}"
        echo "  Command: ${FLAVOR_COMMAND_NAME:-not set}"
        echo ""
        echo "🖥️  System Information"
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        echo "  OS: $(uname -s)"
        echo "  Arch: $(uname -m)"
        echo "  Kernel: $(uname -r)"
        echo "  Hostname: $(hostname)"
        echo "  User: ${USER:-unknown}"
        echo "  Shell: ${SHELL:-unknown}"
        echo "  PWD: $(pwd)"
        ;;
        
    env)
        echo "🌍 Environment Variables"
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        echo ""
        echo "Flavor Variables:"
        env | grep ^FLAVOR_ | sort | sed 's/^/  /'
        echo ""
        echo "Path Variables:"
        env | grep -E '^(PATH|HOME|USER|SHELL|PWD)=' | sort | sed 's/^/  /'
        echo ""
        echo "Total environment variables: $(env | wc -l)"
        ;;
        
    argv)
        echo "📝 Command Line Arguments"
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        echo "  Program: $0"
        echo "  Argument count: $#"
        if [ $# -gt 0 ]; then
            echo ""
            echo "Arguments:"
            i=1
            for arg in "$@"; do
                echo "  [$i]: '$arg'"
                i=$((i + 1))
            done
        else
            echo "  (no arguments provided)"
        fi
        ;;
        
    exit)
        CODE="${1:-0}"
        MESSAGE="${2:-}"
        echo "🚪 Exit Command"
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        echo "  Exit code: $CODE"
        if [ -n "$MESSAGE" ]; then
            echo "  Message: $MESSAGE"
        fi
        exit "$CODE"
        ;;
        
    file)
        OPERATION="${1:-test}"
        FILENAME="${2:-test.txt}"
        WORKENV="${FLAVOR_WORKENV:-/tmp/taster-lite-workenv}"
        
        echo "📁 File Operations"
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        echo "  Workenv: $WORKENV"
        echo "  Operation: $OPERATION"
        echo "  File: $FILENAME"
        echo ""
        
        case "$OPERATION" in
            workenv-test)
                # Test workenv persistence
                mkdir -p "$WORKENV"
                TEST_FILE="$WORKENV/$FILENAME"
                if [ -f "$TEST_FILE" ]; then
                    echo "  ✅ File exists from previous run"
                    echo "  Content: $(cat "$TEST_FILE")"
                else
                    echo "  📝 Creating new file"
                    echo "Created at $(date)" > "$TEST_FILE"
                    echo "  Content: $(cat "$TEST_FILE")"
                fi
                ;;
            write)
                mkdir -p "$WORKENV"
                echo "${3:-Test content}" > "$WORKENV/$FILENAME"
                echo "  ✅ Wrote to $FILENAME"
                ;;
            read)
                if [ -f "$WORKENV/$FILENAME" ]; then
                    echo "  Content of $FILENAME:"
                    cat "$WORKENV/$FILENAME" | sed 's/^/    /'
                else
                    echo "  ❌ File not found: $FILENAME"
                fi
                ;;
            *)
                echo "  ❌ Unknown operation: $OPERATION"
                exit 1
                ;;
        esac
        ;;
        
    echo)
        echo "📢 Echo Command"
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        if [ $# -gt 0 ]; then
            echo "  $*"
        else
            echo "  (nothing to echo)"
        fi
        ;;
        
    signals)
        SLEEP_TIME="${1:-5}"
        echo "⚡ Signal Handling Test"
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        echo "  PID: $$"
        echo "  Sleep time: ${SLEEP_TIME}s"
        echo ""
        
        # Set up signal handlers
        trap 'echo "  🛑 Received SIGINT (Ctrl+C)"; exit 130' INT
        trap 'echo "  🔄 Received SIGTERM"; exit 143' TERM
        trap 'echo "  ⏸️  Received SIGTSTP (Ctrl+Z) - ignoring"' TSTP
        
        echo "  Sleeping for ${SLEEP_TIME} seconds..."
        echo "  Press Ctrl+C to interrupt, Ctrl+Z to test TSTP"
        sleep "$SLEEP_TIME"
        echo "  ✅ Sleep completed successfully"
        ;;
        
    *)
        echo "❌ Unknown command: $COMMAND"
        echo "Run 'taster_lite.sh help' for available commands"
        exit 1
        ;;
esac