#!/bin/bash

set -e

IMAGE=$1
INSTALL_COMMAND=$2

echo "Running pretaster tests on $IMAGE"

docker run --rm \
  -v $PWD:/workspace \
  -w /workspace \
  ${IMAGE} sh -c "
  # Install Python
  ${INSTALL_COMMAND}
  
  # Install pretaster
  cd tests/pretaster
  pip3 install --break-system-packages . || pip3 install .
  
  # Run tests
  echo 'Running combination tests...'
  ./tests/combination-tests.sh
"
