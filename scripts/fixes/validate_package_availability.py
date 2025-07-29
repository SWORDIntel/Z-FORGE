#!/usr/bin/env python3
"""
Package Availability Validator for Z-FORGE
Validates that all required packages exist before attempting installation
"""

import subprocess
import sys
from pathlib import Path
from typing import List, Dict, Tuple

class PackageValidator:
    def __init__(self, chroot_path: str = "/tmp/zforge_workspace/chroot"):
        self.chroot_path = Path(chroot_path)
        
    def _run_chroot_command(self, cmd: List[str]) -> Tuple[int, str, str]:
        """Run command in chroot and return result"""
        full_cmd = ["chroot", str(self.chroot_path)] + cmd
        result = subprocess.run(full_cmd, capture_output=True, text=True)
        return result.returncode, result.stdout, result.stderr
    
    def check_package_exists(self, package: str) -> Dict[str, any]:
        """Check if a package exists in repositories"""
        print(f"Checking package: {package}")
        
        # Check with apt-cache show
        ret_code, stdout, stderr = self._run_chroot_command([
            "apt-cache", "show", package
        ])
        
        if ret_code == 0:
            # Parse version info
            version = ""
            for line in stdout.split('\n'):
                if line.startswith('Version:'):
                    version = line.split(':', 1)[1].strip()
                    break
                    
            return {
                'exists': True,
                'package': package,
                'version': version,
                'source': 'repository'
            }
        
        # Check if package is virtual or has alternatives
        ret_code, stdout, stderr = self._run_chroot_command([
            "apt-cache", "search", f"^{package}$"
        ])
        
        if ret_code == 0 and stdout.strip():
            return {
                'exists': True,
                'package': package,
                'version': 'virtual/alternative',
                'source': 'search_match'
            }
            
        return {
            'exists': False,
            'package': package,
            'error': stderr
        }
    
    def find_zfs_packages(self) -> List[Dict]:
        """Find available ZFS packages"""
        zfs_packages = [
            "zfsutils-linux",
            "zfs-dkms", 
            "zfs-zed",
            "libzfs4linux",
            "libzpool5linux",
            "libnvpair3linux",
            "libuutil3linux",
            "zfs-initramfs",
            "zfs-dracut"
        ]
        
        results = []
        for package in zfs_packages:
            result = self.check_package_exists(package)
            results.append(result)
            
        return results
    
    def find_kernel_packages(self) -> List[Dict]:
        """Find available kernel packages"""
        # Get available kernel versions
        ret_code, stdout, stderr = self._run_chroot_command([
            "apt-cache", "search", "linux-image-.*-amd64"
        ])
        
        kernel_packages = []
        if ret_code == 0:
            for line in stdout.split('\n'):
                if 'linux-image-' in line and '-amd64' in line:
                    package = line.split(' -')[0]
                    result = self.check_package_exists(package)
                    if result['exists']:
                        kernel_packages.append(result)
                        
        return kernel_packages
    
    def generate_report(self) -> Dict:
        """Generate comprehensive package availability report"""
        print("=== Z-FORGE Package Availability Report ===\n")
        
        # Update package lists first
        print("Updating package lists...")
        self._run_chroot_command(["apt-get", "update"])
        
        report = {
            'zfs_packages': self.find_zfs_packages(),
            'kernel_packages': self.find_kernel_packages()
        }
        
        # Print ZFS package status
        print("\nZFS Package Availability:")
        print("-" * 50)
        for pkg in report['zfs_packages']:
            status = "✅ AVAILABLE" if pkg['exists'] else "❌ MISSING"
            version = f" (v{pkg['version']})" if pkg.get('version') else ""
            print(f"{pkg['package']:<20} {status}{version}")
        
        # Print kernel package status  
        print(f"\nAvailable Kernel Packages: {len(report['kernel_packages'])}")
        print("-" * 50)
        for pkg in report['kernel_packages'][:5]:  # Show first 5
            print(f"{pkg['package']:<30} v{pkg['version']}")
        
        # Recommendations
        available_zfs = [p for p in report['zfs_packages'] if p['exists']]
        missing_zfs = [p for p in report['zfs_packages'] if not p['exists']]
        
        print(f"\nSummary:")
        print(f"ZFS packages available: {len(available_zfs)}/{len(report['zfs_packages'])}")
        print(f"Kernel packages available: {len(report['kernel_packages'])}")
        
        if missing_zfs:
            print(f"\n⚠️  Missing ZFS packages:")
            for pkg in missing_zfs:
                print(f"   - {pkg['package']}")
                
        return report

def main():
    if len(sys.argv) > 1:
        chroot_path = sys.argv[1]
    else:
        chroot_path = "/tmp/zforge_workspace/chroot"
    
    validator = PackageValidator(chroot_path)
    report = validator.generate_report()
    
    # Exit with error if critical packages missing
    available_zfs = [p for p in report['zfs_packages'] if p['exists']]
    if len(available_zfs) < 2:  # Need at least zfsutils-linux + one other
        print("\n🚨 CRITICAL: Insufficient ZFS packages available")
        sys.exit(1)
    
    print("\n✅ Package validation completed successfully")

if __name__ == "__main__":
    main()