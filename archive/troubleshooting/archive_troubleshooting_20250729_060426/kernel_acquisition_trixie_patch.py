#!/usr/bin/env python3
"""
Patch for kernel_acquisition.py to properly support Debian Trixie.

This patch updates the kernel acquisition module to:
1. Detect the Debian release (Trixie)
2. Use appropriate repositories for the detected release
3. Install matching kernel and headers for DKMS compatibility
"""

import re
from pathlib import Path
import shutil
from datetime import datetime

def create_patched_kernel_acquisition():
    """Create a patched version of kernel_acquisition.py for Trixie support."""
    
    original_file = Path("/opt/github/Z-FORGE/builder/modules/kernel_acquisition.py")
    backup_file = Path(f"/opt/github/Z-FORGE/builder/modules/kernel_acquisition.py.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
    
    # Read the original file
    with open(original_file, 'r') as f:
        content = f.read()
    
    # Create backup
    shutil.copy2(original_file, backup_file)
    print(f"Created backup at: {backup_file}")
    
    # Patch 1: Add method to detect Debian release
    detect_release_method = '''
    def _detect_debian_release(self) -> str:
        """Detect the Debian release in the chroot environment."""
        try:
            os_release = self.chroot_path / "etc/os-release"
            if os_release.exists():
                with open(os_release, 'r') as f:
                    for line in f:
                        if line.startswith('VERSION_CODENAME='):
                            return line.split('=')[1].strip().strip('"')
            
            # Check debian_version as fallback
            debian_version = self.chroot_path / "etc/debian_version"
            if debian_version.exists():
                with open(debian_version, 'r') as f:
                    version = f.read().strip()
                    if '13' in version or 'trixie' in version:
                        return 'trixie'
                    elif '12' in version:
                        return 'bookworm'
                    elif '11' in version:
                        return 'bullseye'
            
            # Default to trixie for Z-FORGE
            return 'trixie'
        except Exception as e:
            self.logger.warning(f"Error detecting Debian release: {e}")
            return 'trixie'
'''
    
    # Insert the method after __init__
    init_end = content.find("def execute(")
    if init_end > 0:
        content = content[:init_end] + detect_release_method + "\n" + content[init_end:]
    
    # Patch 2: Update _prepare_chroot_environment to use detected release
    content = re.sub(
        r'# Note: Using bookworm for Proxmox as they may not have trixie repos yet',
        '# Detect Debian release and use appropriate repos',
        content
    )
    
    content = re.sub(
        r'sources_list = """# Proxmox kernel repositories\ndeb \[signed-by=/etc/apt/keyrings/proxmox-release-bookworm\.gpg\] http://download\.proxmox\.com/debian/pve bookworm pve-no-subscription\n"""',
        '''debian_release = self._detect_debian_release()
        self.logger.info(f"Detected Debian release: {debian_release}")
        
        # For Trixie, use standard Debian kernels as Proxmox may not have Trixie repos yet
        if debian_release == 'trixie':
            # Ensure contrib is enabled for ZFS
            sources_list_path = self.chroot_path / "etc/apt/sources.list"
            if sources_list_path.exists():
                with open(sources_list_path, 'r') as f:
                    sources_content = f.read()
                
                if 'contrib' not in sources_content:
                    self.logger.info("Adding contrib to sources.list for ZFS support...")
                    lines = sources_content.split('\\n')
                    new_lines = []
                    for line in lines:
                        if line.strip() and not line.strip().startswith('#') and 'main' in line and 'contrib' not in line:
                            line = line.rstrip() + ' contrib non-free-firmware'
                        new_lines.append(line)
                    
                    with open(sources_list_path, 'w') as f:
                        f.write('\\n'.join(new_lines))
            
            # Skip Proxmox repos for Trixie
            return
        
        # For other releases, use Proxmox repos
        sources_list = f"""# Proxmox kernel repositories
deb [signed-by=/etc/apt/keyrings/proxmox-release-{debian_release}.gpg] http://download.proxmox.com/debian/pve {debian_release} pve-no-subscription
"""''',
        content
    )
    
    # Patch 3: Update kernel package selection for Trixie
    content = re.sub(
        r'kernel_image_pkg = "linux-image-amd64"',
        '''# Use release-specific kernel
            debian_release = self._detect_debian_release()
            if debian_release == 'trixie':
                # For Trixie, use the latest available kernel
                kernel_image_pkg = "linux-image-amd64"
                kernel_headers_pkg = "linux-headers-amd64"
                # Also install specific version headers for DKMS
                self._run_chroot_command(["apt-get", "install", "-y", "linux-headers-generic"])
            else:
                kernel_image_pkg = "linux-image-amd64"''',
        content
    )
    
    # Patch 4: Fix the GPG key download for appropriate release
    content = re.sub(
        r'"wget", "-qO", "/etc/apt/keyrings/proxmox-release-bookworm\.gpg",\s*"https://enterprise\.proxmox\.com/debian/proxmox-release-bookworm\.gpg"',
        f'"wget", "-qO", f"/etc/apt/keyrings/proxmox-release-{{debian_release}}.gpg", f"https://enterprise.proxmox.com/debian/proxmox-release-{{debian_release}}.gpg"',
        content
    )
    
    # Write the patched content
    with open(original_file, 'w') as f:
        f.write(content)
    
    print(f"Successfully patched {original_file}")
    print(f"Backup saved at: {backup_file}")
    
    return True

if __name__ == "__main__":
    try:
        create_patched_kernel_acquisition()
        print("\nKernel acquisition module patched for Trixie support!")
        print("\nKey changes:")
        print("1. Added Debian release detection")
        print("2. Updated repository configuration for detected release")
        print("3. Fixed kernel package selection for Trixie")
        print("4. Ensured contrib repository for ZFS support")
    except Exception as e:
        print(f"Error patching kernel acquisition module: {e}")
        exit(1)