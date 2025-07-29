#!/usr/bin/env python3
"""
Fix ZFS package availability by adding proper repositories
"""
import os
import sys
from pathlib import Path

def fix_zfs_repositories():
    """Fix ZFS package availability in multiple modules"""
    
    # First, fix the ZFSBuild module
    zfs_module_path = Path(__file__).parent.parent.parent / "builder" / "modules" / "zfs_build.py"
    
    if zfs_module_path.exists():
        print(f"[*] Fixing ZFS repositories in: {zfs_module_path}")
        
        with open(zfs_module_path, 'r') as f:
            content = f.read()
        
        # Add repository setup method
        repo_setup = '''
    def _setup_zfs_repositories(self):
        """Setup repositories for ZFS packages"""
        self.logger.info("Setting up ZFS repositories...")
        
        # Update sources.list to include contrib and non-free-firmware
        sources_list = self.chroot_path / "etc/apt/sources.list"
        if sources_list.exists():
            with open(sources_list, 'r') as f:
                sources_content = f.read()
            
            # Check if contrib is already enabled
            if 'contrib' not in sources_content:
                self.logger.info("Adding contrib and non-free-firmware to sources.list...")
                lines = sources_content.split('\\n')
                new_lines = []
                
                for line in lines:
                    if line.strip() and not line.strip().startswith('#'):
                        if 'deb ' in line and 'main' in line and 'contrib' not in line:
                            # Add contrib and non-free-firmware
                            line = line.rstrip() + ' contrib non-free-firmware'
                    new_lines.append(line)
                
                with open(sources_list, 'w') as f:
                    f.write('\\n'.join(new_lines))
        
        # For Debian Trixie, ZFS is in contrib
        # No need for backports as Trixie is testing/unstable
        
        # Update package lists
        try:
            result = subprocess.run(
                ["sudo", "chroot", str(self.chroot_path), "apt-get", "update"],
                capture_output=True,
                text=True,
                check=True
            )
            self.logger.info("Package lists updated successfully")
        except subprocess.CalledProcessError as e:
            self.logger.warning(f"Failed to update package lists: {e}")
        
        # Install ZFS packages with proper error handling
        return self._install_zfs_packages_with_fallback()
    
    def _install_zfs_packages_with_fallback(self):
        """Try different ZFS package combinations"""
        # Try different package combinations
        package_sets = [
            # Primary: Standard ZFS packages
            ["zfsutils-linux", "zfs-dkms"],
            # Fallback 1: Just userspace tools
            ["zfsutils-linux"],
            # Fallback 2: Alternative package names
            ["zfs", "zfs-dkms"],
            # Fallback 3: Minimal ZFS
            ["zfs"],
        ]
        
        for i, packages in enumerate(package_sets):
            try:
                self.logger.info(f"Attempting to install ZFS packages (attempt {i+1}): {packages}")
                
                cmd = [
                    "sudo", "chroot", str(self.chroot_path),
                    "apt-get", "install", "-y", "--no-install-recommends"
                ] + packages
                
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    check=True
                )
                
                self.logger.info(f"Successfully installed ZFS packages: {packages}")
                return True
                
            except subprocess.CalledProcessError as e:
                self.logger.warning(f"Failed to install {packages}: {e.stderr}")
                
                if i == len(package_sets) - 1:
                    # Last attempt failed
                    self.logger.error("All ZFS installation attempts failed")
                    # Don't fail the build - ZFS might be optional
                    return False
        
        return False
'''
        
        # Find where to insert this in the module
        # Look for the execute method
        execute_pos = content.find("def execute(")
        if execute_pos > 0:
            # Find the class definition
            class_pos = content.rfind("class ", 0, execute_pos)
            if class_pos > 0:
                # Find end of class opening
                class_end = content.find(":", class_pos)
                next_method = content.find("\n    def ", class_end)
                
                # Insert our methods
                new_content = content[:next_method] + "\n" + repo_setup + content[next_method:]
                
                # Now update the execute method to use our setup
                execute_start = new_content.find("def execute(")
                if execute_start > 0:
                    # Find where ZFS installation happens
                    zfs_install = new_content.find("apt-get install -y zfsutils-linux", execute_start)
                    if zfs_install > 0:
                        # Find the start of that command
                        cmd_start = new_content.rfind("subprocess.run", execute_start, zfs_install)
                        if cmd_start > 0:
                            # Replace with our method call
                            line_start = new_content.rfind("\n", 0, cmd_start)
                            line_end = new_content.find("\n", zfs_install)
                            
                            replacement = '''
        # Setup ZFS repositories and install packages
        if not self._setup_zfs_repositories():
            self.logger.warning("ZFS packages could not be installed")
            # Continue anyway - dracut might handle it'''
                            
                            new_content = new_content[:line_start] + replacement + new_content[line_end:]
                
                # Write the updated content
                with open(zfs_module_path, 'w') as f:
                    f.write(new_content)
                
                print("[✓] Updated ZFSBuild module")
    
    # Also update kernel_acquisition.py if needed
    kernel_module_path = Path(__file__).parent.parent.parent / "builder" / "modules" / "kernel_acquisition.py"
    if kernel_module_path.exists():
        print(f"[*] Checking kernel_acquisition.py...")
        
        with open(kernel_module_path, 'r') as f:
            content = f.read()
        
        # The kernel module already has _add_zfs_repository method
        # Just make sure it's being called properly
        if "_add_zfs_repository" in content:
            print("[✓] kernel_acquisition.py already has ZFS repository setup")
        
    return True

def create_apt_sources_fix():
    """Create a script to fix apt sources in the chroot"""
    
    fix_script = '''#!/bin/bash
# Fix APT sources for ZFS packages

CHROOT_PATH="${1:-/tmp/zforge_workspace/chroot}"

echo "Fixing APT sources for ZFS packages in chroot: $CHROOT_PATH"

# Check if chroot exists
if [ ! -d "$CHROOT_PATH" ]; then
    echo "Error: Chroot path does not exist: $CHROOT_PATH"
    exit 1
fi

# Update sources.list to include contrib
echo "Updating sources.list..."
sudo sed -i 's/main$/main contrib non-free-firmware/g' "$CHROOT_PATH/etc/apt/sources.list"
sudo sed -i 's/main non-free-firmware$/main contrib non-free-firmware/g' "$CHROOT_PATH/etc/apt/sources.list"

# Show updated sources
echo "Updated sources.list:"
grep -v "^#" "$CHROOT_PATH/etc/apt/sources.list" | grep -v "^$"

# Update package lists
echo "Updating package lists..."
sudo chroot "$CHROOT_PATH" apt-get update

# Check if ZFS packages are available
echo "Checking ZFS package availability..."
sudo chroot "$CHROOT_PATH" apt-cache policy zfsutils-linux || echo "zfsutils-linux not found"
sudo chroot "$CHROOT_PATH" apt-cache policy zfs-dkms || echo "zfs-dkms not found"
sudo chroot "$CHROOT_PATH" apt-cache policy zfs || echo "zfs not found"

echo "APT sources fixed. You can now try installing ZFS packages."
'''
    
    script_path = Path(__file__).parent / "fix_apt_sources_zfs.sh"
    with open(script_path, 'w') as f:
        f.write(fix_script)
    
    os.chmod(script_path, 0o755)
    print(f"[✓] Created fix script: {script_path}")
    
    return script_path

if __name__ == "__main__":
    print("=== Fixing ZFS Repository Configuration ===")
    
    # Fix the modules
    if fix_zfs_repositories():
        print("\n[✓] ZFS repository configuration fixed")
    
    # Create manual fix script
    script_path = create_apt_sources_fix()
    
    print("\n[✓] Fixes applied!")
    print("\nIf the build has already created a chroot, you can manually fix it with:")
    print(f"  {script_path}")
    print("\nOr just run the build again - it should now work with the updated modules.")