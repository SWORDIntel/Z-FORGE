#!/usr/bin/env python3
# tests/validate_proxmox_install.py

"""Validate Proxmox VE installation"""

import subprocess
import sys
from pathlib import Path

def validate_proxmox_installation(chroot_path: Path) -> bool:
    """Validate Proxmox is correctly installed"""
    
    checks = []
    
    # Check Proxmox packages
    packages = ['proxmox-ve', 'pve-manager', 'pve-kernel-6.8']
    for pkg in packages:
        result = subprocess.run([
            'chroot', str(chroot_path),
            'dpkg', '-l', pkg
        ], capture_output=True)
        checks.append(('Package ' + pkg, result.returncode == 0))
    
    # Check services
    services = ['pvedaemon', 'pveproxy', 'pve-cluster']
    for svc in services:
        svc_file = chroot_path / f'etc/systemd/system/multi-user.target.wants/{svc}.service'
        checks.append((f'Service {svc}', svc_file.exists() or svc_file.is_symlink()))
    
    # Check ZFS datasets
    datasets = ['rpool/data', 'rpool/data/vm', 'rpool/data/ct']
    for ds in datasets:
        result = subprocess.run(['zfs', 'list', ds], capture_output=True)
        checks.append((f'Dataset {ds}', result.returncode == 0))
    
    # Print results
    all_passed = True
    for check, passed in checks:
        status = '✓' if passed else '✗'
        print(f'{status} {check}')
        if not passed:
            all_passed = False
    
    return all_passed

if __name__ == '__main__':
    if len(sys.argv) != 2:
        print("Usage: validate_proxmox_install.py <chroot_path>")
        sys.exit(1)
    
    chroot_path = Path(sys.argv[1])
    if validate_proxmox_installation(chroot_path):
        print("\n✓ All validation checks passed!")
        sys.exit(0)
    else:
        print("\n✗ Some validation checks failed!")
        sys.exit(1)
