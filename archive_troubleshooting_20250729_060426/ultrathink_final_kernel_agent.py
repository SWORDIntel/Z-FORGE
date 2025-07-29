#!/usr/bin/env python3
"""
UltraThink Final Kernel Agent - Handles version mismatch issues

This agent specifically targets the kernel version naming discrepancy
where APT shows 6.12.38-1 but the actual package is 6.12.38+deb13-amd64
"""

import subprocess
import logging
import sys
from pathlib import Path
from datetime import datetime

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - [FinalKernelAgent] %(levelname)s - %(message)s'
)
logger = logging.getLogger()

class FinalKernelAgent:
    def __init__(self):
        self.chroot = Path("/tmp/zforge_workspace/chroot")
        self.log_file = f"/opt/github/Z-FORGE/final_kernel_agent_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        
    def run_cmd(self, cmd, check=False):
        """Run command and return result"""
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=check)
            return result
        except subprocess.CalledProcessError as e:
            logger.error(f"Command failed: {' '.join(cmd)}")
            return e
            
    def chroot_cmd(self, cmd, check=False):
        """Run command in chroot"""
        full_cmd = ['sudo', 'chroot', str(self.chroot)] + cmd
        return self.run_cmd(full_cmd, check)
        
    def detect_kernel_issue(self):
        """Analyze the specific kernel version mismatch"""
        logger.info("=== Analyzing Kernel Version Mismatch ===")
        
        # Check metapackage policy
        result = self.chroot_cmd(['apt-cache', 'policy', 'linux-image-amd64'])
        if result.returncode == 0:
            logger.info("Metapackage policy:")
            for line in result.stdout.split('\n')[:10]:
                logger.info(f"  {line}")
                
        # Check what's actually installed
        result = self.chroot_cmd(['dpkg', '-l'])
        if result.returncode == 0:
            installed_kernels = []
            for line in result.stdout.split('\n'):
                if 'linux-image-' in line and line.startswith('ii'):
                    installed_kernels.append(line.split()[1])
            
            logger.info(f"Actually installed kernels: {installed_kernels}")
            
        # Check what packages are available with exact names
        result = self.chroot_cmd(['apt-cache', 'search', '^linux-image-6.12'])
        if result.returncode == 0:
            available_612 = []
            for line in result.stdout.split('\n'):
                if line and 'linux-image-6.12' in line:
                    pkg_name = line.split(' - ')[0]
                    available_612.append(pkg_name)
            
            logger.info(f"Available 6.12 kernels: {available_612[:10]}")
            return available_612
            
        return []
        
    def force_install_specific_kernel(self, kernel_packages):
        """Force install the exact kernel packages"""
        logger.info("=== Force Installing Specific Kernel ===")
        
        # Target the exact deb13 kernel
        target_kernels = [pkg for pkg in kernel_packages if '+deb13-amd64' in pkg and not 'unsigned' in pkg]
        
        if not target_kernels:
            logger.error("No deb13 kernels found!")
            return False
            
        target_kernel = target_kernels[0]  # Take the first one
        target_version = target_kernel.replace('linux-image-', '')
        target_headers = f"linux-headers-{target_version}"
        
        logger.info(f"Target kernel: {target_kernel}")
        logger.info(f"Target headers: {target_headers}")
        
        # Remove any existing kernel packages that might conflict
        logger.info("Removing potentially conflicting packages...")
        self.chroot_cmd(['apt-get', 'remove', '-y', 'linux-image-amd64', 'linux-headers-amd64'], check=False)
        
        # Install the specific kernel and headers
        logger.info(f"Installing {target_kernel} and {target_headers}...")
        result = self.chroot_cmd([
            'apt-get', 'install', '-y', '--no-install-recommends',
            target_kernel, target_headers, 'build-essential', 'dkms'
        ])
        
        if result.returncode == 0:
            logger.info("SUCCESS: Specific kernel installed!")
            
            # Now install the metapackages to maintain system consistency
            logger.info("Installing metapackages for future updates...")
            self.chroot_cmd(['apt-get', 'install', '-y', 'linux-image-amd64', 'linux-headers-amd64'], check=False)
            
            return True
        else:
            logger.error(f"Failed to install specific kernel: {result.stderr}")
            
            # Try without headers if that was the issue
            logger.info("Retrying without headers...")
            result = self.chroot_cmd(['apt-get', 'install', '-y', '--no-install-recommends', target_kernel])
            
            if result.returncode == 0:
                logger.info("Kernel installed without headers, trying to install headers separately...")
                self.chroot_cmd(['apt-get', 'install', '-y', target_headers], check=False)
                return True
                
        return False
        
    def verify_kernel_installation(self):
        """Verify that a 6.12+ kernel is actually installed"""
        logger.info("=== Final Verification ===")
        
        # Check for any 6.12+ kernel
        result = self.chroot_cmd(['dpkg', '-l'])
        if result.returncode == 0:
            for line in result.stdout.split('\n'):
                if line.startswith('ii') and 'linux-image-6.1' in line:
                    # Check if it's 6.12 or higher
                    parts = line.split()
                    if len(parts) > 1:
                        pkg_name = parts[1]
                        if 'linux-image-6.12' in pkg_name or any(f'linux-image-6.{v}' in pkg_name for v in range(12, 20)):
                            logger.info(f"✓ SUCCESS: Found kernel {pkg_name}")
                            return True
                            
        logger.error("✗ FAILED: No 6.12+ kernel found")
        return False
        
    def run(self):
        """Main execution"""
        logger.info("🤖 UltraThink Final Kernel Agent Starting")
        logger.info("Target: Fix kernel version mismatch and force install 6.12+")
        
        try:
            # Phase 1: Detect the issue
            available_kernels = self.detect_kernel_issue()
            
            if not available_kernels:
                logger.error("No 6.12 kernels available!")
                return False
                
            # Phase 2: Force install specific kernel
            success = self.force_install_specific_kernel(available_kernels)
            
            if not success:
                logger.error("Failed to install kernel")
                return False
                
            # Phase 3: Verify
            verified = self.verify_kernel_installation()
            
            if verified:
                logger.info("🎉 SUCCESS: Final Kernel Agent completed successfully!")
                logger.info("✅ Kernel 6.12+ is now properly installed")
                return True
            else:
                logger.error("💥 FAILED: Verification failed")
                return False
                
        except Exception as e:
            logger.error(f"Fatal error: {e}")
            import traceback
            traceback.print_exc()
            return False

def main():
    print("🤖 UltraThink Final Kernel Agent")
    print("Targeting kernel version mismatch issue...")
    print()
    
    agent = FinalKernelAgent()
    success = agent.run()
    
    if success:
        print("\n✅ SUCCESS: Kernel issue resolved!")
        sys.exit(0)
    else:
        print("\n❌ FAILED: Manual intervention still required")
        print("\nTry this manual approach:")
        print("sudo chroot /tmp/zforge_workspace/chroot apt-get install linux-image-6.12.38+deb13-amd64")
        sys.exit(1)

if __name__ == "__main__":
    main()