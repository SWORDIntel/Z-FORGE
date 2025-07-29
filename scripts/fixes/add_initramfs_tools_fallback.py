#!/usr/bin/env python3
"""
Add initramfs-tools fallback to kernel_acquisition.py if dracut fails
"""
import os
import sys
from pathlib import Path

def add_initramfs_tools_fallback():
    """Add fallback to initramfs-tools if dracut completely fails"""
    
    # Find the kernel_acquisition.py file
    module_path = Path(__file__).parent.parent.parent / "builder" / "modules" / "kernel_acquisition.py"
    
    if not module_path.exists():
        print(f"[!] Module not found: {module_path}")
        sys.exit(1)
    
    print(f"[*] Adding initramfs-tools fallback to: {module_path}")
    
    # Read the current content
    with open(module_path, 'r') as f:
        content = f.read()
    
    # Find the location where dracut completely fails
    # Look for the final error raise in _generate_dracut_initramfs
    error_location = content.find("# Re-raise original error if all attempts failed")
    
    if error_location == -1:
        print("[!] Could not find the error handling section")
        return False
    
    # Insert the initramfs-tools fallback before re-raising the error
    fallback_code = '''                
                # Final fallback: Try initramfs-tools if dracut completely failed
                self.logger.warning("All dracut attempts failed, falling back to initramfs-tools")
                try:
                    return self._generate_initramfs_tools(kernel_version, include_encryption)
                except Exception as fallback_e:
                    self.logger.error(f"initramfs-tools fallback also failed: {fallback_e}")
                    # Continue with original dracut error
'''
    
    # Insert the fallback code
    new_content = content[:error_location] + fallback_code + content[error_location:]
    
    # Now add the initramfs-tools method to the class
    # Find a good place to insert it (after _generate_dracut_initramfs)
    method_insert_location = content.find("def _install_dracut_emergency")
    
    if method_insert_location == -1:
        # Find alternative location
        method_insert_location = content.find("def _mount_pseudo_filesystems")
    
    initramfs_tools_method = '''
    def _generate_initramfs_tools(self, kernel_version: str, include_encryption: bool = False) -> Tuple[Path, Path]:
        """
        Generate initramfs using initramfs-tools as a fallback when dracut fails.
        
        Args:
            kernel_version: The kernel version to generate initramfs for.
            include_encryption: Whether to include encryption support.
            
        Returns:
            Paths to vmlinuz and initrd.img.
        """
        self.logger.info(f"Generating initramfs using initramfs-tools for kernel {kernel_version}...")
        
        # Define paths
        vmlinuz_path = Path("/boot") / f"vmlinuz-{kernel_version}"
        initrd_path = Path("/boot") / f"initrd.img-{kernel_version}"
        
        # Verify that vmlinuz exists
        chroot_vmlinuz_path = self.chroot_path / vmlinuz_path.relative_to("/")
        if not chroot_vmlinuz_path.exists():
            raise FileNotFoundError(f"Kernel image {vmlinuz_path} not found in chroot")
        
        # Install initramfs-tools if not present
        self.logger.info("Ensuring initramfs-tools is installed...")
        try:
            self._run_chroot_command([
                "apt-get", "install", "-y", "--no-install-recommends",
                "initramfs-tools", "initramfs-tools-core"
            ])
        except subprocess.CalledProcessError as e:
            self.logger.warning(f"Failed to install initramfs-tools: {e}")
        
        # Configure initramfs-tools for ZFS if needed
        if self.config.get('zfs_config', {}).get('enable', True):
            self.logger.info("Configuring initramfs-tools for ZFS support...")
            
            # Create hook script for ZFS
            hook_content = """#!/bin/sh
# ZFS hook for initramfs-tools
PREREQ=""
prereqs()
{
    echo "$PREREQ"
}
case $1 in
prereqs)
    prereqs
    exit 0
    ;;
esac

. /usr/share/initramfs-tools/hook-functions

# Copy ZFS utilities
copy_exec /sbin/zfs
copy_exec /sbin/zpool
copy_exec /sbin/mount.zfs

# Ensure ZFS modules are included
manual_add_modules zfs

# Copy ZFS configuration
if [ -f /etc/zfs/zpool.cache ]; then
    cp -a /etc/zfs/zpool.cache "${DESTDIR}/etc/zfs/"
fi
"""
            hook_path = self.chroot_path / "etc" / "initramfs-tools" / "hooks" / "zfs"
            hook_path.parent.mkdir(parents=True, exist_ok=True)
            with open(hook_path, 'w') as f:
                f.write(hook_content)
            os.chmod(hook_path, 0o755)
            
            # Add ZFS modules to initramfs modules
            modules_path = self.chroot_path / "etc" / "initramfs-tools" / "modules"
            with open(modules_path, 'a') as f:
                f.write("\\n# ZFS modules\\nzfs\\n")
        
        # Add encryption support if needed
        if include_encryption:
            conf_path = self.chroot_path / "etc" / "initramfs-tools" / "initramfs.conf"
            if conf_path.exists():
                with open(conf_path, 'r') as f:
                    conf_content = f.read()
                
                # Enable cryptsetup
                if "CRYPTSETUP=n" in conf_content:
                    conf_content = conf_content.replace("CRYPTSETUP=n", "CRYPTSETUP=y")
                    with open(conf_path, 'w') as f:
                        f.write(conf_content)
        
        # Mount required filesystems
        self._mount_pseudo_filesystems()
        
        try:
            # Run update-initramfs
            self.logger.info(f"Running update-initramfs for kernel {kernel_version}...")
            
            # First, try to create the initramfs
            initramfs_cmd = [
                "update-initramfs",
                "-c",  # Create
                "-k", kernel_version,
                "-v"   # Verbose
            ]
            
            try:
                self._run_chroot_command(initramfs_cmd)
            except subprocess.CalledProcessError as e:
                # If creation fails, try updating existing
                self.logger.warning("Creation failed, trying update...")
                update_cmd = [
                    "update-initramfs",
                    "-u",  # Update
                    "-k", kernel_version,
                    "-v"
                ]
                self._run_chroot_command(update_cmd)
            
            # Verify the initramfs was created
            chroot_initrd_path = self.chroot_path / initrd_path.relative_to("/")
            if not chroot_initrd_path.exists():
                # Check for versioned initrd
                alt_initrd_path = Path("/boot") / f"initrd.img-{kernel_version}"
                chroot_alt_initrd = self.chroot_path / alt_initrd_path.relative_to("/")
                if chroot_alt_initrd.exists():
                    initrd_path = alt_initrd_path
                else:
                    raise FileNotFoundError(f"Failed to generate initramfs at {initrd_path}")
            
            self.logger.info(f"Successfully generated initramfs with initramfs-tools at {initrd_path}")
            
        except subprocess.CalledProcessError as e:
            self.logger.error(f"update-initramfs failed: {e}")
            self.logger.error(f"stdout: {e.stdout}")
            self.logger.error(f"stderr: {e.stderr}")
            raise
        finally:
            # Always unmount the filesystems
            self._unmount_pseudo_filesystems()
        
        return vmlinuz_path, initrd_path
    '''
    
    # Insert the new method
    new_content = new_content[:method_insert_location] + initramfs_tools_method + "\n" + new_content[method_insert_location:]
    
    # Write the updated content
    with open(module_path, 'w') as f:
        f.write(new_content)
    
    print("[✓] Added initramfs-tools fallback method")
    print("[✓] Integrated fallback into error handling")
    print("[✓] Added ZFS support for initramfs-tools")
    
    return True

if __name__ == "__main__":
    print("=== Adding initramfs-tools Fallback ===")
    
    if add_initramfs_tools_fallback():
        print("\n[✓] Successfully added initramfs-tools fallback")
        print("\nNow if dracut completely fails, the build will automatically")
        print("fall back to using the standard Debian initramfs-tools.")
    else:
        print("\n[!] Failed to add fallback")
        sys.exit(1)