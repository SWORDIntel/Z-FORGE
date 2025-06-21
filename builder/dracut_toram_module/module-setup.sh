#!/bin/bash

# Called by dracut
check() {
    # Require tools like grep, findmnt, losetup, etc.
    # dmsquash ensures squashfs tools are available.
    require_binaries grep findmnt losetup umount switch_root mount cp blockdev awk || return 1
    return 0
}

# Called by dracut
depends() {
    # Depends on network, base, kernel-modules, dmsquash (for live squashfs)
    echo "base kernel-modules dmsquash"
    return 0
}

# Called by dracut
install() {
    # Install the hook script that does the actual work
    inst_hook cmdline 30 "\$moddir/zforge-toram-hook.sh"
}
