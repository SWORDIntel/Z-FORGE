#!/usr/bin/env python3
"""
Fix LiveEnvironment package installation issues
Diagnoses and repairs repository configuration in chroot
"""

import subprocess
import sys
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def check_chroot_repos(chroot_path):
    """Check repository configuration in chroot"""
    logger.info("Checking chroot repository configuration...")
    
    sources_list = chroot_path / "etc/apt/sources.list"
    sources_d = chroot_path / "etc/apt/sources.list.d"
    
    logger.info(f"Sources list: {sources_list}")
    if sources_list.exists():
        with open(sources_list) as f:
            logger.info("Current sources.list:")
            for line_num, line in enumerate(f, 1):
                logger.info(f"  {line_num}: {line.strip()}")
    else:
        logger.warning("sources.list does not exist!")
    
    logger.info(f"Sources.list.d directory: {sources_d}")
    if sources_d.exists():
        for file in sources_d.glob("*.list"):
            logger.info(f"Additional source: {file.name}")
            with open(file) as f:
                for line in f:
                    if line.strip() and not line.startswith('#'):
                        logger.info(f"  {line.strip()}")

def fix_chroot_repos(chroot_path):
    """Fix repository configuration in chroot"""
    logger.info("Fixing chroot repository configuration...")
    
    # Create proper sources.list
    sources_content = """# Debian Trixie Main Sources
deb http://deb.debian.org/debian trixie main contrib non-free-firmware
deb-src http://deb.debian.org/debian trixie main contrib non-free-firmware

# Debian Trixie Security
deb http://security.debian.org/debian-security trixie-security main contrib non-free-firmware
deb-src http://security.debian.org/debian-security trixie-security main contrib non-free-firmware

# Debian Bookworm (fallback for missing packages)
deb http://deb.debian.org/debian bookworm main contrib non-free-firmware
deb http://deb.debian.org/debian bookworm-backports main contrib non-free-firmware
"""
    
    sources_list = chroot_path / "etc/apt/sources.list"
    logger.info(f"Writing new sources.list to {sources_list}")
    with open(sources_list, 'w') as f:
        f.write(sources_content)
    
    # Create APT preferences to prefer trixie
    preferences_content = """# Prefer trixie packages
Package: *
Pin: release n=trixie
Pin-Priority: 900

# Allow bookworm as fallback
Package: *
Pin: release n=bookworm
Pin-Priority: 500

# Allow bookworm-backports
Package: *
Pin: release n=bookworm-backports
Pin-Priority: 400
"""
    
    preferences_file = chroot_path / "etc/apt/preferences.d/01-release-priorities"
    logger.info(f"Writing APT preferences to {preferences_file}")
    preferences_file.parent.mkdir(parents=True, exist_ok=True)
    with open(preferences_file, 'w') as f:
        f.write(preferences_content)

def test_package_availability(chroot_path):
    """Test if key packages are available"""
    logger.info("Testing package availability...")
    
    # Update package lists first
    logger.info("Updating package lists...")
    result = subprocess.run(
        ["chroot", str(chroot_path), "apt-get", "update"],
        capture_output=True,
        text=True
    )
    
    if result.returncode != 0:
        logger.error(f"Package list update failed: {result.stderr}")
        return False
    
    # Test key packages
    test_packages = [
        'live-boot',
        'systemd-sysv', 
        'network-manager',
        'grub-common',
        'util-linux'
    ]
    
    available_packages = []
    missing_packages = []
    
    for package in test_packages:
        result = subprocess.run(
            ["chroot", str(chroot_path), "apt-cache", "show", package],
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            available_packages.append(package)
            logger.info(f"✅ {package} - available")
        else:
            missing_packages.append(package)
            logger.warning(f"❌ {package} - not available")
    
    logger.info(f"Available: {len(available_packages)}, Missing: {len(missing_packages)}")
    return len(missing_packages) == 0

def create_minimal_package_list():
    """Create a minimal package list that should work"""
    minimal_packages = [
        # Absolutely essential
        'systemd',
        'systemd-sysv',
        'util-linux',
        'kmod',
        'udev',
        
        # Basic networking (if available)
        'isc-dhcp-client',
        'iputils-ping',
        'wget',
        'curl',
        
        # Basic filesystem tools
        'e2fsprogs',
        'dosfstools',
        
        # Basic bootloader tools (if available)
        'grub-common',
        'efibootmgr',
        
        # Live boot (if available)
        'live-boot',
        'live-config',
    ]
    
    return minimal_packages

def main():
    if len(sys.argv) != 2:
        print("Usage: python3 fix_live_environment_packages.py <chroot_path>")
        sys.exit(1)
    
    chroot_path = Path(sys.argv[1])
    
    if not chroot_path.exists():
        logger.error(f"Chroot path does not exist: {chroot_path}")
        sys.exit(1)
    
    logger.info(f"Fixing LiveEnvironment packages for chroot: {chroot_path}")
    
    # Step 1: Check current state
    check_chroot_repos(chroot_path)
    
    # Step 2: Fix repositories
    fix_chroot_repos(chroot_path)
    
    # Step 3: Test package availability
    if test_package_availability(chroot_path):
        logger.info("✅ Repository fix successful - packages are now available")
    else:
        logger.warning("⚠️  Some packages still missing - will use minimal set")
    
    # Step 4: Create minimal package recommendation
    minimal = create_minimal_package_list()
    logger.info(f"Minimal package set ({len(minimal)} packages):")
    for pkg in minimal:
        logger.info(f"  - {pkg}")
    
    logger.info("Repository configuration fixed. Retry the build now.")

if __name__ == "__main__":
    main()