#!/bin/bash
# z-forge/build-iso.sh - Complete ISO build script

set -e

echo "══════════════════════════════════════════════════════════════════"
echo "                Z-FORGE V3 ISO BUILD PROCESS"
echo "══════════════════════════════════════════════════════════════════"
echo ""

# Check root
if [ "$EUID" -ne 0 ]; then
    echo "[!] This script must be run as root"
    exit 1
fi

# Configuration
WORKSPACE="/tmp/zforge_workspace"
ISO_OUTPUT="$PWD/zforge-proxmox-v3.iso"
LOG_FILE="$PWD/zforge-build.log"

# Create workspace
echo "[*] Creating workspace at $WORKSPACE..."
mkdir -p "$WORKSPACE"

# Initialize log
echo "[*] Build started at $(date)" | tee "$LOG_FILE"

# Make sure builder directory is in path
export PYTHONPATH=$PWD:$PYTHONPATH

# Function to run builder module
run_module() {
    local module=$1
    echo "[*] Running module: $module" | tee -a "$LOG_FILE"
    # Use Python directly to run the module to avoid path issues
    python3 -c "
import sys
from builder.core.builder import ZForgeBuilder
builder = ZForgeBuilder('build_spec.yml')
result = builder.execute_module('$module')
if result.get('status') != 'success':
    print(f\"[!] Module $module failed: {result.get('error')}\")
    sys.exit(1)
" 2>&1 | tee -a "$LOG_FILE"

    if [ ${PIPESTATUS[0]} -ne 0 ]; then
        echo "[!] Module $module failed!" | tee -a "$LOG_FILE"
        exit 1
    fi
}

# Execute build pipeline
echo "[*] Starting build pipeline..." | tee -a "$LOG_FILE"

# Run each module in sequence
modules=(
    "WorkspaceSetup"
    "Debootstrap"
    "KernelAcquisition"
    "ZFSBuild"
    "ProxmoxIntegration"
    "LiveEnvironment"
    "CalamaresIntegration"
    "ISOGeneration"
)

for module in "${modules[@]}"; do
    run_module "$module"
done

# Final steps
echo "[*] Build completed successfully!" | tee -a "$LOG_FILE"
echo "[*] ISO location: $ISO_OUTPUT" | tee -a "$LOG_FILE"
echo "[*] ISO size: $(du -h "$ISO_OUTPUT" | cut -f1)" | tee -a "$LOG_FILE"

# Generate checksums
echo "[*] Generating checksums..." | tee -a "$LOG_FILE"
sha256sum "$ISO_OUTPUT" > "$ISO_OUTPUT.sha256"
md5sum "$ISO_OUTPUT" > "$ISO_OUTPUT.md5"

echo "" | tee -a "$LOG_FILE"
echo "══════════════════════════════════════════════════════════════════"
echo "                    BUILD COMPLETE"
echo "══════════════════════════════════════════════════════════════════"
echo "" | tee -a "$LOG_FILE"
echo "Next steps:" | tee -a "$LOG_FILE"
echo "1. Test ISO in virtual machine:" | tee -a "$LOG_FILE"
echo "   qemu-system-x86_64 -m 4G -cdrom $ISO_OUTPUT -enable-kvm" | tee -a "$LOG_FILE"
echo "" | tee -a "$LOG_FILE"
echo "2. Write to USB drive:" | tee -a "$LOG_FILE"
echo "   dd if=$ISO_OUTPUT of=/dev/sdX bs=4M status=progress" | tee -a "$LOG_FILE"
echo "" | tee -a "$LOG_FILE"
