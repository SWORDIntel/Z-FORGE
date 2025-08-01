# [ARCHIVED] Redundant Scripts Analysis

**Note: This analysis has been completed. See CLEANUP_SUMMARY_20250801.md for results.**

# Original Redundant Scripts Analysis

## Active Scripts (Used by current build system)
These scripts are actively used and have been fixed:
- `scripts/workspace/workspace_config.sh` - Fixed to use $HOME
- `scripts/build/build_zfs_on_host.sh` - Fixed to use $HOME
- `scripts/workspace/setup_no_tmp_build.sh` - Fixed to use $HOME
- `scripts/build/build_proxmox_on_host.sh` - No hardcoded paths
- `scripts/build/build-auto.py` - No hardcoded paths

## Build Process Scripts
The current build process uses:
1. `make -f Makefile.no_tmp build` → calls `scripts/build/build-auto.py`
2. `make -f Makefile.no_tmp build-zfs` → calls `scripts/build/build_zfs_on_host.sh`
3. `make -f Makefile.no_tmp build-proxmox` → calls `scripts/build/build_proxmox_on_host.sh`

## Redundant Scripts Categories
The following scripts contain hardcoded paths but are **NOT** used by the current build system:

### Old Build Scripts
- `scripts/build/build.sh` - Old build system
- `scripts/build/run_zfs_build.sh` - Replaced by build_zfs_on_host.sh

### Fix Scripts (Many outdated)
- `scripts/fixes/*` - Various fix scripts with hardcoded paths
- `scripts/fix/*` - Older fix directory

### Download Scripts (Redundant)
- `scripts/download/*` - Various download scripts, mostly unused

### Package Scripts (Redundant)
- `scripts/package/*` - Old package management scripts

### Chroot Scripts (Some may be useful)
- `scripts/chroot/bootstrap_chroot.sh`
- `scripts/chroot/use_debootstrap.sh`
- `scripts/chroot/complete_zfs_install.sh` - Still referenced in README

### Agent Scripts
- `scripts/agents/*` - Ultrathink agents with hardcoded paths

## Recommendation
The 120 remaining hardcoded paths are mostly in redundant scripts not used by the current build system. The critical paths have been fixed. Consider:
1. Moving redundant scripts to an archive directory
2. Or running a batch update on all scripts if you want to keep them functional