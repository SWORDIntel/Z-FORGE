#!/bin/bash
# Z-FORGE True Incremental Bootstrap
# Builds one workspace progressively, adding layers incrementally

set -e
WORKSPACE="/tmp/zforge-bootstrap-workspace"
LOGDIR="logs"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

echo "🚀 Z-FORGE True Incremental Bootstrap - $TIMESTAMP"
echo "Building single workspace with progressive module addition"
echo "========================================================="

mkdir -p "$LOGDIR" bootstrap_results

# Clean any existing workspace
echo "Cleaning previous workspace..."
sudo rm -rf "$WORKSPACE" 2>/dev/null || true

echo "=== Bootstrap Phase 1: Foundation Setup ===" | tee "$LOGDIR/bootstrap-incremental-$TIMESTAMP.log"
echo "Creating base workspace at: $WORKSPACE" | tee -a "$LOGDIR/bootstrap-incremental-$TIMESTAMP.log"

# Phase 1: Create minimal base system
echo "Phase 1: Minimal base system (debootstrap + basic setup)"
python3 -c "
import sys
sys.path.append('builder')
from core.builder import Builder
from pathlib import Path

config = {
    'workspace_path': '$WORKSPACE',
    'debian_release': 'trixie',
    'enable_debug': True,
    'ram_build': True
}

builder = Builder(config)
print('Creating base workspace...')
builder.setup_workspace()
print('Running debootstrap...')
builder.run_debootstrap()
print('Phase 1 complete: Base system ready')
" 2>&1 | tee -a "$LOGDIR/bootstrap-incremental-$TIMESTAMP.log"

if [ $? -eq 0 ]; then
    echo "✅ Phase 1 SUCCESS: Base system created" | tee -a "$LOGDIR/bootstrap-incremental-$TIMESTAMP.log"
    echo "SUCCESS: Phase 1 - Base System" > "bootstrap_results/phase1_foundation.txt"
else
    echo "❌ Phase 1 FAILED: Base system creation"
    exit 1
fi

echo "=== Bootstrap Phase 2: ZFS Layer ===" | tee -a "$LOGDIR/bootstrap-incremental-$TIMESTAMP.log"
echo "Phase 2: Adding ZFS support to existing workspace"
python3 -c "
import sys
sys.path.append('builder')
from modules.zfs_build import ZfsBuild
from pathlib import Path

workspace = Path('$WORKSPACE')
config = {'version': '2.3.3', 'build_from_source': True}

zfs_module = ZfsBuild(workspace, config)
print('Building ZFS on existing system...')
result = zfs_module.execute()
print(f'ZFS build result: {result}')
print('Phase 2 complete: ZFS added')
" 2>&1 | tee -a "$LOGDIR/bootstrap-incremental-$TIMESTAMP.log"

if [ $? -eq 0 ]; then
    echo "✅ Phase 2 SUCCESS: ZFS layer added" | tee -a "$LOGDIR/bootstrap-incremental-$TIMESTAMP.log"
    echo "SUCCESS: Phase 2 - ZFS Layer" > "bootstrap_results/phase2_zfs.txt"
else
    echo "❌ Phase 2 FAILED: ZFS layer addition"
    exit 1
fi

echo "=== Bootstrap Phase 3: Kernel Layer ===" | tee -a "$LOGDIR/bootstrap-incremental-$TIMESTAMP.log"
echo "Phase 3: Adding kernel and modules to existing workspace"
python3 -c "
import sys
sys.path.append('builder')
from modules.kernel_acquisition import KernelAcquisition
from pathlib import Path

workspace = Path('$WORKSPACE')
config = {'kernel_version': '6.14.0-15-generic'}

kernel_module = KernelAcquisition(workspace, config)
print('Adding kernel to existing system...')
result = kernel_module.execute()
print(f'Kernel acquisition result: {result}')
print('Phase 3 complete: Kernel added')
" 2>&1 | tee -a "$LOGDIR/bootstrap-incremental-$TIMESTAMP.log"

if [ $? -eq 0 ]; then
    echo "✅ Phase 3 SUCCESS: Kernel layer added" | tee -a "$LOGDIR/bootstrap-incremental-$TIMESTAMP.log"
    echo "SUCCESS: Phase 3 - Kernel Layer" > "bootstrap_results/phase3_kernel.txt"
else
    echo "❌ Phase 3 FAILED: Kernel layer addition"
    exit 1
fi

echo "=== Bootstrap Phase 4: Proxmox Foundation ===" | tee -a "$LOGDIR/bootstrap-incremental-$TIMESTAMP.log"
echo "Phase 4: Adding Proxmox base to existing workspace"
python3 -c "
import sys
sys.path.append('builder')
from modules.proxmox_repo_setup import ProxmoxRepoSetup
from pathlib import Path

workspace = Path('$WORKSPACE')
config = {'pve_version': '9.0', 'debian_version': 'trixie'}

proxmox_repo = ProxmoxRepoSetup(workspace, config)
print('Setting up Proxmox repositories...')
result = proxmox_repo.execute()
print(f'Proxmox repo setup result: {result}')
print('Phase 4 complete: Proxmox foundation ready')
" 2>&1 | tee -a "$LOGDIR/bootstrap-incremental-$TIMESTAMP.log"

if [ $? -eq 0 ]; then
    echo "✅ Phase 4 SUCCESS: Proxmox foundation added" | tee -a "$LOGDIR/bootstrap-incremental-$TIMESTAMP.log"
    echo "SUCCESS: Phase 4 - Proxmox Foundation" > "bootstrap_results/phase4_proxmox_base.txt"
else
    echo "❌ Phase 4 FAILED: Proxmox foundation"
    exit 1
fi

echo "=== Bootstrap Phase 5: Proxmox Services ===" | tee -a "$LOGDIR/bootstrap-incremental-$TIMESTAMP.log"
echo "Phase 5: Adding Proxmox services to existing workspace"
python3 -c "
import sys
sys.path.append('builder')
from modules.proxmox_service_config import ProxmoxServiceConfig
from pathlib import Path

workspace = Path('$WORKSPACE')
config = {'pve_version': '9.0', 'debian_version': 'trixie'}

proxmox_services = ProxmoxServiceConfig(workspace, config)
print('Configuring Proxmox services...')
result = proxmox_services.execute()
print(f'Proxmox services result: {result}')
print('Phase 5 complete: Proxmox services configured')
" 2>&1 | tee -a "$LOGDIR/bootstrap-incremental-$TIMESTAMP.log"

if [ $? -eq 0 ]; then
    echo "✅ Phase 5 SUCCESS: Proxmox services added" | tee -a "$LOGDIR/bootstrap-incremental-$TIMESTAMP.log"
    echo "SUCCESS: Phase 5 - Proxmox Services" > "bootstrap_results/phase5_proxmox_services.txt"
else
    echo "❌ Phase 5 FAILED: Proxmox services"
    exit 1
fi

echo "=== Bootstrap Phase 6: Final ISO Generation ===" | tee -a "$LOGDIR/bootstrap-incremental-$TIMESTAMP.log"
echo "Phase 6: Generating final ISO from complete workspace"
python3 -c "
import sys
sys.path.append('builder')
from modules.iso_generation import IsoGeneration
from pathlib import Path

workspace = Path('$WORKSPACE')
config = {
    'output_iso_name': 'zforge-bootstrap-complete.iso',
    'compression': 'xz'
}

iso_module = IsoGeneration(workspace, config)
print('Generating final ISO...')
result = iso_module.execute()
print(f'ISO generation result: {result}')
print('Phase 6 complete: Bootstrap ISO ready')
" 2>&1 | tee -a "$LOGDIR/bootstrap-incremental-$TIMESTAMP.log"

if [ $? -eq 0 ]; then
    echo "✅ Phase 6 SUCCESS: Final ISO generated" | tee -a "$LOGDIR/bootstrap-incremental-$TIMESTAMP.log"
    echo "SUCCESS: Phase 6 - Final ISO" > "bootstrap_results/phase6_final_iso.txt"
else
    echo "❌ Phase 6 FAILED: ISO generation"
    exit 1
fi

echo "" | tee -a "$LOGDIR/bootstrap-incremental-$TIMESTAMP.log"
echo "🎉 INCREMENTAL BOOTSTRAP COMPLETE!" | tee -a "$LOGDIR/bootstrap-incremental-$TIMESTAMP.log"
echo "Final workspace: $WORKSPACE" | tee -a "$LOGDIR/bootstrap-incremental-$TIMESTAMP.log"
echo "Final ISO: $(find . -name 'zforge-bootstrap-complete.iso' 2>/dev/null || echo 'ISO location pending')" | tee -a "$LOGDIR/bootstrap-incremental-$TIMESTAMP.log"
echo "Build log: $LOGDIR/bootstrap-incremental-$TIMESTAMP.log"

# Workspace size analysis
echo "=== Final Workspace Analysis ===" | tee -a "$LOGDIR/bootstrap-incremental-$TIMESTAMP.log"
du -sh "$WORKSPACE" 2>/dev/null | tee -a "$LOGDIR/bootstrap-incremental-$TIMESTAMP.log" || echo "Workspace size analysis failed"
ls -la bootstrap_results/ | tee -a "$LOGDIR/bootstrap-incremental-$TIMESTAMP.log"