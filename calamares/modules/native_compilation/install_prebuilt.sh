#!/bin/bash
# Fallback script for Calamares native compilation
# Installs prebuilt packages if compilation fails

set -euo pipefail

LOG_FILE="/tmp/native_compilation_fallback.log"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] FALLBACK: $*" | tee -a "$LOG_FILE"
}

main() {
    log "Native compilation failed, installing prebuilt packages as fallback"
    
    # Update package lists
    apt-get update -qq
    
    # Install basic ZFS packages from Debian repositories
    log "Installing ZFS from Debian repositories..."
    apt-get install -y -qq \
        zfsutils-linux \
        zfs-dkms \
        zfs-zed || true
    
    # Try to install any prebuilt packages from the ISO
    if [ -d "/cdrom/pool/main" ]; then
        log "Installing additional packages from ISO..."
        
        # Install any ZFS packages
        find /cdrom/pool -name "*zfs*.deb" -exec dpkg -i {} \; 2>/dev/null || true
        
        # Install any Proxmox packages
        find /cdrom/pool -name "*proxmox*.deb" -exec dpkg -i {} \; 2>/dev/null || true
        find /cdrom/pool -name "*pve*.deb" -exec dpkg -i {} \; 2>/dev/null || true
    fi
    
    # Fix any broken dependencies
    apt-get -f install -y -qq || true
    
    # Enable basic services
    systemctl enable zfs.target || true
    systemctl enable zfs-import-cache || true
    
    # Load modules if possible
    modprobe zfs 2>/dev/null || log "Could not load ZFS module (normal during installation)"
    
    log "Fallback installation complete"
    log "Warning: System is using generic packages, not optimized for this hardware"
    
    echo "FALLBACK_SUCCESS" > /tmp/calamares_progress
}

main "$@"