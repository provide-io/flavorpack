#!/bin/sh
# Stand-in for a real launcher binary in the format-compatibility fixtures.
#
# Verification never executes the launcher -- it only measures its length and
# covers its bytes -- so the fixtures embed this 300-odd byte script instead of
# a multi-megabyte binary. That keeps each committed fixture around 10-20 KB.
#
# The builders probe the launcher for a version string before embedding it.
if [ "$1" = "--version" ] || [ "$1" = "version" ]; then
    echo "flavor-fixture-stub 1.0"
fi
exit 0
