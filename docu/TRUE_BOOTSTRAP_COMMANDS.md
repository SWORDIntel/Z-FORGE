# True Incremental Bootstrap Commands
## Single Workspace Progressive Build

### 🎯 **Philosophy**
Build **ONE workspace** progressively, adding layers incrementally instead of creating separate ISOs each time.

---

## 📋 **Manual Layer-by-Layer Commands**

### **Setup**
```bash
mkdir -p logs bootstrap_results
export WORKSPACE="/tmp/zforge-bootstrap-workspace"
sudo rm -rf "$WORKSPACE" 2>/dev/null || true
```

### **Layer 1: Foundation (Base System)**
```bash
echo "=== Layer 1: Foundation Setup ==="
python3 -c "
import sys
sys.path.append('builder')
from core.builder import Builder

config = {
    'workspace_path': '$WORKSPACE',
    'debian_release': 'trixie',
    'enable_debug': True,
    'ram_build': True
}

builder = Builder(config)
builder.setup_workspace()
builder.run_debootstrap()
print('✅ Foundation layer complete')
" 2>&1 | tee logs/layer1-foundation-$(date +%Y%m%d_%H%M%S).log
```

### **Layer 2: ZFS Integration**
```bash
echo "=== Layer 2: ZFS Integration ==="
python3 -c "
import sys
sys.path.append('builder')
from modules.zfs_build import ZfsBuild
from pathlib import Path

workspace = Path('$WORKSPACE')
config = {'version': '2.3.3', 'build_from_source': True}

zfs_module = ZfsBuild(workspace, config)
result = zfs_module.execute()
print(f'✅ ZFS layer complete: {result}')
" 2>&1 | tee logs/layer2-zfs-$(date +%Y%m%d_%H%M%S).log
```

### **Layer 3: Kernel & Modules**
```bash
echo "=== Layer 3: Kernel & Modules ==="
python3 -c "
import sys
sys.path.append('builder')
from modules.kernel_acquisition import KernelAcquisition
from pathlib import Path

workspace = Path('$WORKSPACE')
config = {'kernel_version': '6.14.0-15-generic'}

kernel_module = KernelAcquisition(workspace, config)
result = kernel_module.execute()
print(f'✅ Kernel layer complete: {result}')
" 2>&1 | tee logs/layer3-kernel-$(date +%Y%m%d_%H%M%S).log
```

### **Layer 4: Proxmox Foundation**
```bash
echo "=== Layer 4: Proxmox Foundation ==="
python3 -c "
import sys
sys.path.append('builder')
from modules.proxmox_repo_setup import ProxmoxRepoSetup
from pathlib import Path

workspace = Path('$WORKSPACE')
config = {'pve_version': '9.0', 'debian_version': 'trixie'}

proxmox_repo = ProxmoxRepoSetup(workspace, config)
result = proxmox_repo.execute()
print(f'✅ Proxmox foundation complete: {result}')
" 2>&1 | tee logs/layer4-proxmox-foundation-$(date +%Y%m%d_%H%M%S).log
```

### **Layer 5: Proxmox Packages**
```bash
echo "=== Layer 5: Proxmox Packages ==="
python3 -c "
import sys
sys.path.append('builder')
from modules.proxmox_package_install import ProxmoxPackageInstall
from pathlib import Path

workspace = Path('$WORKSPACE')
config = {'pve_version': '9.0', 'debian_version': 'trixie'}

proxmox_packages = ProxmoxPackageInstall(workspace, config)
result = proxmox_packages.execute()
print(f'✅ Proxmox packages complete: {result}')
" 2>&1 | tee logs/layer5-proxmox-packages-$(date +%Y%m%d_%H%M%S).log
```

### **Layer 6: Proxmox Services**
```bash
echo "=== Layer 6: Proxmox Services ==="
python3 -c "
import sys
sys.path.append('builder')
from modules.proxmox_service_config import ProxmoxServiceConfig
from pathlib import Path

workspace = Path('$WORKSPACE')
config = {'pve_version': '9.0', 'debian_version': 'trixie'}

proxmox_services = ProxmoxServiceConfig(workspace, config)
result = proxmox_services.execute()
print(f'✅ Proxmox services complete: {result}')
" 2>&1 | tee logs/layer6-proxmox-services-$(date +%Y%m%d_%H%M%S).log
```

### **Layer 7: Networking**
```bash
echo "=== Layer 7: Networking ==="
python3 -c "
import sys
sys.path.append('builder')
from modules.proxmox_network_config import ProxmoxNetworkConfig
from pathlib import Path

workspace = Path('$WORKSPACE')
config = {'pve_version': '9.0', 'debian_version': 'trixie'}

proxmox_network = ProxmoxNetworkConfig(workspace, config)
result = proxmox_network.execute()
print(f'✅ Networking layer complete: {result}')
" 2>&1 | tee logs/layer7-networking-$(date +%Y%m%d_%H%M%S).log
```

### **Layer 8: Storage**
```bash
echo "=== Layer 8: Storage ==="
python3 -c "
import sys
sys.path.append('builder')
from modules.proxmox_storage_config import ProxmoxStorageConfig
from pathlib import Path

workspace = Path('$WORKSPACE')
config = {'pve_version': '9.0', 'debian_version': 'trixie'}

proxmox_storage = ProxmoxStorageConfig(workspace, config)
result = proxmox_storage.execute()
print(f'✅ Storage layer complete: {result}')
" 2>&1 | tee logs/layer8-storage-$(date +%Y%m%d_%H%M%S).log
```

### **Layer 9: Clustering**
```bash
echo "=== Layer 9: Clustering ==="
python3 -c "
import sys
sys.path.append('builder')
from modules.proxmox_cluster_setup import ProxmoxClusterSetup
from pathlib import Path

workspace = Path('$WORKSPACE')
config = {'pve_version': '9.0', 'debian_version': 'trixie'}

proxmox_cluster = ProxmoxClusterSetup(workspace, config)
result = proxmox_cluster.execute()
print(f'✅ Clustering layer complete: {result}')
" 2>&1 | tee logs/layer9-clustering-$(date +%Y%m%d_%H%M%S).log
```

### **Layer 10: Final ISO**
```bash
echo "=== Layer 10: Final ISO Generation ==="
python3 -c "
import sys
sys.path.append('builder')
from modules.iso_generation import IsoGeneration
from pathlib import Path

workspace = Path('$WORKSPACE')
config = {
    'output_iso_name': 'zforge-incremental-bootstrap.iso',
    'compression': 'xz'
}

iso_module = IsoGeneration(workspace, config)
result = iso_module.execute()
print(f'✅ Final ISO complete: {result}')
" 2>&1 | tee logs/layer10-final-iso-$(date +%Y%m%d_%H%M%S).log
```

---

## 🤖 **Automated Success Evaluator**

```bash
#!/bin/bash
# check_layer_success.sh
echo "=== Bootstrap Layer Success Analysis ==="
WORKSPACE="/tmp/zforge-bootstrap-workspace"

check_layer() {
    local layer=$1
    local description=$2
    local check_command=$3
    
    echo -n "Layer $layer ($description): "
    if eval "$check_command" >/dev/null 2>&1; then
        echo "✅ SUCCESS"
        echo "SUCCESS: Layer $layer - $description" > "bootstrap_results/layer${layer}_success.txt"
        return 0
    else
        echo "❌ FAILED"
        return 1
    fi
}

# Layer checks
check_layer 1 "Foundation" "[ -d '$WORKSPACE/chroot' ]"
check_layer 2 "ZFS" "[ -f '$WORKSPACE/chroot/usr/bin/zfs' ]"
check_layer 3 "Kernel" "[ -d '$WORKSPACE/chroot/lib/modules' ]"
check_layer 4 "Proxmox Foundation" "[ -f '$WORKSPACE/chroot/etc/apt/sources.list.d/pve-sources.list' ]"
check_layer 5 "Proxmox Packages" "[ -d '$WORKSPACE/chroot/usr/share/zforge' ]"
check_layer 6 "Proxmox Services" "[ -f '$WORKSPACE/chroot/etc/systemd/system/pvedaemon.service' ]"
check_layer 7 "Networking" "[ -f '$WORKSPACE/chroot/etc/network/interfaces' ]"
check_layer 8 "Storage" "[ -f '$WORKSPACE/chroot/etc/pve/storage.cfg' ]"
check_layer 9 "Clustering" "[ -f '$WORKSPACE/chroot/etc/corosync/corosync.conf' ]"
check_layer 10 "Final ISO" "[ -f 'zforge-incremental-bootstrap.iso' ]"

echo ""
echo "=== Workspace Analysis ==="
if [ -d "$WORKSPACE" ]; then
    echo "Workspace size: $(du -sh $WORKSPACE 2>/dev/null | cut -f1)"
    echo "Chroot status: $([ -d '$WORKSPACE/chroot' ] && echo 'EXISTS' || echo 'MISSING')"
    echo "Key files:"
    ls -la "$WORKSPACE/chroot/usr/bin/zfs" 2>/dev/null && echo "  ✅ ZFS binary found"
    ls -la "$WORKSPACE/chroot/etc/pve/" 2>/dev/null | head -3 && echo "  ✅ Proxmox config found"
else
    echo "❌ Workspace not found at $WORKSPACE"
fi

echo ""
echo "Success markers:"
ls -la bootstrap_results/ 2>/dev/null || echo "No success markers found"
```

---

## 🚀 **Quick Commands**

**Automated Incremental Bootstrap:**
```bash
./bootstrap_incremental.sh
```

**Manual with Success Evaluation:**
```bash
# Save the evaluator
cat > check_layer_success.sh << 'EOF'
[evaluator script content from above]
EOF
chmod +x check_layer_success.sh

# Run after each layer
./check_layer_success.sh
```

**Monitor Progress:**
```bash
watch -n 5 'du -sh /tmp/zforge-bootstrap-workspace 2>/dev/null || echo "Workspace not ready"; ls bootstrap_results/ 2>/dev/null | wc -l'
```

This approach builds **ONE complete system incrementally** rather than separate ISOs! 🎯