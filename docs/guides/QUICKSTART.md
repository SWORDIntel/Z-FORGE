# Z-FORGE Quick Start Guide

## Fastest Path to Success

### 1. Prerequisites (2 minutes)
```bash
sudo apt update && sudo apt install -y \
    git build-essential debootstrap \
    python3 python3-pip python3-yaml \
    arch-install-scripts squashfs-tools \
    xorriso isolinux syslinux-utils
```

### 2. Get Z-FORGE (1 minute)
```bash
git clone [repository-url] /opt/github/Z-FORGE
cd /opt/github/Z-FORGE
chmod +x scripts/**/*.sh
```

### 3. Install ZFS Support (5-10 minutes)
```bash
# This single command does everything:
# - Creates workspace in HOME
# - Bootstraps chroot
# - Installs dependencies
# - Configures ZFS
sudo ./scripts/chroot/complete_zfs_install.sh
```

### 4. Build ISO (15-30 minutes)
```bash
# Non-/tmp build (recommended)
sudo make -f Makefile.no_tmp build

# Or standard build
sudo make build
```

## That's It! 🎉

Your ISO will be in: `iso_output/`

---

## Common Commands After Setup

### Enter Chroot
```bash
sudo ./scripts/chroot/use_arch_chroot.sh
```

### Check Build Status
```bash
tail -f logs/zforge_build_*.log
```

### Clean and Rebuild
```bash
sudo make clean
sudo make -f Makefile.no_tmp build
```

---

## If Something Goes Wrong

### Network Issues in Chroot
```bash
sudo ./scripts/fixes/fix_chroot_network.sh
```

### Permission Issues
```bash
sudo chown -R $USER:$USER /opt/github/Z-FORGE
```

### Start Over
```bash
sudo rm -rf ~/zforge_workspace
sudo ./scripts/chroot/complete_zfs_install.sh
```

---

## More Info
- Full guide: `START_FROM_SCRATCH.md`
- Documentation: `docs/README.md`
- Quick reference: `checkpoint/QUICK_REFERENCE.md`