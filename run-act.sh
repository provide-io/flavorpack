#!/bin/bash
# Run act with proper configuration for Colima

# Set Docker host to the correct socket
export DOCKER_HOST="unix:///REDACTED_ABS_PATH"

# Run act without trying to mount the Docker socket
# The --container-daemon-socket flag with "-" disables socket mounting
exec act \
  --container-daemon-socket - \
  --container-architecture linux/amd64 \
  --bind \
  --use-gitignore \
  "$@"