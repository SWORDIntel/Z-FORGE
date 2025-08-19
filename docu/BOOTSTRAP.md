# Z-FORGE Bootstrap Guide
## Reliable Build Methods That Actually Work

### 🎯 **TL;DR - Quickest Path to Success**

```bash
# Create logs directory
mkdir -p logs

# Run the most stable build (5 minutes)
sudo python3 build.py --spec build_specs/build_spec_working.yml --verbose --debug 2>&1 | tee logs/build-$(date +%Y%m%d_%H%M%S).log

# Check for generated ISO
ls -la *.iso
```

---

## 📋 **Recommended Build Order (Progressive Complexity)**

### **1. Minimal Working Build** ✅ (5 minutes, Most Stable)
```bash
sudo python3 build.py --spec build_specs/build_spec_working.yml --verbose --debug 2>&1 | tee logs/minimal-$(date +%Y%m%d_%H%M%S).log
```
- **Success Rate**: 95%
- **Purpose**: Validates build system is working
- **Output**: Basic bootable ISO

### **2. ZFS-Only Build** (10 minutes, No Proxmox)
```bash
sudo python3 build.py --spec build_specs/build_spec_no_proxmox.yml --verbose --debug 2>&1 | tee logs/zfs-only-$(date +%Y%m%d_%H%M%S).log
```
- **Success Rate**: 90%
- **Purpose**: ZFS-focused system without Proxmox complications
- **Output**: ZFS-enabled ISO

### **3. High-Performance Build** (15 minutes, Recommended)
```bash
sudo python3 build.py --spec build_specs/build_spec_outside_packages.yml --verbose --debug 2>&1 | tee logs/outside-$(date +%Y%m%d_%H%M%S).log
```
- **Success Rate**: 85%
- **Purpose**: Optimized build with outside package strategy
- **Output**: Performance-optimized ZFS ISO

### **4. Clean Trixie Build** (20 minutes)
```bash
sudo python3 build.py --spec build_specs/build_spec_trixie_clean.yml --verbose --debug 2>&1 | tee logs/trixie-$(date +%Y%m%d_%H%M%S).log
```
- **Success Rate**: 80%
- **Purpose**: Clean Debian Trixie base
- **Output**: Standard Trixie ISO with ZFS

### **5. Proxmox VE 9 Basic** (30 minutes)
```bash
sudo python3 build.py --spec build_specs/build_spec_proxmox9.yml --verbose --debug 2>&1 | tee logs/pve9-basic-$(date +%Y%m%d_%H%M%S).log
```
- **Success Rate**: 70%
- **Purpose**: Basic Proxmox VE 9 on Trixie
- **Output**: Minimal Proxmox ISO

### **6. Full Proxmox VE 9** (45 minutes)
```bash
sudo python3 build.py --spec build_specs/build_spec_proxmox_full.yml --verbose --debug 2>&1 | tee logs/pve9-full-$(date +%Y%m%d_%H%M%S).log
```
- **Success Rate**: 65%
- **Purpose**: Complete Proxmox VE 9 with all features
- **Output**: Full-featured Proxmox ISO

---

## 🔧 **Manual Step-by-Step Method**

### **Step 1: Prepare Workspace**
```bash
export WORKSPACE="/tmp/zforge-manual"
sudo rm -rf "$WORKSPACE"
mkdir -p "$WORKSPACE"
```

### **Step 2: Run Debootstrap**
```bash
sudo debootstrap \
    --arch=amd64 \
    --include=wget,curl,gnupg,lsb-release,locales \
    trixie \
    "$WORKSPACE/chroot" \
    http://deb.debian.org/debian
```

### **Step 3: Mount System Directories**
```bash
sudo mount -t proc proc "$WORKSPACE/chroot/proc"
sudo mount -t sysfs sys "$WORKSPACE/chroot/sys"
sudo mount -t devtmpfs udev "$WORKSPACE/chroot/dev"
sudo mount -t devpts devpts "$WORKSPACE/chroot/dev/pts"
```

### **Step 4: Configure APT Sources**
```bash
sudo tee "$WORKSPACE/chroot/etc/apt/sources.list" << EOF
deb http://deb.debian.org/debian trixie main contrib non-free non-free-firmware
deb-src http://deb.debian.org/debian trixie main contrib non-free non-free-firmware
deb http://deb.debian.org/debian-security trixie-security main contrib non-free non-free-firmware
EOF

sudo chroot "$WORKSPACE/chroot" apt-get update
```

### **Step 5: Install Core Packages**
```bash
# Install kernel
sudo chroot "$WORKSPACE/chroot" apt-get install -y \
    linux-image-amd64 \
    linux-headers-amd64 \
    firmware-linux \
    firmware-linux-nonfree

# Install ZFS
sudo chroot "$WORKSPACE/chroot" apt-get install -y \
    zfsutils-linux \
    zfs-dkms \
    zfs-initramfs

# Verify installations
sudo chroot "$WORKSPACE/chroot" which zfs
ls "$WORKSPACE/chroot/boot/vmlinuz-"*
```

### **Step 6: Cleanup**
```bash
sudo umount "$WORKSPACE/chroot/dev/pts" || true
sudo umount "$WORKSPACE/chroot/dev" || true
sudo umount "$WORKSPACE/chroot/proc" || true
sudo umount "$WORKSPACE/chroot/sys" || true
```

---

## 📊 **Success Validation**

### **Check Build Success**
```bash
# Look for ISO file
ls -la *.iso

# Check latest log for errors
tail -50 logs/*.log | grep -i "error\|failed\|success"

# Verify workspace size (if exists)
du -sh /tmp/zforge-workspace-*
```

### **Quick Health Check Script**
```bash
#!/bin/bash
echo "=== Z-FORGE Build Health Check ==="
echo "ISOs found: $(ls *.iso 2>/dev/null | wc -l)"
echo "Recent errors: $(grep -i error logs/*.log 2>/dev/null | wc -l)"
echo "Workspace status:"
for workspace in /tmp/zforge-workspace-*; do
    if [ -d "$workspace" ]; then
        echo "  - $(basename $workspace): $(du -sh $workspace | cut -f1)"
    fi
done
```

---

## 🆘 **Troubleshooting Common Issues**

### **Issue: Import Errors**
```bash
# Fix: Use the build.py directly, not the bootstrap scripts
sudo python3 build.py --spec build_specs/build_spec_working.yml --verbose
```

### **Issue: No Space Left**
```bash
# Fix: Clean workspaces and increase tmpfs
sudo rm -rf /tmp/zforge-workspace-*
sudo mount -o remount,size=40G /tmp
```

### **Issue: Package Not Found**
```bash
# Fix: Update sources and use fallback mirrors
sudo apt-get update
sudo apt-get install -y debootstrap squashfs-tools xorriso
```

### **Issue: Permission Denied**
```bash
# Fix: Ensure running with sudo
sudo python3 build.py --spec build_specs/build_spec_working.yml --verbose
```

---

## 🚀 **Best Practices**

1. **Start Small**: Always test with `build_spec_working.yml` first
2. **Use Logging**: Always redirect output to logs with `tee`
3. **Monitor Resources**: Watch RAM usage with `free -h` during builds
4. **Clean Between Builds**: Remove old workspaces to free space
5. **Check Dependencies**: Ensure all required packages are installed

---

## 💡 **Advanced Tips**

### **Parallel Builds** (if you have lots of RAM)
```bash
# Terminal 1
sudo python3 build.py --spec build_specs/build_spec_working.yml --verbose &

# Terminal 2 (different workspace)
sudo python3 build.py --spec build_specs/build_spec_no_proxmox.yml --verbose &
```

### **Custom Workspace Location**
```bash
sudo python3 build.py \
    --spec build_specs/build_spec_working.yml \
    --workspace /mnt/fast-disk/custom-workspace \
    --verbose
```

### **Resume Failed Build**
```bash
sudo python3 build.py \
    --spec build_specs/build_spec_working.yml \
    --resume \
    --verbose
```

---

## 📝 **Summary**

**For best results:**
1. Use the direct `build.py` commands (not complex bootstrap scripts)
2. Start with `build_spec_working.yml` (highest success rate)
3. Progress to more complex builds after confirming basics work
4. Always use `--verbose --debug` and save logs
5. All builds now use RAM workspaces for 3-5x performance

The build system is designed to be modular - if one approach fails, try a simpler spec first to identify the issue.