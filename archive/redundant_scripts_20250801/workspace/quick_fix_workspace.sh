#!/bin/bash
# Quick fix for workspace issue

echo "Quick fixes for workspace issue:"
echo ""

# Option 1: Set environment variable
echo "1. Setting ZFORGE_WORKSPACE to home directory..."
export ZFORGE_WORKSPACE="$HOME/zforge_workspace"
echo "export ZFORGE_WORKSPACE=$HOME/zforge_workspace" >> ~/.bashrc
mkdir -p "$ZFORGE_WORKSPACE"
echo "✅ Created workspace at: $ZFORGE_WORKSPACE"

# Option 2: Check if we can move existing workspace
if [ -d "${CHROOT_PATH:-/home/john/zforge_workspace/chroot}" ]; then
    echo ""
    echo "2. Moving existing chroot to new location..."
    echo "Run these commands:"
    echo "  sudo mv ${ZFORGE_WORKSPACE:-/home/john/zforge_workspace} $HOME/"
    echo "  export ZFORGE_WORKSPACE=$HOME/zforge_workspace"
fi

echo ""
echo "3. Quick test - try running make with new workspace:"
echo "  export ZFORGE_WORKSPACE=$HOME/zforge_workspace"
echo "  make build"
echo ""
echo "Or if you have sudo:"
echo "  sudo mount -o remount,exec /tmp"
echo "  make build"