#!/bin/bash

set -e

NEEDS_TEST_TASTER_RESULT=$1
NEEDS_COMPREHENSIVE_TEST_RESULT=$2

# Check if any test job failed
if [ "${NEEDS_TEST_TASTER_RESULT}" != "success" ] || [ "${NEEDS_COMPREHENSIVE_TEST_RESULT}" != "success" ]; then
  echo "❌ Some taster tests failed"
  exit 1
fi
echo "✅ All taster tests passed"
