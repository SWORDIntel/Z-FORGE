#!/bin/bash
# Unmount filesystems and move workspace safely

set -e

echo "═══════════════════════════════════════════════════════════════════"
echo "        Unmounting and Moving Workspace"
echo "═══════════════════════════════════════════════════════════════════"

# Find all mounted filesystems in workspace
echo "[1/4] Finding mounted filesystems..."
MOUNTS=$(mount | grep "${ZFORGE_WORKSPACE:-/home/john/zforge_workspace}" | awk '{print $3}' | sort -r)

if [ -n "$MOUNTS" ]; then
    echo "Found mounted filesystems:"
    echo "$MOUNTS"
    echo ""
    echo "[2/4] Unmounting filesystems..."
    echo "Run these commands as root:"
    echo ""
    for mount_point in $MOUNTS; do
        echo "sudo umount -l $mount_point"
    done
    echo ""
    echo "Or unmount all at once:"
    echo "sudo umount -l ${ZFORGE_WORKSPACE:-/home/john/zforge_workspace}/*/proc"
    echo "sudo umount -l ${ZFORGE_WORKSPACE:-/home/john/zforge_workspace}/*/sys" 
    echo "sudo umount -l ${ZFORGE_WORKSPACE:-/home/john/zforge_workspace}/*/dev/pts"
    echo "sudo umount -l ${ZFORGE_WORKSPACE:-/home/john/zforge_workspace}/*/dev"
else
    echo "No mounted filesystems found in workspace"
fi

echo ""
echo "[3/4] After unmounting, move the workspace:"
echo "export ZFORGE_WORKSPACE=\$HOME/zforge_workspace"
echo "sudo mv ${ZFORGE_WORKSPACE:-/home/john/zforge_workspace} \$HOME/"

echo ""
echo "[4/4] Then run the build:"
echo "make build"

echo ""
echo "Complete command sequence:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
cat << 'EOF'
# Unmount all
sudo umount -l ${ZFORGE_WORKSPACE:-/home/john/zforge_workspace}/*/proc || true
sudo umount -l ${ZFORGE_WORKSPACE:-/home/john/zforge_workspace}/*/sys || true
sudo umount -l ${ZFORGE_WORKSPACE:-/home/john/zforge_workspace}/*/dev/pts || true
sudo umount -l ${ZFORGE_WORKSPACE:-/home/john/zforge_workspace}/*/dev || true

# Set new workspace
export ZFORGE_WORKSPACE=$HOME/zforge_workspace

# Move workspace
sudo mv ${ZFORGE_WORKSPACE:-/home/john/zforge_workspace} $HOME/

# Run build
make build
EOF
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"