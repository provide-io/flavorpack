#!/bin/bash
# Test logging at different levels

echo "📊 Logging Level Test Script"
echo "============================"
echo ""

# Function to log at different levels
log_message() {
    local level=$1
    local message=$2
    local timestamp=$(date +"%Y-%m-%d %H:%M:%S")
    
    case $level in
        ERROR)
            echo "❌ [$timestamp] ERROR: $message" >&2
            ;;
        WARN)
            echo "⚠️  [$timestamp] WARN: $message" >&2
            ;;
        INFO)
            echo "ℹ️  [$timestamp] INFO: $message"
            ;;
        DEBUG)
            echo "🔍 [$timestamp] DEBUG: $message"
            ;;
        TRACE)
            echo "🔬 [$timestamp] TRACE: $message"
            ;;
        *)
            echo "❓ [$timestamp] UNKNOWN: $message"
            ;;
    esac
}

# Check what log level is set
determine_log_level() {
    # Check various environment variables
    if [ -n "$FLAVOR_LOG_LEVEL" ]; then
        echo "Log level from FLAVOR_LOG_LEVEL: $FLAVOR_LOG_LEVEL"
        LOG_LEVEL=$FLAVOR_LOG_LEVEL
    elif [ -n "$FLAVOR_LAUNCHER_LOG_LEVEL" ]; then
        echo "Log level from FLAVOR_LAUNCHER_LOG_LEVEL: $FLAVOR_LAUNCHER_LOG_LEVEL"
        LOG_LEVEL=$FLAVOR_LAUNCHER_LOG_LEVEL
    elif [ -n "$LOG_LEVEL" ]; then
        echo "Log level from LOG_LEVEL: $LOG_LEVEL"
    else
        echo "No log level set, defaulting to INFO"
        LOG_LEVEL="info"
    fi
}

# Determine active log level
determine_log_level
echo ""

# Log at each level
log_message ERROR "This is an error message (always shown)"
log_message WARN "This is a warning message"
log_message INFO "This is an info message"
log_message DEBUG "This is a debug message"
log_message TRACE "This is a trace message"

echo ""
echo "📋 Log Level Hierarchy:"
echo "  ERROR - Always shown"
echo "  WARN  - Shown at: warn, info, debug, trace"
echo "  INFO  - Shown at: info, debug, trace"
echo "  DEBUG - Shown at: debug, trace"
echo "  TRACE - Shown at: trace only"

echo ""
echo "✅ Logging test completed"
exit 0