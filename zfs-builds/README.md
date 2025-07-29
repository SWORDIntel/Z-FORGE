# ZFS Build Scripts

This directory contains scripts for building and managing ZFS on Debian systems.

## Subdirectories

### zfs-2.3.3/
Scripts specifically for building ZFS version 2.3.3:
- **build-zfs-2.3.3-debian-packages.sh** - Builds Debian packages for ZFS 2.3.3
- **build-zfs-2.3.3-from-source.sh** - Builds ZFS 2.3.3 from source code
- **build-zfs-2.3.3-minimal.sh** - Minimal build for ZFS 2.3.3 (userspace + kernel modules)
- **build-zfs-2.3.3-simple.sh** - Simplified ZFS 2.3.3 build process
- **build-zfs-fix-headers.sh** - Fixes header conflicts during build
- **build-zfs-native-debian.sh** - Native Debian build method
- **build-zfs-optimized.sh** - Optimized build with CPU-specific flags
- **fix-zfs-build.sh** - General ZFS build issue fixes
- **fix-zfs-changelog.sh** - Fixes changelog formatting issues
- **fix-zfs-gitrev.sh** - Creates missing zfs_gitrev.h file
- **fix-zfs-module-version.sh** - Fixes module version mismatches
- **upgrade-zfs-2.3.3.sh** - Upgrades existing ZFS to 2.3.3
- **upgrade-zfs-trixie.sh** - ZFS upgrade for Debian Trixie

### zfs-utils/
Utility scripts for ZFS management:
- **check-zfs-build-deps.sh** - Checks build dependencies for ZFS
- **install-zfs-from-backports.sh** - Installs ZFS from Debian backports
- **install-zfs-python-deps.sh** - Installs Python dependencies for ZFS
- **test-zfs-performance.sh** - Performance testing for ZFS pools
- **zfsback.sh** - ZFS backup utility
- **zfdashinst.sh** - ZFS dashboard installer

### zfs-troubleshooting/
Scripts for fixing common ZFS issues:
- **build-zfs-initramfs-only.sh** - Rebuilds only ZFS initramfs components
- **fix-zfs-module-version.sh** - Resolves module version conflicts