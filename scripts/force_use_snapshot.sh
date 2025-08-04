#!/bin/bash
# Force build to use stable Trixie snapshot instead of live repos

echo "=== Forcing build to use stable Trixie snapshot ==="

# Copy snapshot sources to chroot
if [ -d "/root/zforge_workspace/chroot" ]; then
    echo "✓ Found chroot directory"
    
    # Add snapshot repository to sources.list
    echo "deb [trusted=yes] file:///root/zforge_cache/trixie_snapshot/repository ./" > /root/zforge_workspace/chroot/etc/apt/sources.list.d/zforge-snapshot.list
    
    # Comment out problematic repositories
    sed -i 's/^deb/#deb/g' /root/zforge_workspace/chroot/etc/apt/sources.list
    
    # Update package lists in chroot
    chroot /root/zforge_workspace/chroot apt-get update
    
    echo "✓ Chroot configured to use snapshot"
else
    echo "✗ No chroot found - run this after workspace_setup"
fi

echo "Done!"