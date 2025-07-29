# Z-FORGE Kernel/ZFS Fix Scripts

## Quick Fix

Just run:
```bash
/opt/github/Z-FORGE/FIX_NOW.sh
```

This will automatically fix your kernel and ZFS installation issues.

## UltraThink Multi-Agent System

The main fix system uses multiple specialized agents working in parallel:

### Agents Deployed:

1. **Diagnostic Agent** - Comprehensive system analysis
2. **Repair Agent** - Fixes DPKG and APT issues  
3. **Repository Agent** - Configures Debian Trixie sources
4. **Kernel Agents** (3 parallel strategies):
   - Specific 6.12.38 kernel installation
   - Metapackage installation
   - Latest available kernel
5. **ZFS Agent** - Installs ZFS with DKMS
6. **Verification Agent** - Confirms fix success

### Files Created:

- `ultrathink_kernel_fix.py` - Main multi-agent system
- `launch_ultrathink.sh` - Easy launcher script
- `ultrathink_fallback.sh` - Comprehensive fallback if agents fail
- `FIX_NOW.sh` - One-click fix solution

### Other Diagnostic Scripts:

- `diagnose_kernel_version.sh` - Detailed kernel diagnostics
- `check_debian_kernels.sh` - Shows kernels for each Debian release
- `quick_kernel_check.sh` - Quick system status check

### Manual Fix Scripts:

- `fix_dpkg_interrupted.sh` - Fix interrupted DPKG
- `fix_trixie_kernel_612.sh` - Install specific 6.12 kernel
- `fix_trixie_kernel_version.sh` - Fix APT sources for Trixie
- `install_trixie_kernel_safe.sh` - Safe kernel installation
- `recover_and_install.sh` - Complete recovery process

## Expected Result

After running the fix:
- Kernel 6.12.38+deb13-amd64 (or newer) installed
- ZFS packages installed with DKMS support
- APT sources pointing to Debian Trixie (testing)
- All package conflicts resolved

## Logs

All operations are logged to:
- `/opt/github/Z-FORGE/ultrathink_fix_*.log`
- `/opt/github/Z-FORGE/ultrathink_results_*.json`
- `/opt/github/Z-FORGE/ultrathink_fallback_*.log`

## If Issues Persist

1. Check the log files for specific errors
2. Ensure the chroot exists at `/tmp/zforge_workspace/chroot`
3. Verify you have sudo privileges
4. Try individual scripts for specific issues

## Manual Commands

If automated fixes fail:

```bash
# Fix DPKG
sudo chroot /tmp/zforge_workspace/chroot dpkg --configure -a
sudo chroot /tmp/zforge_workspace/chroot apt-get install -f

# Update sources to Trixie
sudo nano /tmp/zforge_workspace/chroot/etc/apt/sources.list
# Add: deb http://deb.debian.org/debian testing main contrib non-free-firmware

# Update and install kernel
sudo chroot /tmp/zforge_workspace/chroot apt-get update
sudo chroot /tmp/zforge_workspace/chroot apt-get install linux-image-amd64 linux-headers-amd64

# Install ZFS
sudo chroot /tmp/zforge_workspace/chroot apt-get install zfsutils-linux zfs-dkms
```