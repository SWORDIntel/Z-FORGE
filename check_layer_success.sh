#!/bin/bash
# Z-FORGE Layer Success Evaluator
# Checks incremental bootstrap progress automatically

echo "=== Z-FORGE Bootstrap Layer Success Analysis ==="
WORKSPACE="/tmp/zforge-bootstrap-workspace"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

mkdir -p bootstrap_results

check_layer() {
    local layer=$1
    local description=$2
    local check_command=$3
    
    echo -n "Layer $layer ($description): "
    if eval "$check_command" >/dev/null 2>&1; then
        echo "✅ SUCCESS"
        echo "SUCCESS: Layer $layer - $description - $(date)" > "bootstrap_results/layer${layer}_success.txt"
        return 0
    else
        echo "❌ FAILED"
        return 1
    fi
}

echo "Checking bootstrap layers in workspace: $WORKSPACE"
echo "Analysis timestamp: $TIMESTAMP"
echo ""

# Progressive layer validation
total_layers=10
successful_layers=0

# Layer 1: Foundation (Base System)
if check_layer 1 "Foundation" "[ -d '$WORKSPACE/chroot' ] && [ -f '$WORKSPACE/chroot/bin/bash' ]"; then
    ((successful_layers++))
fi

# Layer 2: ZFS Integration  
if check_layer 2 "ZFS" "[ -f '$WORKSPACE/chroot/usr/bin/zfs' ] || [ -f '$WORKSPACE/chroot/sbin/zfs' ]"; then
    ((successful_layers++))
fi

# Layer 3: Kernel & Modules
if check_layer 3 "Kernel" "[ -d '$WORKSPACE/chroot/lib/modules' ] && [ -n \"\$(ls -A '$WORKSPACE/chroot/lib/modules' 2>/dev/null)\" ]"; then
    ((successful_layers++))
fi

# Layer 4: Proxmox Foundation
if check_layer 4 "Proxmox Foundation" "[ -f '$WORKSPACE/chroot/etc/apt/sources.list.d/pve-sources.list' ] || [ -d '$WORKSPACE/chroot/etc/pve' ]"; then
    ((successful_layers++))
fi

# Layer 5: Proxmox Packages
if check_layer 5 "Proxmox Packages" "[ -d '$WORKSPACE/chroot/usr/share/zforge' ] || [ -f '$WORKSPACE/chroot/usr/bin/qm' ]"; then
    ((successful_layers++))
fi

# Layer 6: Proxmox Services
if check_layer 6 "Proxmox Services" "[ -f '$WORKSPACE/chroot/etc/systemd/system/pvedaemon.service' ] || [ -f '$WORKSPACE/chroot/etc/systemd/system/pveproxy.service' ]"; then
    ((successful_layers++))
fi

# Layer 7: Networking
if check_layer 7 "Networking" "[ -f '$WORKSPACE/chroot/etc/network/interfaces' ] && grep -q 'vmbr' '$WORKSPACE/chroot/etc/network/interfaces' 2>/dev/null"; then
    ((successful_layers++))
fi

# Layer 8: Storage
if check_layer 8 "Storage" "[ -f '$WORKSPACE/chroot/etc/pve/storage.cfg' ] || [ -d '$WORKSPACE/chroot/var/lib/vz' ]"; then
    ((successful_layers++))
fi

# Layer 9: Clustering
if check_layer 9 "Clustering" "[ -f '$WORKSPACE/chroot/etc/corosync/corosync.conf' ] || [ -d '$WORKSPACE/chroot/etc/pve/ha' ]"; then
    ((successful_layers++))
fi

# Layer 10: Final ISO
if check_layer 10 "Final ISO" "[ -f 'zforge-incremental-bootstrap.iso' ] || [ -f '*.iso' ]"; then
    ((successful_layers++))
fi

echo ""
echo "=== Summary ==="
echo "Successful layers: $successful_layers/$total_layers"
completion_percentage=$((successful_layers * 100 / total_layers))
echo "Completion: $completion_percentage%"

if [ $successful_layers -eq $total_layers ]; then
    echo "🎉 BOOTSTRAP COMPLETE! All layers successful."
else
    echo "⚠️  Bootstrap in progress. Next layer: $((successful_layers + 1))"
fi

echo ""
echo "=== Workspace Analysis ==="
if [ -d "$WORKSPACE" ]; then
    workspace_size=$(du -sh "$WORKSPACE" 2>/dev/null | cut -f1)
    echo "Workspace size: $workspace_size"
    echo "Chroot status: $([ -d '$WORKSPACE/chroot' ] && echo 'EXISTS' || echo 'MISSING')"
    
    echo ""
    echo "Key system components:"
    [ -f "$WORKSPACE/chroot/usr/bin/zfs" ] && echo "  ✅ ZFS binary found" || echo "  ❌ ZFS binary missing"
    [ -d "$WORKSPACE/chroot/etc/pve" ] && echo "  ✅ Proxmox config found" || echo "  ❌ Proxmox config missing"
    [ -f "$WORKSPACE/chroot/etc/systemd/system/pvedaemon.service" ] && echo "  ✅ Proxmox services found" || echo "  ❌ Proxmox services missing"
    [ -d "$WORKSPACE/chroot/lib/modules" ] && echo "  ✅ Kernel modules found" || echo "  ❌ Kernel modules missing"
    
    echo ""
    echo "Chroot size breakdown:"
    du -sh "$WORKSPACE/chroot"/{usr,lib,etc,var} 2>/dev/null | sort -hr | head -5
else
    echo "❌ Workspace not found at $WORKSPACE"
fi

echo ""
echo "=== Success Markers ==="
if [ -d "bootstrap_results" ] && [ -n "$(ls -A bootstrap_results/ 2>/dev/null)" ]; then
    echo "Found $(ls bootstrap_results/layer*_success.txt 2>/dev/null | wc -l) success markers:"
    ls -la bootstrap_results/layer*_success.txt 2>/dev/null | sort
else
    echo "No success markers found"
fi

echo ""
echo "=== Next Steps ==="
if [ $successful_layers -lt $total_layers ]; then
    next_layer=$((successful_layers + 1))
    case $next_layer in
        1) echo "Run Layer 1: Foundation setup (debootstrap)" ;;
        2) echo "Run Layer 2: ZFS integration" ;;
        3) echo "Run Layer 3: Kernel & modules" ;;
        4) echo "Run Layer 4: Proxmox foundation" ;;
        5) echo "Run Layer 5: Proxmox packages" ;;
        6) echo "Run Layer 6: Proxmox services" ;;
        7) echo "Run Layer 7: Networking configuration" ;;
        8) echo "Run Layer 8: Storage configuration" ;;
        9) echo "Run Layer 9: Clustering setup" ;;
        10) echo "Run Layer 10: Final ISO generation" ;;
    esac
else
    echo "🚀 Ready for production! Bootstrap complete."
fi

# Save analysis report
cat > "bootstrap_results/analysis_$TIMESTAMP.txt" << EOF
Bootstrap Analysis Report
=========================
Timestamp: $TIMESTAMP
Successful Layers: $successful_layers/$total_layers
Completion: $completion_percentage%
Workspace: $WORKSPACE
Workspace Size: $(du -sh "$WORKSPACE" 2>/dev/null | cut -f1 || echo "N/A")
Status: $([ $successful_layers -eq $total_layers ] && echo "COMPLETE" || echo "IN_PROGRESS")
EOF

echo ""
echo "Analysis saved to: bootstrap_results/analysis_$TIMESTAMP.txt"