#!/bin/bash

set -e

STATUS="${NEEDS_TEST_CORE_DISTROS_RESULT}"
COLOR=$([ "$STATUS" = "success" ] && echo "good" || echo "danger")

curl -X POST ${SLACK_WEBHOOK_URL} \
  -H 'Content-Type: application/json' \
  -d "{
    \"attachments\": [{
      \"color\": \"$COLOR\",
      \"title\": \"Daily Compatibility Check\",
      \"text\": \"Status: $STATUS\",
      \"fields\": [
        {\"title\": \"Core Distros\", \"value\": \"${NEEDS_TEST_CORE_DISTROS_RESULT}\", \"short\": true},
        {\"title\": \"ARM64\", \"value\": \"${NEEDS_TEST_ARM64_RESULT}\", \"short\": true}
      ]
    }]
  }"

