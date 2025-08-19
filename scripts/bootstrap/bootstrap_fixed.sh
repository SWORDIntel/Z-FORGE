#!/bin/bash
# Z-FORGE Fixed Bootstrap Script
# Uses proper module imports and validates each step

set -e
WORKSPACE="/tmp/zforge-bootstrap-workspace"
LOGDIR="logs"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

echo "🚀 Z-FORGE Fixed Bootstrap - $TIMESTAMP"
echo "========================================="

mkdir -p "$LOGDIR" bootstrap_results

# Clean workspace
echo "Cleaning previous workspace..."
sudo rm -rf "$WORKSPACE" 2>/dev/null || true

# Use the actual build system with proper specs
echo "=== Phase 1: Minimal Working Build ==="
echo "Using build_spec_working.yml for foundation..."
if sudo python3 build.py \
    --spec build_specs/build_spec_working.yml \
    --workspace "$WORKSPACE" \
    --verbose --debug 2>&1 | tee "$LOGDIR/bootstrap-phase1-$TIMESTAMP.log"; then
    echo "✅ Phase 1 SUCCESS: Foundation created"
    echo "SUCCESS: Phase 1 - Foundation" > bootstrap_results/phase1_success.txt
    
    # Check actual workspace state
    echo "Workspace validation:"
    if [ -d "$WORKSPACE/chroot/bin" ]; then
        echo "  ✅ Chroot bin directory exists"
    else
        echo "  ❌ Chroot bin directory missing"
        exit 1
    fi
    
    if [ -f "$WORKSPACE/chroot/etc/debian_version" ]; then
        echo "  ✅ Debian system installed: $(cat $WORKSPACE/chroot/etc/debian_version)"
    else
        echo "  ❌ Debian system not properly installed"
        exit 1
    fi
else
    echo "❌ Phase 1 FAILED"
    exit 1
fi

echo ""
echo "🎉 Foundation bootstrap complete!"
echo "Workspace ready at: $WORKSPACE"
echo "Next: Run additional phases or use the workspace for development"