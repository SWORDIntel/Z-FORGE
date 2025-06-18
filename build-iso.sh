#!/bin/bash
# Z-FORGE V3 - ISO build script

set -e

echo "════════════════════════════════════════════════════════════════"
echo "                Z-FORGE V3 ISO BUILD PROCESS"
echo "════════════════════════════════════════════════════════════════"
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

# Save script directory
SCRIPT_DIR="$PWD"

# Add script directory to Python path
export PYTHONPATH="$SCRIPT_DIR:$PYTHONPATH"

# Function to ensure dracut is installed
ensure_dracut_installed() {
    echo "[*] Ensuring dracut is properly installed..." | tee -a "$LOG_FILE"
    
    # Execute in chroot
    chroot "$WORKSPACE/chroot" /bin/bash -c "
        # Remove initramfs-tools if present
        apt-get remove -y initramfs-tools || true
        
        # Install dracut
        apt-get install -y dracut dracut-core dracut-network dracut-squash
        
        # Configure dracut for ZFS
        mkdir -p /etc/dracut.conf.d
        echo 'add_dracutmodules+=\" zfs \"' > /etc/dracut.conf.d/zfs.conf
        echo 'filesystems+=\" zfs \"' >> /etc/dracut.conf.d/zfs.conf
        
        # Create hostid
        if [ ! -f /etc/hostid ]; then
            zgenhostid \$(hexdump -n 4 -e '\"0x%08x\"' /dev/urandom)
        fi
    "
}

# Function to create dracut config module if needed
ensure_dracut_module_exists() {
    if [ ! -f "$SCRIPT_DIR/builder/modules/dracut_config.py" ]; then
        echo "[*] Creating DracutConfig module..." | tee -a "$LOG_FILE"
        cat > "$SCRIPT_DIR/builder/modules/dracut_config.py" << 'EOF'
#!/usr/bin/env python3

"""
Dracut Configuration Module
Ensures dracut is properly installed and configured for ZFS
"""

import subprocess
from pathlib import Path
from typing import Dict, Optional
import logging

class DracutConfig:
    """Handles dracut installation and configuration"""
    
    def __init__(self, workspace: Path, config: Dict):
        self.workspace = workspace
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)
        self.chroot_path = workspace / "chroot"
        
    def execute(self, resume_data: Optional[Dict] = None) -> Dict:
        """
        Install and configure dracut
        
        Returns:
            Dict with configuration status
        """
        
        self.logger.info("Starting dracut configuration...")
        
        try:
            # Remove initramfs-tools
            self._remove_initramfs_tools()
            
            # Install dracut packages
            self._install_dracut()
            
            # Configure dracut
            self._configure_dracut()
            
            # Generate initramfs with dracut
            self._generate_initramfs()
            
            return {
                'status': 'success',
                'dracut_version': self._get_dracut_version()
            }
            
        except Exception as e:
            self.logger.error(f"Dracut configuration failed: {e}")
            return {
                'status': 'error',
                'error': str(e),
                'module': self.__class__.__name__
            }
    
    def _remove_initramfs_tools(self):
        """Remove initramfs-tools if installed"""
        
        self.logger.info("Removing initramfs-tools...")
        
        subprocess.run([
            "chroot", str(self.chroot_path),
            "apt-get", "remove", "-y", "initramfs-tools"
        ], check=False)  # Don't fail if initramfs-tools isn't installed
    
    def _install_dracut(self):
        """Install dracut packages"""
        
        self.logger.info("Installing dracut packages...")
        
        subprocess.run([
            "chroot", str(self.chroot_path),
            "apt-get", "install", "-y",
            "dracut",
            "dracut-core",
            "dracut-network",
            "dracut-squash"
        ], check=True)
    
    def _configure_dracut(self):
        """Configure dracut"""
        
        self.logger.info("Configuring dracut...")
        
        # Get dracut config from build configuration
        dracut_cfg = self.config.get('dracut_config', {})
        modules = dracut_cfg.get('modules', ['zfs', 'systemd', 'network'])
        compress = dracut_cfg.get('compress', 'zstd')
        hostonly = 'yes' if dracut_cfg.get('hostonly', True) else 'no'
        kernel_cmdline = dracut_cfg.get('kernel_cmdline', 'root=zfs:AUTO')
        extra_drivers = dracut_cfg.get('extra_drivers', ['nvme'])
        
        # Create main dracut configuration
        dracut_conf = f"""# Z-Forge dracut configuration

# Compression method
compress="{compress}"

# Include extra modules
add_dracutmodules+=" {' '.join(modules)} "

# Include necessary filesystem modules
filesystems+=" zfs "

# Enable hostonly mode
hostonly="{hostonly}"

# Add kernel command line parameters
kernel_cmdline="{kernel_cmdline}"

# Include any additional drivers
add_drivers+=" {' '.join(extra_drivers)} "
"""
        
        dracut_conf_path = self.chroot_path / "etc/dracut.conf.d/zforge.conf"
        dracut_conf_path.parent.mkdir(parents=True, exist_ok=True)
        with open(dracut_conf_path, 'w') as f:
            f.write(dracut_conf)
        
        # Create ZFS-specific configuration
        zfs_conf = """# ZFS dracut configuration

# Enable ZFS hostid support
install_optional_items+=" /etc/hostid /etc/zfs/zpool.cache "

# Include ZFS commands
install_items+=" /usr/bin/zfs /usr/bin/zpool "
"""
        
        zfs_conf_path = self.chroot_path / "etc/dracut.conf.d/zfs.conf"
        with open(zfs_conf_path, 'w') as f:
            f.write(zfs_conf)
        
        # Create hostid if it doesn't exist
        hostid_path = self.chroot_path / "etc/hostid"
        if not hostid_path.exists():
            subprocess.run([
                "chroot", str(self.chroot_path),
                "bash", "-c", "zgenhostid $(hexdump -n 4 -e '\"0x%08x\"' /dev/urandom)"
            ], check=True)
    
    def _generate_initramfs(self):
        """Generate initramfs with dracut"""
        
        self.logger.info("Generating initramfs with dracut...")
        
        # Find installed kernel
        kernel_version_cmd = "ls -1 /lib/modules | tail -1"
        result = subprocess.run(
            ["chroot", str(self.chroot_path), "bash", "-c", kernel_version_cmd],
            capture_output=True,
            text=True,
            check=True
        )
        
        kernel_version = result.stdout.strip()
        
        if not kernel_version:
            raise Exception("No kernel modules found")
        
        self.logger.info(f"Regenerating initramfs for kernel {kernel_version}")
        
        # Generate initramfs
        subprocess.run([
            "chroot", str(self.chroot_path),
            "dracut", "-f", f"/boot/initramfs-{kernel_version}.img", kernel_version,
            "--force", "--verbose"
        ], check=True)
        
        # Create symbolic link for compatibility
        subprocess.run([
            "chroot", str(self.chroot_path),
            "ln", "-sf", f"initramfs-{kernel_version}.img", f"/boot/initrd.img-{kernel_version}"
        ], check=True)
    
    def _get_dracut_version(self):
        """Get installed dracut version"""
        
        result = subprocess.run(
            ["chroot", str(self.chroot_path), "dracut", "--version"],
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            return result.stdout.strip()
        return "unknown"
EOF
        chmod +x "$SCRIPT_DIR/builder/modules/dracut_config.py"
    fi
}

# Function to run builder module
run_module() {
    local module=$1
    echo "[*] Running module: $module" | tee -a "$LOG_FILE"
    
    python3 -c "
import sys
from builder.core.builder import ZForgeBuilder
builder = ZForgeBuilder('$SCRIPT_DIR/build_spec.yml')
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

# Ensure dracut module exists
ensure_dracut_module_exists

# Make sure build_spec.yml exists
if [ ! -f "$SCRIPT_DIR/build_spec.yml" ]; then
    echo "[*] Creating default build configuration..." | tee -a "$LOG_FILE"
    cat > "$SCRIPT_DIR/build_spec.yml" << 'EOF'
# Z-Forge Build Configuration
builder_config:
  debian_release: bookworm
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

bootloader_config:
  primary: zfsbootmenu
  enable_opencore: true
  opencore_drivers:
    - NvmExpressDxe.efi
    - OpenRuntime.efi

dracut_config:
  modules:
    - zfs
    - systemd
    - network
  compress: zstd
  hostonly: true
  kernel_cmdline: "root=zfs:AUTO"
  extra_drivers:
    - nvme

modules:
  - name: WorkspaceSetup
    enabled: true
  - name: Debootstrap
    enabled: true
  - name: KernelAcquisition
    enabled: true
  - name: ZFSBuild
    enabled: true
  - name: DracutConfig
    enabled: true
  - name: ProxmoxIntegration
    enabled: true
  - name: LiveEnvironment
    enabled: true
  - name: CalamaresIntegration
    enabled: true
  - name: ISOGeneration
    enabled: true
EOF
fi

# Run each module in sequence
modules=(
    "WorkspaceSetup"
    "Debootstrap"
    "KernelAcquisition"
    "ZFSBuild"
    "DracutConfig"
    "ProxmoxIntegration"
    "LiveEnvironment"
    "CalamaresIntegration"
    "ISOGeneration"
)

# Add hook to ensure dracut after debootstrap
after_debootstrap() {
    echo "[*] Post-Debootstrap: Ensuring dracut is installed..." | tee -a "$LOG_FILE"
    ensure_dracut_installed
}

for module in "${modules[@]}"; do
    run_module "$module"
    
    # Special hooks after specific modules
    if [ "$module" == "Debootstrap" ]; then
        after_debootstrap
    fi
done

# Final steps
if [ -f "$ISO_OUTPUT" ]; then
    echo "[*] Build completed successfully!" | tee -a "$LOG_FILE"
    echo "[*] ISO location: $ISO_OUTPUT" | tee -a "$LOG_FILE"
    echo "[*] ISO size: $(du -h "$ISO_OUTPUT" | cut -f1)" | tee -a "$LOG_FILE"

    # Generate checksums
    echo "[*] Generating checksums..." | tee -a "$LOG_FILE"
    sha256sum "$ISO_OUTPUT" > "$ISO_OUTPUT.sha256"
    md5sum "$ISO_OUTPUT" > "$ISO_OUTPUT.md5"
else
    echo "[!] Build failed: ISO file not created" | tee -a "$LOG_FILE"
    exit 1
fi

echo "" | tee -a "$LOG_FILE"
echo "════════════════════════════════════════════════════════════════"
echo "                    BUILD COMPLETE"
echo "════════════════════════════════════════════════════════════════"
echo "" | tee -a "$LOG_FILE"
echo "Next steps:" | tee -a "$LOG_FILE"
echo "1. Test ISO in virtual machine:" | tee -a "$LOG_FILE"
echo "   qemu-system-x86_64 -m 4G -cdrom $ISO_OUTPUT -enable-kvm" | tee -a "$LOG_FILE"
echo "" | tee -a "$LOG_FILE"
echo "2. Write to USB drive:" | tee -a "$LOG_FILE"
echo "   dd if=$ISO_OUTPUT of=/dev/sdX bs=4M status=progress" | tee -a "$LOG_FILE"
echo "" | tee -a "$LOG_FILE"
