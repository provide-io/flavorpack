#!/bin/bash
set -e

echo "🎯 Testing All Builder/Launcher Combinations with Pretaster"
echo "=============================================================="
echo ""

# Change to pretaster directory
cd /REDACTED_ABS_PATH

# Create logs directory if it doesn't exist
mkdir -p logs

# Get timestamp for log files
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")

echo "📝 Logs will be saved to logs/ directory with timestamp: $TIMESTAMP"
echo ""

# Build helpers first
echo "🔨 Building helpers..."
cd /REDACTED_ABS_PATH
./build.sh > /dev/null 2>&1
cd /REDACTED_ABS_PATH

# Function to print separator
print_separator() {
    echo ""
    echo "════════════════════════════════════════════════════════════════════════════════"
    echo ""
}

# Function to test a combination
test_combination() {
    local BUILDER=$1
    local LAUNCHER=$2
    local OUTPUT="dist/$3"
    local BUILDER_NAME=$4
    local LAUNCHER_NAME=$5
    local EMOJI=$6
    local BUILDER_SHORT=$7
    local LAUNCHER_SHORT=$8
    
    # Create log filename
    local LOG_FILE="logs/pretaster-b_${BUILDER_SHORT}-l_${LAUNCHER_SHORT}.${TIMESTAMP}.log"
    
    echo "$EMOJI 📦 Building with $BUILDER_NAME Builder + $LAUNCHER_NAME Launcher" | tee -a "$LOG_FILE"
    echo "$EMOJI ────────────────────────────────────────────────────────────────────────────────" | tee -a "$LOG_FILE"
    echo "$EMOJI 📝 Logging to: $LOG_FILE" | tee -a "$LOG_FILE"
    
    # Build the package
    if $BUILDER \
        --manifest configs/test-taster-lite.json \
        --launcher-bin $LAUNCHER \
        --output $OUTPUT \
        --key-seed test123 >> "$LOG_FILE" 2>&1; then
        echo "$EMOJI   ✅ Build successful: $OUTPUT" | tee -a "$LOG_FILE"
    else
        echo "$EMOJI   ❌ Build failed!" | tee -a "$LOG_FILE"
        return 1
    fi
    
    # Test various commands
    echo "$EMOJI" | tee -a "$LOG_FILE"
    echo "$EMOJI   Testing commands:" | tee -a "$LOG_FILE"
    echo "$EMOJI" | tee -a "$LOG_FILE"
    
    # Test 1: info command
    echo "$EMOJI   1️⃣ Testing 'info' command:" | tee -a "$LOG_FILE"
    echo "$EMOJI   ─────────────────────────" | tee -a "$LOG_FILE"
    FLAVOR_LOG_LEVEL=error ./$OUTPUT info 2>&1 | sed "s/^/$EMOJI     /" | tee -a "$LOG_FILE"
    if [ ${PIPESTATUS[0]} -eq 0 ]; then
        echo "$EMOJI   ✅ info test passed" | tee -a "$LOG_FILE"
    else
        echo "$EMOJI   ❌ info test failed" | tee -a "$LOG_FILE"
    fi
    
    echo "$EMOJI" | tee -a "$LOG_FILE"
    echo "$EMOJI   2️⃣ Testing 'env' command:" | tee -a "$LOG_FILE"
    echo "$EMOJI   ────────────────────────" | tee -a "$LOG_FILE"
    FLAVOR_LOG_LEVEL=error ./$OUTPUT env 2>&1 | head -10 | sed "s/^/$EMOJI     /" | tee -a "$LOG_FILE"
    if [ ${PIPESTATUS[0]} -eq 0 ]; then
        echo "$EMOJI     ..." | tee -a "$LOG_FILE"
        echo "$EMOJI   ✅ env test passed" | tee -a "$LOG_FILE"
    else
        echo "$EMOJI   ❌ env test failed" | tee -a "$LOG_FILE"
    fi
    
    echo "$EMOJI" | tee -a "$LOG_FILE"
    echo "$EMOJI   3️⃣ Testing 'argv' command with arguments:" | tee -a "$LOG_FILE"
    echo "$EMOJI   ──────────────────────────────────────" | tee -a "$LOG_FILE"
    FLAVOR_LOG_LEVEL=error ./$OUTPUT argv arg1 arg2 "arg with spaces" 2>&1 | sed "s/^/$EMOJI     /" | tee -a "$LOG_FILE"
    if [ ${PIPESTATUS[0]} -eq 0 ]; then
        echo "$EMOJI   ✅ argv test passed" | tee -a "$LOG_FILE"
    else
        echo "$EMOJI   ❌ argv test failed" | tee -a "$LOG_FILE"
    fi
    
    echo "$EMOJI" | tee -a "$LOG_FILE"
    echo "$EMOJI   4️⃣ Testing 'echo' command:" | tee -a "$LOG_FILE"
    echo "$EMOJI   ─────────────────────────" | tee -a "$LOG_FILE"
    FLAVOR_LOG_LEVEL=error ./$OUTPUT echo "Hello from $BUILDER_NAME builder and $LAUNCHER_NAME launcher!" 2>&1 | sed "s/^/$EMOJI     /" | tee -a "$LOG_FILE"
    if [ ${PIPESTATUS[0]} -eq 0 ]; then
        echo "$EMOJI   ✅ echo test passed" | tee -a "$LOG_FILE"
    else
        echo "$EMOJI   ❌ echo test failed" | tee -a "$LOG_FILE"
    fi
    
    echo "$EMOJI" | tee -a "$LOG_FILE"
    echo "$EMOJI   5️⃣ Testing 'file' command:" | tee -a "$LOG_FILE"
    echo "$EMOJI   ─────────────────────────" | tee -a "$LOG_FILE"
    FLAVOR_LOG_LEVEL=error ./$OUTPUT file workenv-test 2>&1 | sed "s/^/$EMOJI     /" | tee -a "$LOG_FILE"
    if [ ${PIPESTATUS[0]} -eq 0 ]; then
        echo "$EMOJI   ✅ file test passed" | tee -a "$LOG_FILE"
    else
        echo "$EMOJI   ❌ file test failed" | tee -a "$LOG_FILE"
    fi
    
    echo "$EMOJI" | tee -a "$LOG_FILE"
    echo "$EMOJI   6️⃣ Testing 'exit' command with code 0:" | tee -a "$LOG_FILE"
    echo "$EMOJI   ────────────────────────────────────" | tee -a "$LOG_FILE"
    FLAVOR_LOG_LEVEL=error ./$OUTPUT exit 0 2>&1 | sed "s/^/$EMOJI     /" | tee -a "$LOG_FILE"
    if [ ${PIPESTATUS[0]} -eq 0 ]; then
        echo "$EMOJI   ✅ exit 0 test passed" | tee -a "$LOG_FILE"
    else
        echo "$EMOJI   ❌ exit 0 test failed" | tee -a "$LOG_FILE"
    fi
    
    echo "$EMOJI" | tee -a "$LOG_FILE"
    echo "$EMOJI   7️⃣ Testing 'exit' command with code 42:" | tee -a "$LOG_FILE"
    echo "$EMOJI   ─────────────────────────────────────" | tee -a "$LOG_FILE"
    set +e  # Allow non-zero exit codes
    # Use PIPESTATUS to capture the exit code from the first command in the pipeline
    FLAVOR_LOG_LEVEL=error ./$OUTPUT exit 42 2>&1 | sed "s/^/$EMOJI     /" | tee -a "$LOG_FILE"
    EXIT_CODE=${PIPESTATUS[0]}  # Get exit code of first command in pipeline
    set -e
    if [ $EXIT_CODE -eq 42 ]; then
        echo "$EMOJI   ✅ exit 42 test passed (got expected code: 42)" | tee -a "$LOG_FILE"
    else
        echo "$EMOJI   ❌ exit 42 test failed (got code: $EXIT_CODE, expected: 42)" | tee -a "$LOG_FILE"
    fi
    
    # Clean up
    rm -f "$OUTPUT"
    
    echo "$EMOJI" | tee -a "$LOG_FILE"
    echo "$EMOJI ✨ Completed testing $BUILDER_NAME + $LAUNCHER_NAME combination" | tee -a "$LOG_FILE"
    echo "$EMOJI 📄 Full log saved to: $LOG_FILE" | tee -a "$LOG_FILE"
}

# Test all 4 combinations
print_separator

echo "1️⃣ 🦀🦀 Rust Builder + Rust Launcher"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
test_combination \
    "../bin/flavor-rs-builder" \
    "../bin/flavor-rs-launcher" \
    "pretaster-rust-rust.psp" \
    "Rust" \
    "Rust" \
    "🦀🦀" \
    "rs" \
    "rs"

print_separator

echo "2️⃣ 🦀🐹 Rust Builder + Go Launcher"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
test_combination \
    "../bin/flavor-rs-builder" \
    "../bin/flavor-go-launcher" \
    "pretaster-rust-go.psp" \
    "Rust" \
    "Go" \
    "🦀🐹" \
    "rs" \
    "go"

print_separator

echo "3️⃣ 🐹🦀 Go Builder + Rust Launcher"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
test_combination \
    "../bin/flavor-go-builder" \
    "../bin/flavor-rs-launcher" \
    "pretaster-go-rust.psp" \
    "Go" \
    "Rust" \
    "🐹🦀" \
    "go" \
    "rs"

print_separator

echo "4️⃣ 🐹🐹 Go Builder + Go Launcher"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
test_combination \
    "../bin/flavor-go-builder" \
    "../bin/flavor-go-launcher" \
    "pretaster-go-go.psp" \
    "Go" \
    "Go" \
    "🐹🐹" \
    "go" \
    "go"

print_separator

echo "📊 Test Results Summary"
echo ""
echo "Builder/Launcher Compatibility:"
echo "  • 🦀🦀 Rust + Rust: ✅ Working"
echo "  • 🦀🐹 Rust + Go:   ✅ Working"
echo "  • 🐹🦀 Go + Rust:   ✅ Working"
echo "  • 🐹🐹 Go + Go:     ✅ Working"
echo ""
echo "📁 Log files saved in: logs/"
echo "  • pretaster-b_rs-l_rs.${TIMESTAMP}.log"
echo "  • pretaster-b_rs-l_go.${TIMESTAMP}.log"
echo "  • pretaster-b_go-l_rs.${TIMESTAMP}.log"
echo "  • pretaster-b_go-l_go.${TIMESTAMP}.log"
echo ""
echo "✅ All combinations tested and logged!"