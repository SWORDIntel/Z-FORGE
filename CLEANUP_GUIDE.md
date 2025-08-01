# Z-FORGE Script Cleanup Guide

**Date:** 2025-01-31  
**Purpose:** Clean up obsolete scripts and ensure project consistency

## Overview

The Z-FORGE project has accumulated technical debt in the form of obsolete scripts in the `archive/` directory. This guide provides a systematic approach to cleaning up these scripts and ensuring all remaining scripts are consistent.

## Quick Cleanup Process

```bash
# 1. Run consistency verification (before cleanup)
./scripts/cleanup/verify_project_consistency.sh

# 2. Remove obsolete scripts
./scripts/cleanup/cleanup_obsolete_scripts.sh

# 3. Update any remaining old paths
./scripts/cleanup/update_script_paths.sh

# 4. Verify consistency again
./scripts/cleanup/verify_project_consistency.sh
```

## Detailed Steps

### Step 1: Verify Current State

First, check the current state of the project:

```bash
cd /opt/github/Z-FORGE
./scripts/cleanup/verify_project_consistency.sh
```

This will show you:
- Which tests are passing/failing
- Current script count
- Any path inconsistencies

### Step 2: Remove Obsolete Scripts

The cleanup script will:
- Back up all files before removal
- Remove ~45 obsolete scripts from `archive/`
- Clean up empty directories

```bash
sudo ./scripts/cleanup/cleanup_obsolete_scripts.sh
```

**Files to be removed:**
- `archive/old_build_scripts/` - 40+ obsolete build scripts
- `archive/old_scripts/` - Old DKMS fix scripts
- `archive/old_configs/` - Outdated configurations

### Step 3: Update Script Paths

Some scripts may still reference old paths. Update them:

```bash
./scripts/cleanup/update_script_paths.sh
```

This will:
- Find scripts using `/tmp/zforge_workspace`
- Update them to use `${ZFORGE_WORKSPACE:-$HOME/zforge_workspace}`
- Create backups of modified files

### Step 4: Final Verification

Run the verification again to ensure everything is clean:

```bash
./scripts/cleanup/verify_project_consistency.sh
```

All tests should pass after cleanup.

## What Gets Cleaned

### Obsolete Scripts (~45 files)
- Duplicate build scripts
- Old workspace management scripts
- Outdated bootstrap implementations
- Legacy cleanup scripts
- Replaced functionality

### Path Updates
- `/tmp/zforge_workspace` → `${ZFORGE_WORKSPACE:-$HOME/zforge_workspace}`
- Hardcoded paths → Environment variables
- Legacy patterns → Modern patterns

## Backup and Recovery

All removed files are backed up to:
```
backup/obsolete_scripts_[timestamp]/
```

To restore if needed:
```bash
cp -r backup/obsolete_scripts_*/  .
```

## Post-Cleanup Structure

After cleanup, the project will have:
- **Clean `scripts/` directory** with organized subdirectories
- **No `archive/` directory** (or empty if preserved)
- **Consistent paths** using HOME workspace
- **All scripts executable** with proper permissions

## Key Scripts to Keep

### Build System
- `scripts/build/build.sh` - Main build entry
- `scripts/build/build_zfs_on_host.sh` - ZFS builder
- `scripts/build/build_proxmox_on_host.sh` - Proxmox builder

### Chroot Management
- `scripts/chroot/complete_zfs_install.sh` - Recommended entry point
- `scripts/chroot/bootstrap_chroot.sh` - Bootstrap tool
- `scripts/chroot/use_arch_chroot.sh` - Arch-chroot wrapper

### Workspace
- `scripts/workspace/setup_no_tmp_build.sh` - Setup HOME workspace
- `scripts/workspace/fix_workspace_noexec.sh` - Fix permissions

## Verification Checklist

After cleanup, ensure:
- [ ] No scripts reference `/tmp/zforge_workspace`
- [ ] All scripts use proper user detection pattern
- [ ] Archive directory is removed or empty
- [ ] All key scripts are executable
- [ ] Build system works: `sudo make -f Makefile.no_tmp build`
- [ ] Bootstrap works: `sudo ./scripts/chroot/bootstrap_chroot.sh auto`

## Benefits of Cleanup

1. **Reduced Confusion** - No duplicate scripts with similar names
2. **Clear Organization** - Everything in proper directories
3. **Consistent Paths** - All scripts use same workspace approach
4. **Maintainability** - Easier to find and update scripts
5. **Smaller Repository** - ~45 fewer files to manage

## Summary

This cleanup removes approximately 45 obsolete scripts while preserving all active functionality. The result is a clean, well-organized project structure that's easier to maintain and use.