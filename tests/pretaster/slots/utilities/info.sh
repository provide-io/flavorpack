#!/bin/bash
echo "ℹ️ System Info Utility"
echo "  Kernel: $(uname -r)"
echo "  Load: $(uptime | awk -F'load average:' '{print $2}')"
echo "  Memory: $(free -h 2>/dev/null | grep Mem | awk '{print $3 " / " $2}' || echo 'N/A on macOS')"