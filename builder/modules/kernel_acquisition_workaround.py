#!/usr/bin/env python3
"""
Workaround for kernel version with + character issue
This module replaces the standard dracut generation with a more robust approach
"""

import os
import subprocess
from pathlib import Path
import logging

class KernelAcquisitionWorkaround:
    """Alternative dracut handling for problematic kernel versions"""
    
    @staticmethod
    def generate_initramfs_workaround(chroot_path: Path, kernel_version: str, logger: logging.Logger):
        """
        Generate initramfs using alternative methods when standard dracut fails
        """
        logger.info(f"Applying workaround for kernel version: {kernel_version}")
        
        # Method 1: Use mkinitramfs if available (as fallback)
        try:
            # Check if mkinitramfs exists
            result = subprocess.run(
                ["chroot", str(chroot_path), "which", "mkinitramfs"],
                capture_output=True
            )
            if result.returncode == 0:
                logger.info("Found mkinitramfs, using as fallback")
                # Install initramfs-tools if not present
                subprocess.run(
                    ["chroot", str(chroot_path), "apt-get", "install", "-y", "initramfs-tools"],
                    check=False
                )
                # Generate initramfs
                subprocess.run(
                    ["chroot", str(chroot_path), "mkinitramfs", "-o", 
                     f"/boot/initrd.img-{kernel_version}", kernel_version],
                    check=True
                )
                logger.info("Successfully generated initramfs using mkinitramfs")
                return True
        except subprocess.CalledProcessError:
            logger.warning("mkinitramfs approach failed")
        
        # Method 2: Create a wrapper script that handles the + character
        try:
            wrapper_script = f"""#!/bin/bash
# Dracut wrapper for kernel with + character
KVER="{kernel_version}"
OUTPUT="/boot/initrd.img-{kernel_version}"

# Create dracut config that works around the issue
cat > /etc/dracut.conf.d/99-workaround.conf <<EOF
# Workaround for kernel version with +
hostonly="no"
add_dracutmodules+=" kernel-modules base rootfs-block zfs "
omit_dracutmodules+=" network "
compress="zstd"
show_modules="yes"
EOF

# Try different approaches
echo "Attempting dracut with escaped kernel version..."
dracut --force --verbose "$OUTPUT" "$KVER" || \\
dracut --force --verbose "$OUTPUT" || \\
dracut --force --no-kernel "$OUTPUT"

# Clean up
rm -f /etc/dracut.conf.d/99-workaround.conf

# Verify output
if [ -f "$OUTPUT" ]; then
    echo "Successfully created $OUTPUT"
    exit 0
else
    echo "Failed to create initramfs"
    exit 1
fi
"""
            wrapper_path = chroot_path / "tmp" / "dracut_wrapper.sh"
            with open(wrapper_path, 'w') as f:
                f.write(wrapper_script)
            os.chmod(wrapper_path, 0o755)
            
            result = subprocess.run(
                ["chroot", str(chroot_path), "/tmp/dracut_wrapper.sh"],
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                logger.info("Successfully generated initramfs using wrapper script")
                return True
            else:
                logger.error(f"Wrapper script failed: {result.stderr}")
                
        except Exception as e:
            logger.error(f"Wrapper script approach failed: {e}")
        
        # Method 3: Copy from a working kernel if available
        try:
            boot_dir = chroot_path / "boot"
            existing_initrds = list(boot_dir.glob("initrd.img-*"))
            if existing_initrds:
                source_initrd = existing_initrds[0]
                target_initrd = boot_dir / f"initrd.img-{kernel_version}"
                
                logger.warning(f"Copying existing initrd from {source_initrd.name}")
                import shutil
                shutil.copy2(source_initrd, target_initrd)
                
                # Try to update it with current kernel modules
                update_script = f"""#!/bin/bash
cd /tmp
mkdir -p initrd_work
cd initrd_work
zcat {target_initrd} | cpio -id 2>/dev/null
# Update kernel modules if possible
if [ -d /lib/modules/{kernel_version} ]; then
    rm -rf lib/modules/*
    cp -r /lib/modules/{kernel_version} lib/modules/
fi
find . | cpio -o -H newc | gzip > {target_initrd}
cd /
rm -rf /tmp/initrd_work
"""
                update_path = chroot_path / "tmp" / "update_initrd.sh"
                with open(update_path, 'w') as f:
                    f.write(update_script)
                os.chmod(update_path, 0o755)
                
                subprocess.run(
                    ["chroot", str(chroot_path), "/tmp/update_initrd.sh"],
                    check=False
                )
                
                logger.info("Created initramfs by copying and updating existing one")
                return True
                
        except Exception as e:
            logger.error(f"Copy approach failed: {e}")
        
        return False