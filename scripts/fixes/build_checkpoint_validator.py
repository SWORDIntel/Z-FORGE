#!/usr/bin/env python3
"""
Build Checkpoint Validator for Z-FORGE
Validates critical dependencies before proceeding with each build phase
"""

import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Tuple, Optional

class BuildCheckpointValidator:
    def __init__(self, chroot_path: str = "/tmp/zforge_workspace/chroot"):
        self.chroot_path = Path(chroot_path)
        
    def _run_chroot_command(self, cmd: List[str]) -> Tuple[int, str, str]:
        """Run command in chroot and return result"""
        full_cmd = ["chroot", str(self.chroot_path)] + cmd
        result = subprocess.run(full_cmd, capture_output=True, text=True)
        return result.returncode, result.stdout, result.stderr
        
    def validate_zfs_installation(self) -> Dict[str, any]:
        """Validate ZFS is properly installed"""
        print("🔍 Validating ZFS installation...")
        
        checks = {
            'zfs_command': False,
            'zpool_command': False,
            'zfs_dkms': False,
            'kernel_modules': False,
            'version': None
        }
        
        # Check ZFS commands exist
        ret_code, _, _ = self._run_chroot_command(["which", "zfs"])
        checks['zfs_command'] = ret_code == 0
        
        ret_code, _, _ = self._run_chroot_command(["which", "zpool"])
        checks['zpool_command'] = ret_code == 0
        
        # Check DKMS
        ret_code, stdout, _ = self._run_chroot_command(["dkms", "status"])
        checks['zfs_dkms'] = 'zfs' in stdout.lower()
        
        # Check version
        ret_code, stdout, _ = self._run_chroot_command(["zfs", "version"])
        if ret_code == 0:
            for line in stdout.split('\n'):
                if 'zfs-' in line.lower():
                    checks['version'] = line.strip()
                    break
        
        # Check kernel modules
        kernel_dirs = list((self.chroot_path / "lib/modules").glob("*/"))
        for kernel_dir in kernel_dirs:
            zfs_modules = list(kernel_dir.rglob("zfs.ko*"))
            if zfs_modules:
                checks['kernel_modules'] = True
                break
                
        return checks
        
    def validate_kernel_installation(self) -> Dict[str, any]:
        """Validate kernel is properly installed"""
        print("🔍 Validating kernel installation...")
        
        checks = {
            'vmlinuz_exists': False,
            'initrd_exists': False,
            'headers_installed': False,
            'modules_dir': False,
            'kernel_version': None
        }
        
        # Check for vmlinuz files
        boot_dir = self.chroot_path / "boot"
        vmlinuz_files = list(boot_dir.glob("vmlinuz-*"))
        checks['vmlinuz_exists'] = len(vmlinuz_files) > 0
        
        # Check for initrd files
        initrd_files = list(boot_dir.glob("initrd.img-*")) + list(boot_dir.glob("initramfs-*.img"))
        checks['initrd_exists'] = len(initrd_files) > 0
        
        # Get kernel version
        if vmlinuz_files:
            kernel_file = vmlinuz_files[0].name
            checks['kernel_version'] = kernel_file.replace('vmlinuz-', '')
            
            # Check for corresponding modules directory
            modules_dir = self.chroot_path / "lib/modules" / checks['kernel_version']
            checks['modules_dir'] = modules_dir.exists()
            
            # Check for headers
            headers_dir = modules_dir / "build"
            checks['headers_installed'] = headers_dir.exists()
            
        return checks
        
    def validate_dracut_configuration(self) -> Dict[str, any]:
        """Validate dracut is configured for ZFS"""
        print("🔍 Validating dracut configuration...")
        
        checks = {
            'dracut_installed': False,
            'zfs_module_config': False,
            'hostid_exists': False
        }
        
        # Check dracut is installed
        ret_code, _, _ = self._run_chroot_command(["which", "dracut"])
        checks['dracut_installed'] = ret_code == 0
        
        # Check ZFS dracut configuration
        zfs_conf = self.chroot_path / "etc/dracut.conf.d/zfs.conf"
        checks['zfs_module_config'] = zfs_conf.exists()
        
        # Check hostid
        hostid_file = self.chroot_path / "etc/hostid"
        checks['hostid_exists'] = hostid_file.exists()
        
        return checks
        
    def run_pre_zfs_checks(self) -> bool:
        """Run checks before ZFS installation"""
        print("🔍 Running pre-ZFS installation checks...")
        
        issues = []
        
        # Check chroot exists
        if not self.chroot_path.exists():
            issues.append(f"Chroot directory does not exist: {self.chroot_path}")
            
        # Check basic system is ready
        ret_code, _, _ = self._run_chroot_command(["apt-get", "--version"])
        if ret_code != 0:
            issues.append("APT is not functional in chroot")
            
        # Check build tools
        for tool in ["gcc", "make", "autoconf"]:
            ret_code, _, _ = self._run_chroot_command(["which", tool])
            if ret_code != 0:
                issues.append(f"Build tool missing: {tool}")
                
        if issues:
            print("❌ Pre-ZFS checks failed:")
            for issue in issues:
                print(f"   - {issue}")
            return False
            
        print("✅ Pre-ZFS checks passed")
        return True
        
    def run_post_zfs_checks(self) -> bool:
        """Run checks after ZFS installation"""
        print("🔍 Running post-ZFS installation validation...")
        
        zfs_checks = self.validate_zfs_installation()
        
        critical_failures = []
        warnings = []
        
        if not zfs_checks['zfs_command']:
            critical_failures.append("ZFS command not found")
        if not zfs_checks['zpool_command']:
            critical_failures.append("ZPool command not found")
            
        if not zfs_checks['zfs_dkms']:
            warnings.append("ZFS DKMS modules not detected")
        if not zfs_checks['kernel_modules']:
            warnings.append("ZFS kernel modules not found")
            
        # Print results
        if zfs_checks['version']:
            print(f"✅ ZFS version: {zfs_checks['version']}")
            
        if warnings:
            print("⚠️  Warnings:")
            for warning in warnings:
                print(f"   - {warning}")
                
        if critical_failures:
            print("❌ Critical failures:")
            for failure in critical_failures:
                print(f"   - {failure}")
            return False
            
        print("✅ Post-ZFS checks passed")
        return True
        
    def run_comprehensive_validation(self) -> Dict[str, bool]:
        """Run all validation checks"""
        print("🔍 Running comprehensive build validation...")
        
        results = {
            'zfs_validation': False,
            'kernel_validation': False,
            'dracut_validation': False
        }
        
        # Validate ZFS
        zfs_checks = self.validate_zfs_installation()
        results['zfs_validation'] = (
            zfs_checks['zfs_command'] and 
            zfs_checks['zpool_command']
        )
        
        # Validate kernel
        kernel_checks = self.validate_kernel_installation()
        results['kernel_validation'] = (
            kernel_checks['vmlinuz_exists'] and
            kernel_checks['modules_dir']
        )
        
        # Validate dracut
        dracut_checks = self.validate_dracut_configuration()
        results['dracut_validation'] = (
            dracut_checks['dracut_installed'] and
            dracut_checks['hostid_exists']
        )
        
        # Print summary
        print("\n=== Validation Summary ===")
        for check, passed in results.items():
            status = "✅ PASS" if passed else "❌ FAIL"
            print(f"{check:<20} {status}")
            
        all_passed = all(results.values())
        if all_passed:
            print("\n🎉 All validations passed!")
        else:
            print("\n⚠️  Some validations failed - build may not work correctly")
            
        return results

def main():
    chroot_path = sys.argv[1] if len(sys.argv) > 1 else "/tmp/zforge_workspace/chroot"
    validator = BuildCheckpointValidator(chroot_path)
    
    if len(sys.argv) > 2 and sys.argv[2] == "pre-zfs":
        success = validator.run_pre_zfs_checks()
    elif len(sys.argv) > 2 and sys.argv[2] == "post-zfs":
        success = validator.run_post_zfs_checks()
    else:
        results = validator.run_comprehensive_validation()
        success = all(results.values())
        
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()