#!/bin/bash
# Simple fix and resume script

echo "=== Simple Fix and Resume ==="

# Fix the repository first
sudo ./scripts/fix_snapshot_repo.sh

# Check if fix worked
if [ -f "/root/zforge_cache/trixie_snapshot/repository/Packages.gz" ]; then
    echo "✓ Repository fixed successfully"
    
    # Now fix the chroot sources
    echo "Updating chroot sources..."
    sudo rm -f /root/zforge_workspace/chroot/etc/apt/sources.list.d/zforge-snapshot.list
    echo "deb [trusted=yes] file:///root/zforge_cache/trixie_snapshot/repository ./" | sudo tee /root/zforge_workspace/chroot/etc/apt/sources.list.d/zforge-snapshot.list
    
    # Update chroot
    sudo chroot /root/zforge_workspace/chroot apt-get update
    
    # Resume build
    echo "Resuming build..."
    sudo python3 build.py --spec build_spec_proxmox9.yml --resume
    
else
    echo "✗ Repository fix failed"
    echo "Falling back to regular build..."
    sudo python3 build.py --spec build_spec.yml --resume
fi