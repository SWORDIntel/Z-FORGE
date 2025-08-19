# Z-FORGE Build Workflow - Proxmox VE 9.0 Beta + ZFS 2.3.3

## Clean Build Process

### Prerequisites
```bash
# Install dependencies
make -f Makefile.no_tmp deps
```

### Option 1: Complete Build (Recommended)
```bash
# Builds ZFS and Proxmox first, then Z-FORGE ISO
make -f Makefile.no_tmp build-debian13
```

### Option 2: Build Sources Only
```bash
# Build both ZFS and Proxmox from source (no ISO)
make -f Makefile.no_tmp build-sources
```

### Option 3: Individual Builds
```bash
# Build just ZFS from Proxmox source
make -f Makefile.no_tmp build-zfs

# Build just Proxmox VE from source  
make -f Makefile.no_tmp build-proxmox
```

### Option 4: ISO Only (Sources already built)
```bash
# Build ISO assuming ZFS and Proxmox packages exist
make -f Makefile.no_tmp build-debian13-no-sources
```

## Build Components

### ZFS 2.3.3 from Proxmox Source
- **Source**: `https://git.proxmox.com/git/zfsonlinux.git`
- **Build Script**: `scripts/build/build_zfs_on_host.sh`
- **Build Location**: Outside chroot (host system)
- **Output**: Packages in `prebuilt_packages/`
- **Features**: RAID-Z expansion, Proxmox optimizations

### Proxmox VE 9.0 Beta from Source
- **Sources**: 
  - `https://git.proxmox.com/git/pve-manager.git`
  - `https://git.proxmox.com/git/proxmox-ve.git`
  - `https://git.proxmox.com/git/pve-kernel.git`
- **Build Script**: `scripts/build/build_proxmox_on_host.sh`
- **Build Location**: Outside chroot (host system)
- **Output**: Packages in `prebuilt_packages/`
- **Features**: SDN Fabrics, LVM snapshots, advanced clustering

## Expected Build Time
- **ZFS Build**: 15-30 minutes
- **Proxmox Build**: 30-60 minutes (userspace only)
- **ISO Build**: 45-90 minutes
- **Total**: 90-180 minutes

## Output
- **ISO**: `~/zforge_workspace/output/zforge-3.0-amd64.iso`
- **ZFS Packages**: `prebuilt_packages/*.deb`
- **Logs**: `~/zforge_workspace/logs/`

## Clean Workspace
```bash
make -f Makefile.no_tmp clean
```