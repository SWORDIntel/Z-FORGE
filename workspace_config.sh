#!/bin/bash
# Z-FORGE Workspace Configuration

# Check if /tmp is noexec
if mount | grep " /tmp " | grep -q noexec; then
    echo "WARNING: /tmp is mounted with noexec"
    export ZFORGE_WORKSPACE="/var/lib/zforge_workspace"
else
    export ZFORGE_WORKSPACE="/tmp/zforge_workspace"
fi

echo "Using workspace: $ZFORGE_WORKSPACE"
