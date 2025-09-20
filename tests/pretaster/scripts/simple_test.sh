#!/bin/bash
# Simple shell script test

echo "🐚 Simple Shell Script Test"
echo "=========================="
echo ""
echo "📊 System Information:"
echo "  OS: $(uname -s)"
echo "  Arch: $(uname -m)"
echo "  Hostname: $(hostname)"
echo "  User: $USER"
echo "  Shell: $SHELL"
echo ""
echo "🌍 Environment:"
echo "  PATH: $PATH"
echo "  HOME: $HOME"
echo "  PWD: $PWD"
echo "  FLAVOR_WORKENV: ${FLAVOR_WORKENV:-not set}"
echo "  FLAVOR_COMMAND_NAME: ${FLAVOR_COMMAND_NAME:-not set}"
echo ""
echo "📝 Arguments:"
echo "  Count: $#"
if [ $# -gt 0 ]; then
    echo "  Values:"
    for arg in "$@"; do
        echo "    - $arg"
    done
else
    echo "  (no arguments provided)"
fi
echo ""
echo "✅ Shell script test completed successfully"
exit 0