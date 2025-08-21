#!/bin/bash
set -e

# Record timing information in build metadata
# Usage: .github/scripts/record-timing.sh <metadata_file> <event_name> <start|end> [value]

METADATA_FILE="$1"
EVENT_NAME="$2"
ACTION="$3"
VALUE="${4:-}"

if [ -z "$METADATA_FILE" ] || [ -z "$EVENT_NAME" ] || [ -z "$ACTION" ]; then
    echo "❌ Usage: $0 <metadata_file> <event_name> <start|end> [value]"
    exit 1
fi

# Ensure metadata file exists (create if needed for start action)
if [ ! -f "$METADATA_FILE" ]; then
    if [ "$ACTION" = "start" ]; then
        # Create initial metadata file if it doesn't exist
        mkdir -p "$(dirname "$METADATA_FILE")"
        echo '{"timings": {}}' > "$METADATA_FILE"
    else
        echo "❌ Metadata file not found: $METADATA_FILE"
        exit 1
    fi
fi

# Get current time in nanoseconds for precision
get_time_ns() {
    # Check if date supports nanoseconds (Linux)
    local test_ns=$(date +%s%N 2>/dev/null)
    if [ -n "$test_ns" ] && [[ "$test_ns" =~ ^[0-9]+$ ]]; then
        echo "$test_ns"
    else
        # Fallback for systems without nanosecond support (macOS)
        python3 -c "import time; print(int(time.time() * 1000000000))"
    fi
}

# Get ISO timestamp
get_timestamp() {
    date -u +"%Y-%m-%dT%H:%M:%S.%3NZ" 2>/dev/null || date -u +"%Y-%m-%dT%H:%M:%SZ"
}

if [ "$ACTION" = "start" ]; then
    # Record start time
    START_TIME=$(get_time_ns)
    START_TIMESTAMP=$(get_timestamp)
    
    # Update metadata with Python for proper JSON handling
    PYTHONIOENCODING=utf-8 python3 -c "
import json
import sys

with open('$METADATA_FILE', 'r') as f:
    data = json.load(f)

if 'timings' not in data:
    data['timings'] = {}

data['timings']['$EVENT_NAME'] = {
    'start_ns': $START_TIME,
    'start_timestamp': '$START_TIMESTAMP',
    'status': 'running'
}

with open('$METADATA_FILE', 'w') as f:
    json.dump(data, f, indent=2)
"
    echo "[TIMER] Started timing: $EVENT_NAME"
    
elif [ "$ACTION" = "end" ]; then
    # Record end time and calculate duration
    END_TIME=$(get_time_ns)
    END_TIMESTAMP=$(get_timestamp)
    
    # Update metadata with duration
    PYTHONIOENCODING=utf-8 python3 -c "
import json
import sys
import os

# Force UTF-8 encoding for Windows
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    os.environ['PYTHONIOENCODING'] = 'utf-8'

with open('$METADATA_FILE', 'r') as f:
    data = json.load(f)

if 'timings' not in data:
    data['timings'] = {}

if '$EVENT_NAME' in data['timings']:
    start_ns = data['timings']['$EVENT_NAME'].get('start_ns', $END_TIME)
    duration_ms = ($END_TIME - start_ns) / 1000000
    data['timings']['$EVENT_NAME']['end_ns'] = $END_TIME
    data['timings']['$EVENT_NAME']['end_timestamp'] = '$END_TIMESTAMP'
    data['timings']['$EVENT_NAME']['duration_ms'] = duration_ms
    data['timings']['$EVENT_NAME']['duration_seconds'] = duration_ms / 1000
    data['timings']['$EVENT_NAME']['status'] = 'completed'
else:
    # If no start time, just record the end
    data['timings']['$EVENT_NAME'] = {
        'end_ns': $END_TIME,
        'end_timestamp': '$END_TIMESTAMP',
        'status': 'completed',
        'duration_ms': 0
    }

# Add custom value if provided
if '$VALUE':
    data['timings']['$EVENT_NAME']['value'] = '$VALUE'

with open('$METADATA_FILE', 'w') as f:
    json.dump(data, f, indent=2)

# Output duration for GitHub Actions - use ASCII-safe characters
if '$EVENT_NAME' in data['timings'] and 'duration_seconds' in data['timings']['$EVENT_NAME']:
    print(f\"[TIMER] Completed {data['timings']['$EVENT_NAME']['duration_seconds']:.2f}s: $EVENT_NAME\")
"
    
elif [ "$ACTION" = "record" ]; then
    # Just record a value without timing
    PYTHONIOENCODING=utf-8 python3 -c "
import json

with open('$METADATA_FILE', 'r') as f:
    data = json.load(f)

if 'timings' not in data:
    data['timings'] = {}

if '$EVENT_NAME' not in data['timings']:
    data['timings']['$EVENT_NAME'] = {}

data['timings']['$EVENT_NAME']['value'] = '$VALUE'
data['timings']['$EVENT_NAME']['timestamp'] = '$(get_timestamp)'

with open('$METADATA_FILE', 'w') as f:
    json.dump(data, f, indent=2)
"
    echo "[RECORD] Recorded: $EVENT_NAME = $VALUE"
fi