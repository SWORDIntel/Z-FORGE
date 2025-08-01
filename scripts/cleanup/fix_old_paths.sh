#!/bin/bash
# Quick fix for old workspace paths

set -e

echo "Fixing old workspace paths in scripts..."

# Get original user home
ORIGINAL_USER=${SUDO_USER:-$(logname 2>/dev/null || echo $USER)}
ORIGINAL_HOME=$(eval echo "~$ORIGINAL_USER" 2>/dev/null || echo "$HOME")

# Find and fix all scripts with old paths
find scripts/ -name "*.sh" -type f | while read -r script; do
    if grep -q "${ZFORGE_WORKSPACE:-/home/john/zforge_workspace}" "$script"; then
        echo "Updating: $script"
        
        # Backup
        cp "$script" "$script.bak"
        
        # Replace paths
        sed -i "s|${CHROOT_PATH:-/home/john/zforge_workspace/chroot}|\${CHROOT_PATH:-$ORIGINAL_HOME/zforge_workspace/chroot}|g" "$script"
        sed -i "s|${ZFORGE_WORKSPACE:-/home/john/zforge_workspace}|\${ZFORGE_WORKSPACE:-$ORIGINAL_HOME/zforge_workspace}|g" "$script"
        
        # Show changes
        if ! diff -q "$script.bak" "$script" >/dev/null; then
            echo "  ✓ Updated paths"
        else
            rm "$script.bak"
        fi
    fi
done

echo "Done fixing paths!"