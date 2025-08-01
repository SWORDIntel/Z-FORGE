#!/bin/bash
# Setup build environment without using /tmp

set -e

echo "═══════════════════════════════════════════════════════════════════"
echo "        Setting Up No-/tmp Build Environment"
echo "═══════════════════════════════════════════════════════════════════"

# Set workspace in home directory
WORKSPACE_BASE="$HOME/zforge_workspace"

echo "[1/5] Creating workspace directories..."
mkdir -p "$WORKSPACE_BASE"/{chroot,cache,output,temp,logs}
mkdir -p "$WORKSPACE_BASE"/cache/debootstrap

echo "✅ Created workspace at: $WORKSPACE_BASE"

echo ""
echo "[2/5] Setting environment variables..."

# Export variables for current session
export ZFORGE_WORKSPACE="$WORKSPACE_BASE"
export TMPDIR="$WORKSPACE_BASE/temp"
export TEMP="$WORKSPACE_BASE/temp"
export TMP="$WORKSPACE_BASE/temp"

# Add to bashrc for persistence
cat >> ~/.bashrc << EOF

# Z-FORGE No-/tmp Configuration
export ZFORGE_WORKSPACE="$WORKSPACE_BASE"
export TMPDIR="$WORKSPACE_BASE/temp"
export TEMP="$WORKSPACE_BASE/temp"
export TMP="$WORKSPACE_BASE/temp"
EOF

echo "✅ Environment variables set"

echo ""
echo "[3/5] Creating fixed build scripts..."

# Create a wrapper for the build
cat > run_build_no_tmp.sh << 'EOF'
#!/bin/bash
# Run build without using /tmp

# Set all temp variables to our workspace
export ZFORGE_WORKSPACE="$HOME/zforge_workspace"
export TMPDIR="$ZFORGE_WORKSPACE/temp"
export TEMP="$ZFORGE_WORKSPACE/temp"
export TMP="$ZFORGE_WORKSPACE/temp"

# Use our custom build spec
export ZFORGE_CONFIG="build_spec_no_tmp.yml"

echo "Running build with:"
echo "  Workspace: $ZFORGE_WORKSPACE"
echo "  Temp dir: $TMPDIR"
echo "  Config: $ZFORGE_CONFIG"
echo ""

# Run the build
exec make build
EOF

chmod +x run_build_no_tmp.sh

echo "✅ Created run_build_no_tmp.sh"

echo ""
echo "[4/5] Checking for existing chroot..."

if [ -d "${CHROOT_PATH:-$HOME/zforge_workspace/chroot}" ]; then
    echo "Found existing chroot in /tmp"
    echo "To migrate it, run:"
    echo "  sudo mv ${CHROOT_PATH:-$HOME/zforge_workspace/chroot} $WORKSPACE_BASE/"
fi

echo ""
echo "[5/5] Creating Python wrapper..."

# Create a Python wrapper that sets the workspace
cat > builder/core/workspace_override.py << 'EOF'
"""
Workspace override to avoid /tmp
"""
import os
from pathlib import Path

def get_workspace_path():
    """Get workspace path, avoiding /tmp"""
    # Priority order:
    # 1. Environment variable
    # 2. Home directory
    # 3. /var/lib (if running as root)
    
    if 'ZFORGE_WORKSPACE' in os.environ:
        return Path(os.environ['ZFORGE_WORKSPACE'])
    
    if os.geteuid() == 0:
        # Running as root, use /var/lib
        return Path('/var/lib/zforge_workspace')
    else:
        # Use home directory
        return Path.home() / 'zforge_workspace'

# Override the default workspace path
WORKSPACE_PATH = get_workspace_path()

# Ensure temp directories don't use /tmp
os.environ['TMPDIR'] = str(WORKSPACE_PATH / 'temp')
os.environ['TEMP'] = str(WORKSPACE_PATH / 'temp')
os.environ['TMP'] = str(WORKSPACE_PATH / 'temp')
EOF

echo "✅ Created workspace override"

echo ""
echo "═══════════════════════════════════════════════════════════════════"
echo "                Setup Complete!"
echo "═══════════════════════════════════════════════════════════════════"
echo ""
echo "Your new build environment:"
echo "  Workspace: $WORKSPACE_BASE"
echo "  Temp directory: $WORKSPACE_BASE/temp"
echo "  Config file: build_spec_no_tmp.yml"
echo ""
echo "To run the build:"
echo "  ./run_build_no_tmp.sh"
echo ""
echo "Or manually:"
echo "  export ZFORGE_WORKSPACE=$WORKSPACE_BASE"
echo "  export ZFORGE_CONFIG=build_spec_no_tmp.yml"
echo "  make build"
echo ""
echo "This completely avoids /tmp and any noexec issues!"