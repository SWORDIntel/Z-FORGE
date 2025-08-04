#!/usr/bin/env python3
"""
Z-FORGE Build Recovery Tool
Automatic recovery from common build failures
"""

import os
import sys
import subprocess
import shutil
import time
import signal
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple

class BuildRecoveryTool:
    """Automatic recovery from build failures"""
    
    def __init__(self, workspace: str = "/home/john/zforge_workspace"):
        self.workspace = Path(workspace)
        self.chroot = self.workspace / "chroot"
        self.project_root = Path("/opt/github/Z-FORGE")
        self.recovery_log = []
        self.sudo_password = "1786"  # From user context
        
    def recover_from_failure(self, error_type: str, context: Dict = None) -> bool:
        """Main recovery dispatcher"""
        print(f"\n🔧 Attempting recovery for: {error_type}")
        
        recovery_methods = {
            "dpkg_error": self.fix_dpkg_errors,
            "apt_lock": self.fix_apt_locks,
            "broken_packages": self.fix_broken_packages,
            "zfs_install": self.fix_zfs_installation,
            "kernel_install": self.fix_kernel_installation,
            "network_error": self.fix_network_issues,
            "disk_space": self.fix_disk_space,
            "mount_error": self.fix_mount_issues,
            "chroot_error": self.fix_chroot_environment,
            "initramfs_error": self.fix_initramfs_generation
        }
        
        if error_type in recovery_methods:
            try:
                success = recovery_methods[error_type](context)
                if success:
                    self.recovery_log.append(f"✅ Successfully recovered from {error_type}")
                    print(f"✅ Recovery successful for {error_type}")
                else:
                    self.recovery_log.append(f"❌ Failed to recover from {error_type}")
                    print(f"❌ Recovery failed for {error_type}")
                return success
            except Exception as e:
                self.recovery_log.append(f"❌ Recovery error for {error_type}: {e}")
                print(f"❌ Recovery error: {e}")
                return False
        else:
            print(f"⚠️  No recovery method for {error_type}")
            return False
    
    def fix_dpkg_errors(self, context: Dict = None) -> bool:
        """Fix dpkg errors and broken packages"""
        print("  Fixing dpkg errors...")
        
        steps = [
            # Step 1: Configure pending packages
            ("Configuring pending packages", [
                "sudo", "-S", "dpkg", "--configure", "-a"
            ]),
            
            # Step 2: Fix broken packages
            ("Fixing broken packages", [
                "sudo", "-S", "apt-get", "install", "-f", "-y"
            ]),
            
            # Step 3: Clean package cache
            ("Cleaning package cache", [
                "sudo", "-S", "apt-get", "clean"
            ]),
            
            # Step 4: Update package lists
            ("Updating package lists", [
                "sudo", "-S", "apt-get", "update"
            ])
        ]
        
        for step_name, cmd in steps:
            print(f"    • {step_name}")
            if not self._run_sudo_command(cmd):
                return False
                
        return True
    
    def fix_apt_locks(self, context: Dict = None) -> bool:
        """Remove APT lock files safely"""
        print("  Removing APT locks...")
        
        lock_files = [
            "/var/lib/dpkg/lock",
            "/var/lib/dpkg/lock-frontend", 
            "/var/lib/apt/lists/lock",
            "/var/cache/apt/archives/lock"
        ]
        
        # First check if any apt/dpkg processes are running
        print("    • Checking for running APT/dpkg processes")
        try:
            result = subprocess.run(["pgrep", "-f", "apt|dpkg"], 
                                  capture_output=True, text=True)
            if result.stdout.strip():
                print("    • Waiting for APT/dpkg processes to complete...")
                time.sleep(10)
                
                # Check again
                result = subprocess.run(["pgrep", "-f", "apt|dpkg"],
                                      capture_output=True, text=True)
                if result.stdout.strip():
                    # Force kill if still running
                    print("    • Force stopping APT/dpkg processes")
                    self._run_sudo_command(["sudo", "-S", "killall", "-9", "apt-get", "dpkg"])
                    time.sleep(2)
        except:
            pass
        
        # Remove lock files
        for lock_file in lock_files:
            if Path(lock_file).exists():
                print(f"    • Removing {lock_file}")
                self._run_sudo_command(["sudo", "-S", "rm", "-f", lock_file])
        
        # Reconfigure dpkg
        print("    • Reconfiguring dpkg")
        return self._run_sudo_command(["sudo", "-S", "dpkg", "--configure", "-a"])
    
    def fix_broken_packages(self, context: Dict = None) -> bool:
        """Fix broken package dependencies"""
        print("  Fixing broken packages...")
        
        # Try multiple approaches
        approaches = [
            # Approach 1: Standard fix
            ("Standard package fix", [
                "sudo", "-S", "apt-get", "install", "-f", "-y"
            ]),
            
            # Approach 2: Remove problematic packages
            ("Remove problematic packages", [
                "sudo", "-S", "apt-get", "autoremove", "-y"
            ]),
            
            # Approach 3: Update and upgrade
            ("Update and upgrade", [
                "sudo", "-S", "apt-get", "update", "&&",
                "sudo", "-S", "apt-get", "upgrade", "-y"
            ])
        ]
        
        for approach_name, cmd in approaches:
            print(f"    • Trying: {approach_name}")
            if self._run_sudo_command(cmd):
                return True
                
        return False
    
    def fix_zfs_installation(self, context: Dict = None) -> bool:
        """Fix ZFS installation issues"""
        print("  Fixing ZFS installation...")
        
        # Step 1: Install kernel headers
        print("    • Installing kernel headers")
        kernel_version = os.uname().release
        if not self._run_sudo_command([
            "sudo", "-S", "apt-get", "install", "-y",
            f"linux-headers-{kernel_version}", "linux-headers-generic"
        ]):
            print("    • Using generic headers")
            self._run_sudo_command([
                "sudo", "-S", "apt-get", "install", "-y", 
                "linux-headers-amd64"
            ])
        
        # Step 2: Install DKMS
        print("    • Installing DKMS")
        self._run_sudo_command([
            "sudo", "-S", "apt-get", "install", "-y", "dkms"
        ])
        
        # Step 3: Add contrib/non-free repos if needed
        print("    • Ensuring contrib/non-free repositories")
        sources_file = Path("/etc/apt/sources.list")
        if sources_file.exists():
            content = sources_file.read_text()
            if "contrib" not in content or "non-free" not in content:
                # Add contrib non-free to sources
                self._run_sudo_command([
                    "sudo", "-S", "sed", "-i",
                    "s/main/main contrib non-free/g",
                    "/etc/apt/sources.list"
                ])
                self._run_sudo_command(["sudo", "-S", "apt-get", "update"])
        
        # Step 4: Try installing ZFS
        print("    • Installing ZFS packages")
        return self._run_sudo_command([
            "sudo", "-S", "apt-get", "install", "-y",
            "zfsutils-linux", "zfs-dkms"
        ])
    
    def fix_kernel_installation(self, context: Dict = None) -> bool:
        """Fix kernel installation issues"""
        print("  Fixing kernel installation...")
        
        # Step 1: Remove initramfs-tools conflicts
        print("    • Removing initramfs-tools")
        self._run_sudo_command([
            "sudo", "-S", "apt-get", "remove", "-y",
            "initramfs-tools", "initramfs-tools-core"
        ])
        
        # Step 2: Install dracut
        print("    • Installing dracut")
        self._run_sudo_command([
            "sudo", "-S", "apt-get", "install", "-y",
            "dracut", "dracut-core", "dracut-network"
        ])
        
        # Step 3: Try different kernel package names
        print("    • Installing kernel packages")
        kernel_packages = [
            ["linux-image-amd64", "linux-headers-amd64"],
            ["linux-image-generic", "linux-headers-generic"],
            ["linux-image-6.14.8-1", "linux-headers-6.14.8-1"]
        ]
        
        for packages in kernel_packages:
            print(f"    • Trying: {packages}")
            if self._run_sudo_command([
                "sudo", "-S", "apt-get", "install", "-y"
            ] + packages):
                return True
                
        return False
    
    def fix_network_issues(self, context: Dict = None) -> bool:
        """Fix network connectivity issues"""
        print("  Fixing network issues...")
        
        # Step 1: Restart network service
        print("    • Restarting network services")
        self._run_sudo_command([
            "sudo", "-S", "systemctl", "restart", "systemd-resolved"
        ])
        
        # Step 2: Check DNS
        print("    • Checking DNS configuration")
        resolv_conf = Path("/etc/resolv.conf")
        if not resolv_conf.exists() or resolv_conf.stat().st_size == 0:
            print("    • Setting up DNS")
            self._run_sudo_command([
                "sudo", "-S", "sh", "-c",
                "echo 'nameserver 8.8.8.8\\nnameserver 8.8.4.4' > /etc/resolv.conf"
            ])
        
        # Step 3: Test connectivity
        print("    • Testing connectivity")
        result = subprocess.run(["ping", "-c", "1", "-W", "5", "8.8.8.8"],
                              capture_output=True)
        return result.returncode == 0
    
    def fix_disk_space(self, context: Dict = None) -> bool:
        """Free up disk space"""
        print("  Freeing disk space...")
        
        # Step 1: Clean APT cache
        print("    • Cleaning APT cache")
        self._run_sudo_command(["sudo", "-S", "apt-get", "clean"])
        self._run_sudo_command(["sudo", "-S", "apt-get", "autoclean"])
        
        # Step 2: Remove old kernels
        print("    • Removing old kernels")
        self._run_sudo_command(["sudo", "-S", "apt-get", "autoremove", "--purge", "-y"])
        
        # Step 3: Clean workspace if exists
        if self.workspace.exists():
            print("    • Cleaning workspace")
            # Remove old chroot if exists
            old_chroot = self.workspace / "chroot.old"
            if old_chroot.exists():
                print("    • Removing old chroot backup")
                self._run_sudo_command(["sudo", "-S", "rm", "-rf", str(old_chroot)])
            
            # Clean build artifacts
            for pattern in ["*.log", "*.tmp", "*.iso"]:
                for file in self.workspace.glob(pattern):
                    print(f"    • Removing {file.name}")
                    file.unlink()
        
        # Step 4: Check available space
        stat = os.statvfs(self.workspace if self.workspace.exists() else "/")
        free_gb = (stat.f_bavail * stat.f_frsize) / (1024**3)
        print(f"    • Free space: {free_gb:.1f}GB")
        
        return free_gb > 10  # Need at least 10GB
    
    def fix_mount_issues(self, context: Dict = None) -> bool:
        """Fix mount-related issues"""
        print("  Fixing mount issues...")
        
        if not self.chroot.exists():
            print("    • Chroot doesn't exist, nothing to unmount")
            return True
        
        # Step 1: Check what's mounted
        print("    • Checking mounts")
        result = subprocess.run(["mount"], capture_output=True, text=True)
        chroot_mounts = [line for line in result.stdout.split("\n") 
                        if str(self.chroot) in line]
        
        if not chroot_mounts:
            print("    • No mounts to fix")
            return True
        
        # Step 2: Kill processes using the mounts
        print("    • Checking for processes using mounts")
        self._run_sudo_command([
            "sudo", "-S", "fuser", "-km", str(self.chroot)
        ])
        time.sleep(2)
        
        # Step 3: Unmount in correct order
        mount_points = [
            self.chroot / "dev/pts",
            self.chroot / "dev",
            self.chroot / "proc",
            self.chroot / "sys",
            self.chroot / "run"
        ]
        
        for mount_point in mount_points:
            if mount_point.exists():
                print(f"    • Unmounting {mount_point}")
                self._run_sudo_command([
                    "sudo", "-S", "umount", "-l", str(mount_point)
                ])
        
        return True
    
    def fix_chroot_environment(self, context: Dict = None) -> bool:
        """Fix or rebuild chroot environment"""
        print("  Fixing chroot environment...")
        
        if not self.chroot.exists():
            print("    • Chroot doesn't exist, will be created by build")
            return True
        
        # Step 1: Check if chroot is valid
        required_dirs = ["bin", "etc", "lib", "usr", "var"]
        missing = [d for d in required_dirs if not (self.chroot / d).exists()]
        
        if missing:
            print(f"    • Chroot is corrupted, missing: {missing}")
            print("    • Backing up and removing corrupted chroot")
            
            # Backup if space allows
            backup = self.workspace / f"chroot.backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            try:
                shutil.move(str(self.chroot), str(backup))
                print(f"    • Backed up to {backup.name}")
            except:
                # Force remove if can't backup
                self._run_sudo_command(["sudo", "-S", "rm", "-rf", str(self.chroot)])
                print("    • Removed corrupted chroot")
            
            return True
        
        # Step 2: Fix permissions
        print("    • Fixing chroot permissions")
        self._run_sudo_command([
            "sudo", "-S", "chown", "-R", "root:root", str(self.chroot)
        ])
        
        # Step 3: Ensure required mounts
        print("    • Setting up required mounts")
        mounts = [
            ("proc", "proc", self.chroot / "proc"),
            ("sysfs", "sys", self.chroot / "sys"),
            ("devtmpfs", "dev", self.chroot / "dev")
        ]
        
        for fs_type, source, target in mounts:
            if not target.exists():
                target.mkdir(parents=True, exist_ok=True)
            
            # Check if already mounted
            result = subprocess.run(["mount"], capture_output=True, text=True)
            if str(target) not in result.stdout:
                print(f"    • Mounting {source} to {target}")
                self._run_sudo_command([
                    "sudo", "-S", "mount", "-t", fs_type, source, str(target)
                ])
        
        return True
    
    def fix_initramfs_generation(self, context: Dict = None) -> bool:
        """Fix initramfs generation issues"""
        print("  Fixing initramfs generation...")
        
        # Step 1: Ensure dracut is installed
        print("    • Ensuring dracut is installed")
        if not self._run_sudo_command([
            "sudo", "-S", "apt-get", "install", "-y",
            "dracut", "dracut-core", "dracut-network"
        ]):
            return False
        
        # Step 2: Remove initramfs-tools
        print("    • Removing initramfs-tools")
        self._run_sudo_command([
            "sudo", "-S", "apt-get", "remove", "--purge", "-y",
            "initramfs-tools", "initramfs-tools-core"
        ])
        
        # Step 3: Configure dracut
        print("    • Configuring dracut")
        dracut_conf_dir = Path("/etc/dracut.conf.d")
        if not dracut_conf_dir.exists():
            self._run_sudo_command([
                "sudo", "-S", "mkdir", "-p", str(dracut_conf_dir)
            ])
        
        # Write basic dracut config
        config_content = """# Z-FORGE dracut configuration
compress="zstd"
hostonly="no"
early_microcode="yes"
add_dracutmodules+=" base systemd kernel-modules rootfs-block terminfo udev-rules "
"""
        
        config_file = dracut_conf_dir / "zforge.conf"
        self._run_sudo_command([
            "sudo", "-S", "sh", "-c",
            f"echo '{config_content}' > {config_file}"
        ])
        
        # Step 4: Regenerate initramfs
        print("    • Regenerating initramfs")
        kernel_version = os.uname().release
        return self._run_sudo_command([
            "sudo", "-S", "dracut", "-f", 
            f"/boot/initrd.img-{kernel_version}", kernel_version
        ])
    
    def _run_sudo_command(self, cmd: List[str]) -> bool:
        """Run command with sudo"""
        try:
            # Add password to stdin for sudo -S
            if "sudo" in cmd and "-S" in cmd:
                result = subprocess.run(
                    cmd,
                    input=f"{self.sudo_password}\n",
                    text=True,
                    capture_output=True,
                    timeout=60
                )
            else:
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    timeout=60
                )
            
            return result.returncode == 0
        except subprocess.TimeoutExpired:
            print(f"      ⚠️  Command timed out")
            return False
        except Exception as e:
            print(f"      ⚠️  Command failed: {e}")
            return False
    
    def auto_recover_from_log(self, log_file: Path) -> bool:
        """Analyze log and automatically recover"""
        print(f"\n📋 Analyzing log file: {log_file.name}")
        
        if not log_file.exists():
            print("  ❌ Log file not found")
            return False
        
        # Read log content
        try:
            with open(log_file, 'r') as f:
                content = f.read()
        except:
            # Try with sudo
            result = subprocess.run(
                ["sudo", "-S", "cat", str(log_file)],
                input=f"{self.sudo_password}\n",
                text=True,
                capture_output=True
            )
            if result.returncode != 0:
                print("  ❌ Cannot read log file")
                return False
            content = result.stdout
        
        # Detect error patterns and recover
        recoveries_attempted = []
        
        # Check for various error patterns
        error_patterns = {
            "dpkg returned an error code": "dpkg_error",
            "Could not get lock": "apt_lock",
            "Unable to acquire the dpkg frontend lock": "apt_lock",
            "broken packages": "broken_packages",
            "Failed to install.*zfs": "zfs_install",
            "Kernel acquisition failed": "kernel_install",
            "Network is unreachable": "network_error",
            "No space left on device": "disk_space",
            "target is busy": "mount_error",
            "chroot.*failed": "chroot_error",
            "dracut.*failed": "initramfs_error"
        }
        
        for pattern, error_type in error_patterns.items():
            if pattern in content.lower():
                if error_type not in recoveries_attempted:
                    print(f"  🔍 Detected: {error_type}")
                    if self.recover_from_failure(error_type):
                        recoveries_attempted.append(error_type)
        
        if recoveries_attempted:
            print(f"\n✅ Attempted recovery for {len(recoveries_attempted)} issues")
            return True
        else:
            print("  ℹ️  No recoverable errors detected")
            return False
    
    def generate_recovery_report(self) -> str:
        """Generate recovery report"""
        report = []
        report.append("=" * 60)
        report.append("BUILD RECOVERY REPORT")
        report.append("=" * 60)
        report.append(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append(f"Recovery Actions: {len(self.recovery_log)}")
        report.append("")
        
        for action in self.recovery_log:
            report.append(f"  {action}")
        
        report.append("")
        report.append("=" * 60)
        
        return "\n".join(report)

def main():
    """Main recovery function"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Z-FORGE Build Recovery Tool")
    parser.add_argument("--log", help="Log file to analyze and recover from")
    parser.add_argument("--error", help="Specific error type to recover from")
    parser.add_argument("--auto", action="store_true", 
                       help="Automatically fix common issues")
    
    args = parser.parse_args()
    
    tool = BuildRecoveryTool()
    
    if args.log:
        # Analyze and recover from log
        log_file = Path(args.log)
        success = tool.auto_recover_from_log(log_file)
    elif args.error:
        # Recover from specific error
        success = tool.recover_from_failure(args.error)
    elif args.auto:
        # Auto fix common issues
        print("🔧 Running automatic recovery for common issues...")
        tool.fix_apt_locks()
        tool.fix_dpkg_errors()
        tool.fix_disk_space()
        tool.fix_mount_issues()
        success = True
    else:
        # Interactive mode
        print("Z-FORGE Build Recovery Tool")
        print("=" * 40)
        print("\nAvailable recovery options:")
        print("1. Fix dpkg/APT errors")
        print("2. Fix APT lock files")
        print("3. Fix broken packages")
        print("4. Fix ZFS installation")
        print("5. Fix kernel installation")
        print("6. Fix network issues")
        print("7. Fix disk space")
        print("8. Fix mount issues")
        print("9. Fix chroot environment")
        print("10. Fix initramfs generation")
        print("0. Run all fixes")
        
        choice = input("\nSelect option (0-10): ").strip()
        
        if choice == "0":
            for error_type in ["apt_lock", "dpkg_error", "broken_packages",
                              "disk_space", "mount_error", "chroot_error"]:
                tool.recover_from_failure(error_type)
            success = True
        elif choice == "1":
            success = tool.recover_from_failure("dpkg_error")
        elif choice == "2":
            success = tool.recover_from_failure("apt_lock")
        elif choice == "3":
            success = tool.recover_from_failure("broken_packages")
        elif choice == "4":
            success = tool.recover_from_failure("zfs_install")
        elif choice == "5":
            success = tool.recover_from_failure("kernel_install")
        elif choice == "6":
            success = tool.recover_from_failure("network_error")
        elif choice == "7":
            success = tool.recover_from_failure("disk_space")
        elif choice == "8":
            success = tool.recover_from_failure("mount_error")
        elif choice == "9":
            success = tool.recover_from_failure("chroot_error")
        elif choice == "10":
            success = tool.recover_from_failure("initramfs_error")
        else:
            print("Invalid option")
            success = False
    
    # Print report
    print(tool.generate_recovery_report())
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())