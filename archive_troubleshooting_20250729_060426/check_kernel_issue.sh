#!/bin/bash
# Check what's preventing kernel installation

echo "=== Kernel Installation Issue Diagnosis ==="
echo

# Check if we can run those commands
echo "1. Checking kernel policy:"
echo "sudo chroot /tmp/zforge_workspace/chroot apt-cache policy linux-image-amd64"
echo

echo "2. Available kernels:"  
echo "sudo chroot /tmp/zforge_workspace/chroot apt-cache search linux-image-6"
echo

echo "3. Current APT sources:"
echo "sudo head -3 /tmp/zforge_workspace/chroot/etc/apt/sources.list"
echo

echo "=== IMMEDIATE FIX ==="
echo "Run the nuclear option:"
echo "sudo /opt/github/Z-FORGE/nuclear_kernel_fix.sh"
echo
echo "This will:"
echo "• Force remove all old kernels"
echo "• Try 5 different installation methods"
echo "• Use aggressive APT options"
echo "• Download packages manually if needed"
echo "• Handle all edge cases"