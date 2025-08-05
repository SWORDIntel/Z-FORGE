#!/bin/bash
# Ultrathink chroot wrapper for shell scripts
# This replaces 'chroot' commands with the ultrathink solution

ULTRATHINK_SOLUTION="$(dirname "$0")/../../ultrathink_chroot_solution.py"

if [ "$1" = "chroot" ]; then
    shift  # Remove 'chroot' command
    CHROOT_PATH="$1"
    shift  # Remove chroot path
    
    # Use ultrathink solution
    exec python3 "$ULTRATHINK_SOLUTION" "$CHROOT_PATH" -- "$@"
else
    # Direct usage
    exec python3 "$ULTRATHINK_SOLUTION" "$@"
fi
