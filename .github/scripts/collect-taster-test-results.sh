#!/bin/bash

set -e

PLATFORM=$1
RUNNER=$2
JOB_STATUS=$3
TASTER_PATH=$4
HELPER_VERSION=$5

mkdir -p test-results

# Create test report
cat > test-results/taster-${PLATFORM}.json << EOF
{
  "platform": "${PLATFORM}",
  "runner": "${RUNNER}",
  "status": "${JOB_STATUS}",
  "taster_path": "${TASTER_PATH}",
  "timestamp": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")",
  "helper_version": "${HELPER_VERSION}"
}
EOF
