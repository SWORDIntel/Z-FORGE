#!/bin/bash
# module-setup.sh for 90zforge-toram

# called by dracut
check() {
    # Check for required binaries
    require_binaries dd free awk grep || return 1
    return 0
}

# called by dracut
depends() {
    # Basic dependencies - removed dmsquash-live as it's not available in Debian
    echo systemd
}

# called by dracut
install() {
    # Install our toram hook
    inst_hook pre-pivot 90 "$moddir/zforge-toram-hook.sh"
    
    # Install required binaries
    inst_multiple dd free awk grep mount umount
    
    # Install filesystem tools
    inst_multiple fsck mkfs.ext4 mkfs.vfat || true
}

installkernel() {
    # Include necessary modules
    hostonly='' instmods squashfs loop overlay tmpfs
}
