#!/bin/bash

set -e

NEEDS_TEST_RESULT=$1
NEEDS_BUILD_WHEELS_RESULT=$2
NEEDS_BUILD_FLAVOR_RESULT=$3
NEEDS_TEST_FLAVOR_PSP_RESULT=$4

# Check if any test job failed
if [ "${NEEDS_TEST_RESULT}" != "success" ]; then
  echo "❌ Some tests failed"
  exit 1
fi

# Check if wheel build failed
if [ "${NEEDS_BUILD_WHEELS_RESULT}" != "success" ]; then
  echo "❌ Python wheel build failed"
  exit 1
fi

# Check if Flavor build failed
if [ "${NEEDS_BUILD_FLAVOR_RESULT}" != "success" ]; then
  echo "❌ Flavor build failed"
  exit 1
fi

# Check if PSP tests failed
if [ "${NEEDS_TEST_FLAVOR_PSP_RESULT}" != "success" ]; then
  echo "❌ Flavor PSP self-contained tests failed"
  exit 1
fi

echo "✅ All tests, wheels, and builds passed"
