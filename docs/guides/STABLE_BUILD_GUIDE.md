# Z-FORGE Stable Build Guide

## Quick Start - Get a Working Build NOW

```bash
# 1. Switch to stable Debian
./scripts/quick_fix_bookworm.sh

# 2. Run stable build with validation
sudo python3 scripts/build_stable.py

# That's it! This should work reliably.
```

## Why Stable Builds Work Better

### Debian Bookworm (Stable) vs Trixie (Testing)
- **Bookworm**: Packages don't change, dependencies are fixed, everything works
- **Trixie**: Packages change daily, dependencies break, builds fail randomly

### What We Fixed
1. ✅ Switched from Trixie to Bookworm
2. ✅ Added pre-build validation
3. ✅ Enhanced error handling
4. ✅ Package pre-downloading
5. ✅ Better progress reporting

## Build Options

### 1. Minimal Stable Build (Recommended First)
```bash
sudo python3 build.py --spec build_spec_minimal.yml
```
- Just the essentials
- Most likely to succeed
- Good for testing

### 2. Full Stable Build
```bash
sudo python3 build.py --spec build_spec_stable.yml
```
- All basic features
- Still using stable packages
- Much more reliable than Trixie

### 3. Enhanced Build with Validation
```bash
sudo python3 scripts/build_stable.py
```
- Pre-flight checks
- Better error messages
- Package caching
- Progress tracking

## If Build Still Fails

### 1. Clean Everything
```bash
sudo rm -rf ~/zforge_workspace/*
sudo rm -rf ~/zforge_cache/*
```

### 2. Check Your System
```bash
# Run validation only
sudo python3 -c "
import sys
sys.path.insert(0, '.')
from scripts.build_stable import StableBuildValidator
v = StableBuildValidator()
v.validate_all()
"
```

### 3. Try Offline Build
```bash
# Download all packages first
sudo apt-get update
sudo apt-get download -d debootstrap systemd live-boot grub-pc

# Then build
sudo python3 build.py --spec build_spec_stable.yml
```

### 4. Use Docker/Podman (Future)
```bash
# Coming soon - containerized builds for 100% reliability
```

## Common Issues and Solutions

### "Package not found"
- **Cause**: Network issues or mirror problems
- **Fix**: Use `--mirror` option with different mirror

### "GPG verification failed"
- **Cause**: Key issues with repositories
- **Fix**: Already fixed with gpg_bypass module

### "No space left on device"
- **Cause**: Workspace fills up
- **Fix**: Clean workspace, need 20GB+ free

### "Permission denied"
- **Cause**: Not running as root
- **Fix**: Use `sudo`

## Understanding Module Order

```
workspace_setup     → Creates directories
    ↓
debootstrap        → Creates base system (Bookworm!)
    ↓
gpg_bypass         → Disables GPG checks
    ↓
chroot_setup       → Mounts /proc, /sys, /dev
    ↓
kernel_acquisition → Installs kernel
    ↓
live_environment   → Configures live boot
    ↓
squashfs          → Compresses filesystem
    ↓
iso_generation    → Creates bootable ISO
```

## Package Lists

### Minimal (What we build)
- systemd, kernel, live-boot
- Basic networking
- Boot loader

### Full (What you can add)
- Desktop environment
- Development tools
- Your custom packages

## Success Metrics

A successful build will:
1. Complete all modules without error
2. Create an ISO file in ~/zforge_workspace/
3. ISO will be ~500MB-1GB for minimal build
4. Can be tested in VirtualBox/QEMU

## Testing Your ISO

```bash
# Quick test with QEMU
qemu-system-x86_64 -m 2048 -cdrom ~/zforge_workspace/zforge-stable.iso

# Or VirtualBox
# Create new VM, attach ISO, boot
```

## Next Steps After Success

1. **Add Features Gradually**
   - Enable one module at a time
   - Test after each addition
   - Keep working backups

2. **Pin Package Versions**
   ```yaml
   packages:
     base:
       - systemd=252.19-1~deb12u1
   ```

3. **Create Snapshot**
   ```bash
   cp -r ~/zforge_workspace ~/zforge_workspace.working
   ```

## The Truth About Complex Builds

- Even Debian's own installer fails sometimes
- Building custom distros is HARD
- Start simple, add complexity gradually
- Use stable base, always

## Emergency Recovery

If everything is broken:
```bash
# Reset to clean state
cd /opt/github/Z-FORGE
git stash
git pull
./scripts/quick_fix_bookworm.sh
sudo python3 scripts/build_stable.py
```

Remember: **Stable > Bleeding Edge** when you need it to WORK!