#!/bin/bash
# Fix workspace noexec issue by using alternative location or remounting

set -e

echo "═══════════════════════════════════════════════════════════════════"
echo "        Fixing Workspace noexec Issue"
echo "═══════════════════════════════════════════════════════════════════"

# Check current /tmp mount options
echo "[1/4] Checking /tmp mount status..."
mount | grep " /tmp " || echo "/tmp not separately mounted"
echo ""

# Option 1: Try to remount /tmp without noexec (requires root)
if [ "$EUID" -eq 0 ]; then
    echo "[2/4] Attempting to remount /tmp without noexec..."
    if mount -o remount,exec /tmp 2>/dev/null; then
        echo "✅ Successfully remounted /tmp with exec"
        mount | grep " /tmp "
    else
        echo "❌ Could not remount /tmp"
    fi
else
    echo "[2/4] Not running as root, skipping /tmp remount"
fi

echo ""
echo "[3/4] Creating alternative workspace location..."

# Option 2: Use alternative location
ALT_WORKSPACE="/var/lib/zforge_workspace"
if [ "$EUID" -eq 0 ]; then
    mkdir -p "$ALT_WORKSPACE"
    chmod 755 "$ALT_WORKSPACE"
    echo "✅ Created alternative workspace at: $ALT_WORKSPACE"
    
    # If old workspace exists, move it
    if [ -d "/tmp/zforge_workspace" ]; then
        echo "Moving existing workspace..."
        if [ ! -d "$ALT_WORKSPACE/chroot" ]; then
            mv /tmp/zforge_workspace/* "$ALT_WORKSPACE/" 2>/dev/null || true
        fi
    fi
else
    echo "Alternative workspace: $ALT_WORKSPACE (requires sudo to create)"
fi

echo ""
echo "[4/4] Updating build configuration..."

# Create workspace configuration
cat > workspace_config.sh << 'EOF'
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
EOF

chmod +x workspace_config.sh

echo ""
echo "═══════════════════════════════════════════════════════════════════"
echo "                    Solutions Available"
echo "═══════════════════════════════════════════════════════════════════"
echo ""
echo "Option 1: Remount /tmp with exec (temporary fix):"
echo "  sudo mount -o remount,exec /tmp"
echo "  make build"
echo ""
echo "Option 2: Use alternative workspace (permanent fix):"
echo "  export ZFORGE_WORKSPACE=/var/lib/zforge_workspace"
echo "  sudo mkdir -p \$ZFORGE_WORKSPACE"
echo "  make build"
echo ""
echo "Option 3: Use home directory workspace:"
echo "  export ZFORGE_WORKSPACE=~/zforge_workspace"
echo "  make build"
echo ""
echo "Option 4: Update Makefile to use different location"
echo ""
echo "Recommended: Option 2 (alternative workspace)"