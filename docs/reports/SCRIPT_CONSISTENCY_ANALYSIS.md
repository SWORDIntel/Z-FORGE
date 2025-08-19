# Z-FORGE Script Consistency Analysis Report

**Date:** 2025-01-31  
**Analysis Type:** Comprehensive Script Audit

## Executive Summary

The Z-FORGE project has undergone significant reorganization but still contains inconsistencies between scripts and a large number of obsolete files in the archive. The project is transitioning from `/tmp/zforge_workspace` to `~/zforge_workspace` to avoid noexec mount issues, but not all scripts have been updated to reflect this change.

## 1. Path Consistency Analysis

### Current State
- **Recommended Path:** `~/zforge_workspace` (HOME-based, avoids /tmp issues)
- **Legacy Path:** `/tmp/zforge_workspace` (problematic with noexec mounts)
- **Alternative Path:** `/var/lib/zforge_workspace` (for root operations)

### Script Path Usage

#### ✅ Scripts Using Correct Paths (~/zforge_workspace)
- `scripts/chroot/bootstrap_chroot.sh` - Uses `$ORIGINAL_HOME/zforge_workspace/chroot`
- `scripts/workspace/setup_no_tmp_build.sh` - Sets up `$HOME/zforge_workspace`
- `Makefile.no_tmp` - Defaults to `$(HOME)/zforge_workspace`

#### ❌ Scripts Still Using /tmp Paths
- Many archive scripts still reference `/tmp/zforge_workspace`
- Some scripts have hardcoded paths without using environment variables

### User Detection Pattern

#### ✅ Correct Pattern
```bash
ORIGINAL_USER=${SUDO_USER:-$(logname 2>/dev/null || echo $USER)}
ORIGINAL_HOME=$(eval echo "~$ORIGINAL_USER" 2>/dev/null || echo "$HOME")
```

#### Scripts Using Correct Pattern
- `scripts/chroot/bootstrap_chroot.sh`
- Most newer scripts in `scripts/` directory

## 2. Build System Consistency

### Current Approach
- **Primary:** `Makefile.no_tmp` with HOME workspace
- **Fallback:** Standard `Makefile` (but not present in root)
- **Python:** `build.py` orchestration

### Key Issues
1. Missing standard `Makefile` in root (only `Makefile.no_tmp`)
2. Multiple build approaches without clear hierarchy
3. Some scripts reference old build methods

## 3. Obsolete Scripts Analysis

### Archive Directory (`archive/`)
Contains 40+ obsolete scripts that should be removed:

#### Duplicate Functionality
- `archive/old_build_scripts/zforge_build.sh` - Replaced by current build system
- `archive/old_build_scripts/build_zfs_*` - Multiple redundant ZFS build scripts
- `archive/old_build_scripts/cleanup*.sh` - Replaced by scripts in `scripts/cleanup/`

#### Outdated Approaches
- Scripts using old workspace paths
- Scripts with outdated build methods
- Scripts referencing removed components

### Scripts to Remove (High Priority)
1. **All files in `archive/old_build_scripts/`** - 40+ files
2. **Old workspace scripts in archive**
3. **Duplicate bootstrap/debootstrap scripts**

## 4. Critical Path Analysis

### Bootstrap Location
- **Should be:** `~/zforge_workspace/chroot`
- **Consistency:** Most scripts updated, but some archive scripts still use `/tmp`

### Script Organization
- **Current Structure:** Well-organized under `scripts/`
- **Issue:** Archive contains duplicates and obsolete versions

### ZFS Package Handling
- **Consistent approach:** Build from Proxmox source
- **Version:** ZFS 2.3.3
- **Location:** Prebuilt packages in `/opt/github/Z-FORGE/prebuilt_packages`

## 5. Recommendations

### Immediate Actions

1. **Remove Archive Directory**
   ```bash
   rm -rf archive/old_build_scripts/
   rm -rf archive/old_scripts/
   ```

2. **Create Standard Makefile**
   ```bash
   ln -s Makefile.no_tmp Makefile
   # OR create wrapper Makefile that includes Makefile.no_tmp
   ```

3. **Update Remaining Scripts**
   - Audit all scripts for hardcoded `/tmp` paths
   - Ensure all use environment variables for workspace

### Script Consolidation

1. **Build Scripts**
   - Keep: `scripts/build/build.sh` (main entry)
   - Keep: `scripts/build/build_zfs_on_host.sh`
   - Remove: All archive build scripts

2. **Chroot Scripts**
   - Keep: `scripts/chroot/complete_zfs_install.sh` (recommended entry)
   - Keep: `scripts/chroot/bootstrap_chroot.sh`
   - Keep: `scripts/chroot/use_arch_chroot.sh`
   - Remove: Duplicate functionality in archive

3. **Workspace Scripts**
   - Keep: All in `scripts/workspace/`
   - Ensure consistent with HOME workspace approach

### Environment Variables
All scripts should use:
```bash
ZFORGE_WORKSPACE="${ZFORGE_WORKSPACE:-$HOME/zforge_workspace}"
```

## 6. Script Health Status

### ✅ Healthy Scripts (In Sync)
- Most scripts under `scripts/` directory
- `Makefile.no_tmp`
- Core build scripts

### ⚠️ Scripts Needing Updates
- Any referencing `/tmp/zforge_workspace` directly
- Scripts without proper user detection
- Scripts with hardcoded paths

### ❌ Scripts to Remove
- Everything in `archive/old_build_scripts/`
- Everything in `archive/old_scripts/`
- Approximately 40-45 obsolete scripts total

## 7. Verification Steps

After cleanup:
1. Run workspace setup: `./scripts/workspace/setup_no_tmp_build.sh`
2. Test bootstrap: `sudo ./scripts/chroot/bootstrap_chroot.sh auto`
3. Test build: `sudo make -f Makefile.no_tmp build`
4. Verify no scripts reference removed files

## Conclusion

The Z-FORGE project has a solid foundation with well-organized scripts under the `scripts/` directory. However, the `archive/` directory contains significant technical debt with 40+ obsolete scripts that should be removed. After cleanup and minor updates to ensure path consistency, the project will have a clean, maintainable script collection that works reliably with the HOME-based workspace approach.

**Total Scripts to Remove:** ~45 files  
**Scripts Needing Updates:** <10 files  
**Overall Health:** Good (after cleanup)