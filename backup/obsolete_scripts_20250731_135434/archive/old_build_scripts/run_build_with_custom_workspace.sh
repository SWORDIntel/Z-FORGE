#!/bin/bash
# Run build with custom workspace to avoid noexec check

set -e

echo "═══════════════════════════════════════════════════════════════════"
echo "        Running Build with Custom Workspace"
echo "═══════════════════════════════════════════════════════════════════"

# Option 1: Use home directory
WORKSPACE_HOME="$HOME/zforge_workspace"

# Option 2: Use /var/lib
WORKSPACE_VAR="/var/lib/zforge_workspace"

echo ""
echo "Choose workspace location:"
echo "1. Home directory: $WORKSPACE_HOME"
echo "2. /var/lib (requires sudo): $WORKSPACE_VAR"
echo ""
read -p "Enter choice [1-2]: " choice

case $choice in
    1)
        echo "Using home directory workspace..."
        export ZFORGE_WORKSPACE="$WORKSPACE_HOME"
        
        # Move existing workspace if needed
        if [ -d "/tmp/zforge_workspace/chroot" ] && [ ! -d "$WORKSPACE_HOME/chroot" ]; then
            echo "Moving existing workspace..."
            sudo mv /tmp/zforge_workspace "$WORKSPACE_HOME"
        fi
        
        mkdir -p "$WORKSPACE_HOME"
        echo "Workspace set to: $ZFORGE_WORKSPACE"
        echo ""
        echo "Running build..."
        make build
        ;;
        
    2)
        echo "Using /var/lib workspace..."
        export ZFORGE_WORKSPACE="$WORKSPACE_VAR"
        
        # Create and move
        sudo mkdir -p "$WORKSPACE_VAR"
        
        if [ -d "/tmp/zforge_workspace/chroot" ] && [ ! -d "$WORKSPACE_VAR/chroot" ]; then
            echo "Moving existing workspace..."
            sudo mv /tmp/zforge_workspace/* "$WORKSPACE_VAR/" 2>/dev/null || true
        fi
        
        echo "Workspace set to: $ZFORGE_WORKSPACE"
        echo ""
        echo "Running build..."
        make build
        ;;
        
    *)
        echo "Invalid choice"
        exit 1
        ;;
esac