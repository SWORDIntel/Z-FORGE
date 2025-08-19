#!/bin/bash
# Fix DKMS temporary directory issue in chroot environment

echo "Fixing DKMS in chroot environment..."

# Run this script inside the chroot with proper environment
./scripts/chroot/use_arch_chroot.sh /home/john/zforge_workspace/chroot bash -c "
    export TMPDIR=/tmp
    export TMP=/tmp
    export TEMP=/tmp
    
    # Ensure tmp directory exists and is writable
    mkdir -p /tmp
    chmod 1777 /tmp 2>/dev/null || chmod 777 /tmp
    
    # Test mktemp
    echo 'Testing mktemp in chroot...'
    TESTFILE=\$(mktemp)
    if [ -f \"\$TESTFILE\" ]; then
        echo '✅ mktemp working in chroot'
        rm -f \"\$TESTFILE\"
    else
        echo '❌ mktemp failing in chroot'
        exit 1
    fi
    
    # Continue with kernel configuration
    echo 'Continuing kernel installation...'
    env TMPDIR=/tmp TMP=/tmp TEMP=/tmp dpkg --configure -a
"