# CLAUDE.md - Z-FORGE Development Assistant Notes

## Project Overview
Z-FORGE is a custom Debian ISO builder for Proxmox VE with ZFS support, designed for PowerEdge servers and general hardware.

## Recent Fixes and Improvements (2025-07-22/23)

### Critical Build Fixes

#### 1. Module Import and Syntax Errors
- **Fixed missing imports**: Made `psutil`, `tqdm`, and `requests` optional with fallbacks
- **Fixed syntax errors**: Corrected major indentation issues in `bootloader_setup.py` 
- **Fixed undefined variables**: Changed `config` to `self.config` in `opencore_nvme.py`
- **Fixed regex escapes**: Corrected invalid escape sequence in `zfs_build.py`

#### 2. Duplicate Class Name Resolution
- **BootloaderSetup**: Renamed to `BootloaderSupport` in `bootloader_support.py`
- **Removed duplicate modules**: Backed up `open_core_nvme.py` and `zfs_boot_menu_install.py`
- **Fixed ZFSBootMenuInstall**: Removed stub with incorrect method signature

#### 3. Subprocess Timeout Additions
Added appropriate timeouts to prevent hanging builds:
- 30 seconds for quick commands (mount, system info)
- 300 seconds for package installations
- 600 seconds for compilation tasks (mksquashfs, xorriso)

#### 4. Error Handling Improvements
- Replaced bare `except:` clauses with specific exceptions
- Added proper error handling for file operations
- Standardized logger naming to use `self.__class__.__name__`

### Dracut Module Package Support

#### Comprehensive Package List Added
The following packages were added to `live_environment.py` to support all dracut modules:

**System Components:**
- `util-linux` - Hardware clock (hwclock) for warpclock module
- `systemd-coredump` - Core dump management
- `systemd-timesyncd` - Time synchronization
- `systemd-resolved` - DNS resolution
- `systemd-boot` - systemd-boot and systemd-repart
- `systemd-container` - systemd-portabled support
- `kbd` - Keyboard utilities (loadkeys, setfont) for i18n
- `kmod` - Kernel module utilities

**Network Services:**
- `dbus-broker` - High-performance D-Bus message broker
- `network-manager` - Modern network configuration
- `isc-dhcp-client` - DHCP client for network-legacy
- `rng-tools` - Hardware RNG daemon

**Storage Support:**
- `lvm2` - Logical Volume Management
- `btrfs-progs` - Btrfs filesystem support
- `xfsprogs` - XFS filesystem support
- `e2fsprogs` - ext2/3/4 filesystem utilities
- `dmraid` - Device-mapper RAID support
- `mdadm` - Linux software RAID
- `multipath-tools` - Multipath I/O

**Network Storage:**
- `open-iscsi` - iSCSI initiator support
- `nfs-common` - NFS client support
- `cifs-utils` - SMB/CIFS mounting
- `nbd-client` - Network Block Device
- `nvme-cli` + `jq` - NVMe over Fabrics support
- `fcoe-utils` + `lldpad` - Fibre Channel over Ethernet

**Security & Authentication:**
- `tpm2-tools` - TPM 2.0 support
- `pcsc-lite` - Smart card support
- `cryptsetup` - Disk encryption

**Additional Tools:**
- `biosdevname` - Consistent network device naming
- `erofs-utils` - Enhanced Read-Only File System

#### Robust Package Installation
Implemented graceful fallback for package installation:
1. Attempts batch installation of all packages first
2. Falls back to individual installation if batch fails
3. Logs which packages couldn't be installed
4. Continues build even if optional packages are missing

### Build Process Improvements

#### Module Loading
- Fixed module signature compatibility issues
- Ensured all modules have correct `execute(resume_data, lockfile)` signature
- Added proper return dictionaries with status

#### Path Handling
- Fixed hardcoded paths to check chroot before host system
- Ensured zfsbootmenu.efi is searched in correct locations

#### JSON Serialization
- Identified issue with set objects in build progress (non-critical)
- Build continues despite serialization warnings

## Current Build Status

The build now successfully:
1. ✅ Completes all syntax checks
2. ✅ Loads all modules without import errors
3. ✅ Handles missing packages gracefully
4. ✅ Creates initramfs with minimal dracut warnings
5. ✅ Progresses past ZFSBootMenuInstall module

## Next Steps

1. Monitor build completion through ISO generation
2. Test generated ISO on target hardware
3. Verify ZFS pool creation and encryption work correctly
4. Confirm all hardware support packages are functional

## Module Status Summary

**Phase 0-1**: ✅ Complete (Prerequisites, Setup, Debootstrap)
**Phase 2**: ✅ Complete (Kernel, ZFS Build, Dracut)
**Phase 3**: 🔄 In Progress (ZFSBootMenu, Proxmox Integration)
**Phase 4-7**: ⏳ Pending (Live Environment, Calamares, ISO Generation)

## Key Commands

```bash
# Run build
sudo ./builder/z-forge.py build --config build_spec.yml --debug

# Check latest log
tail -f logs/zforge_build_$(date +%Y%m%d)_*.log

# Resume from last successful module
sudo ./builder/z-forge.py build --config build_spec.yml --resume
```

## Important Notes

- The custom dracut 90zforge-toram module warning is non-critical
- JSON serialization warnings don't stop the build
- Some packages may not be available in all Debian releases (handled gracefully)
- Build uses ZFSBootMenu as primary bootloader (not GRUB) for installed system

---
*Last updated: 2025-07-23 00:30 GMT*