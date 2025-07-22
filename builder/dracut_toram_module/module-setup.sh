#!/bin/bash
# module-setup.sh for 90zforge-toram

# called by dracut
check() {
    # We need dmsquash-live for live ISO support
    require_binaries mksquashfs unsquashfs || return 1
    return 0
}

# called by dracut
depends() {
    # We depend on dmsquash-live for squashfs support
    echo dmsquash-live systemd
}

# called by dracut
install() {
    # Install our toram hook
    inst_hook pre-pivot 90 "$moddir/zforge-toram-hook.sh"
    
    # Install required binaries
    inst_multiple dd free awk grep
}

installkernel() {
    # Include squashfs and loop modules
    hostonly='' instmods squashfs loop
}
