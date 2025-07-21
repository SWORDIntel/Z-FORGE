#!/usr/bin/env bash
# Z-FORGE V3 — ISO build script
# Automates creation of a Z-FORGE V3 Proxmox/ZFS-based installer ISO.
#───────────────────────────────────────────────────────────────────

set -euo pipefail

# ── Initial Environment Check ────────────────────────────────────
SCRIPT_DIR_ABS="$(cd "$(dirname "${BASH_SOURCE[0]}")" &>/dev/null && pwd)"
# shellcheck source=scripts/check_build_env.sh
if ! "$SCRIPT_DIR_ABS/scripts/check_build_env.sh"; then
    echo "[!] Build environment check failed. Please resolve the issues above and try again."
    exit 1
fi
# Proceed only if checks pass

echo "════════════════════════════════════════════════════════════════"
echo "                Z-FORGE V3  ISO  BUILD PROCESS"
echo "════════════════════════════════════════════════════════════════"
echo

# ── Root check ───────────────────────────────────────────────────
if [[ $EUID -ne 0 ]]; then
    echo "[!] This script must be run as root."
    exit 1
fi

# ── Paths & logging ──────────────────────────────────────────────
WORKSPACE="/tmp/zforge_workspace"
ISO_OUTPUT="$PWD/zforge-proxmox-v3.iso"
LOG_FILE="$PWD/zforge-build.log"

# ── Cleanup function and trap ────────────────────────────────────
cleanup() {
    local exit_code=$?
    echo
    if [[ $exit_code -ne 0 ]]; then
        echo "[!] Build failed. Cleaning up workspace..." | tee -a "$LOG_FILE"
    else
        echo "[*] Build completed. Cleaning up workspace..." | tee -a "$LOG_FILE"
    fi
    
    # Run cleanup script if it exists
    if [[ -x "$SCRIPT_DIR_ABS/cleanup-workspace.sh" ]]; then
        "$SCRIPT_DIR_ABS/cleanup-workspace.sh" "$WORKSPACE" || true
    else
        # Fallback: basic cleanup
        echo "[*] Running basic cleanup..." | tee -a "$LOG_FILE"
        
        # Unmount any mounted filesystems
        for mount in dev/pts dev proc sys run; do
            if mountpoint -q "$WORKSPACE/chroot/$mount" 2>/dev/null; then
                umount "$WORKSPACE/chroot/$mount" || umount -l "$WORKSPACE/chroot/$mount" || true
            fi
        done
        
        # Remove workspace
        rm -rf "$WORKSPACE" || sudo rm -rf "$WORKSPACE" || true
    fi
    
    if [[ $exit_code -ne 0 ]]; then
        echo "[!] Build failed with exit code: $exit_code" | tee -a "$LOG_FILE"
    fi
    
    exit $exit_code
}

# Set trap to run cleanup on exit, error, or interrupt
trap cleanup EXIT INT TERM ERR

# Check if workspace already exists and clean it
if [[ -d "$WORKSPACE" ]]; then
    echo "[!] Workspace already exists at ${WORKSPACE}" | tee -a "$LOG_FILE"
    echo "[*] Cleaning existing workspace..." | tee -a "$LOG_FILE"
    
    if [[ -x "$SCRIPT_DIR_ABS/cleanup-workspace.sh" ]]; then
        "$SCRIPT_DIR_ABS/cleanup-workspace.sh" "$WORKSPACE"
    else
        rm -rf "$WORKSPACE" || sudo rm -rf "$WORKSPACE"
    fi
fi

echo "[*] Creating workspace at ${WORKSPACE}…" ; mkdir -p "$WORKSPACE"
echo "[*] Build started at $(date)" | tee  "$LOG_FILE"

SCRIPT_DIR="$PWD"
export PYTHONPATH="${SCRIPT_DIR}:${PYTHONPATH:-}"

# ── Helper: run a Python builder module ──────────────────────────
run_module() {
    local module="$1"
    echo "[*] Running module: ${module}" | tee -a "$LOG_FILE"

    python3 - <<PY 2>&1 | tee -a "$LOG_FILE"
import sys
from builder.core.builder import ZForgeBuilder
builder = ZForgeBuilder("${SCRIPT_DIR}/build_spec.yml")
res = builder.execute_module("${module}")
if res.get("status") != "success":
    print(f"[!] Module ${module} failed: {res.get('error')}")
    sys.exit(1)
PY
    if [[ ${PIPESTATUS[0]} -ne 0 ]]; then
        echo "[!] Module ${module} failed!" | tee -a "$LOG_FILE"
        exit 1
    fi
}

# ── Default build_spec.yml ───────────────────────────────────────
if [[ ! -f "${SCRIPT_DIR}/build_spec.yml" ]]; then
    echo "[*] Creating default build configuration…" | tee -a "$LOG_FILE"
    cat > "${SCRIPT_DIR}/build_spec.yml" <<'YAML'
# ───────────── Z-FORGE Build Configuration ─────────────

builder_config:
  debian_release: trixie
  kernel_version: latest
  output_iso_name: zforge-proxmox-v3.iso
  enable_debug: true
  workspace_path: /tmp/zforge_workspace
  cache_packages: true

proxmox_config:
  version: latest
  minimal_install: true
  include_packages:
    - proxmox-ve
    - pve-kernel-6.8
    - zfs-dkms
    - zfsutils-linux
    - pve-zsync

zfs_config:
  version: latest
  build_from_source: true
  enable_encryption: true
  default_compression: lz4
  encryption:
    default_enabled: true
    default_algorithm: aes-256-gcm
    pbkdf_iterations: 350000
    prompt_during_install: true

bootloader_config:
  primary: zfsbootmenu
  enable_opencore: true
  opencore_drivers:
    - NvmExpressDxe.efi
    - OpenRuntime.efi
  encryption_support: true     # for HEAD branch users
  encrypt_boot: true           # for main branch users

dracut_config:
  modules: [zfs, systemd, network]
  compress: zstd
  hostonly: true
  kernel_cmdline: "root=zfs:AUTO"
  extra_drivers: [nvme]

modules:
  - { name: WorkspaceSetup,     enabled: true }
  - { name: Debootstrap,        enabled: true }
  - { name: KernelAcquisition,  enabled: true }
  - { name: ZFSBuild,           enabled: true }
  - { name: DracutConfig,       enabled: true }
  - { name: ProxmoxIntegration, enabled: true }
  - { name: BootloaderSetup,    enabled: true }
  - { name: SecurityHardening,  enabled: true }
  - { name: EncryptionSupport,  enabled: true }
  - { name: LiveEnvironment,    enabled: true }
  - { name: CalamaresIntegration, enabled: true }
  - { name: ISOGeneration,      enabled: true }

calamares_config:
  modules:
    - welcome
    - locale
    - keyboard
    - partition
    - zfsrootselect
    - users
    - summary
    - install
    - finished
YAML
fi

# ── Bash-level build pipeline ────────────────────────────────────
# IMPORTANT: Order matters! Each module may depend on previous ones
modules=(
  # Phase 1: Base System Setup
  "WorkspaceSetup"      # Create workspace directories
  "Debootstrap"         # Bootstrap base Debian system
  
  # Phase 2: Kernel and Core Modules  
  "KernelAcquisition"   # Install kernel + headers (required for DKMS)
  "ZFSBuild"            # Build/install ZFS (needs kernel headers)
  
  # Phase 3: Boot Infrastructure
  "DracutConfig"        # Configure dracut (needs ZFS modules)
  "BootloaderSetup"     # Configure bootloader with ZFS support
  
  # Phase 4: System Integration
  "ProxmoxIntegration"  # Install Proxmox (can use ZFS storage)
  "SecurityHardening"   # Apply security configurations  
  "EncryptionSupport"   # Setup encryption support
  
  # Phase 5: Live Environment and ISO
  "LiveEnvironment"     # Setup live system
  # CalamaresIntegration will be injected just before ISOGeneration
  "ISOGeneration"       # Generate final ISO
)

echo "[*] Starting build pipeline…" | tee -a "$LOG_FILE"

for module in "${modules[@]}"; do
    if [[ $module == "ISOGeneration" ]]; then
        echo "[*] Setting up Calamares modules…" | tee -a "$LOG_FILE"
        if ! ./setup-calamares-modules.sh; then
            echo "[!] Failed to set up Calamares modules. Aborting." | tee -a "$LOG_FILE"
            exit 1
        fi
        run_module "CalamaresIntegration"
    fi
    run_module "$module"
done

# ── Final checks / checksums ─────────────────────────────────────
if [[ -f "$ISO_OUTPUT" ]]; then
    echo "[*] Build completed successfully!" | tee -a "$LOG_FILE"
    echo "[*] ISO location: $ISO_OUTPUT"    | tee -a "$LOG_FILE"
    echo "[*] ISO size: $(du -h "$ISO_OUTPUT" | cut -f1)" | tee -a "$LOG_FILE"
    echo "[*] Generating checksums…"        | tee -a "$LOG_FILE"
    sha256sum "$ISO_OUTPUT" > "${ISO_OUTPUT}.sha256"
    md5sum    "$ISO_OUTPUT" > "${ISO_OUTPUT}.md5"
else
    echo "[!] Build failed: ISO file not created." | tee -a "$LOG_FILE"
    exit 1
fi

# ── Post-build hints ─────────────────────────────────────────────
cat <<EOS | tee -a "$LOG_FILE"

════════════════════════════════════════════════════════════════
                        BUILD COMPLETE
════════════════════════════════════════════════════════════════

Next steps:
1. Test ISO in a VM (recommended 8GB+ RAM for optimal performance):
   qemu-system-x86_64 -m 8G -cdrom $ISO_OUTPUT -enable-kvm

2. Write to USB drive (replace /dev/sdX):
   dd if=$ISO_OUTPUT of=/dev/sdX bs=4M status=progress
EOS
