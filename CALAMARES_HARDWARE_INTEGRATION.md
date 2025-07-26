# Calamares Hardware Detection Integration

## Overview

The Z-FORGE Calamares installer now includes comprehensive hardware detection and configuration capabilities, fully integrated with the GUI installer experience.

## New Calamares Modules

### 1. **hardwaredetect** (Show Phase)
- Displays detected hardware profile to user
- Shows optimal settings from hardware database
- Categories: Servers, Workstations, Storage Systems, RAID Controllers
- Real-time hardware detection using lspci, dmidecode, lshw

### 2. **hardwareconfig** (Exec Phase)
- Applies hardware-specific optimizations
- Configures kernel modules for detected hardware
- Sets up vendor-specific repositories (Dell OMSA, etc.)
- Applies optimal ZFS settings based on hardware

### 3. **raidcontroller** (Show Phase)
- Detects RAID controllers (Dell PERC, HP Smart Array, LSI, Adaptec)
- Shows IT/HBA mode recommendations for ZFS
- Displays management tool availability
- Allows JBOD mode selection

### 4. **storageconfig** (Show Phase)
- Detects drive types (NVMe, SAS, SATA, USB)
- Shows drive details and optimization options
- Applies scheduler and queue depth settings
- Configures ZFS-specific optimizations

### 5. **opencoreinstall** (Exec Phase)
- Flexible OpenCore installation targets
- Priority-based target selection:
  - vFlash/IDSDM (Priority: 10)
  - USB drives (Priority: 7)
  - SD cards (Priority: 6)
  - Secondary drives (Priority: 5)
- NVMe boot support for legacy systems

## Installation Sequence

```yaml
sequence:
  - show:
    - welcome
    - hardwaredetect      # NEW: Hardware detection
    - telemetryconsent
    - locale
    - keyboard
    - zfspooldetect
    - zfsenhancedconfig
    - raidcontroller      # NEW: RAID configuration
    - storageconfig       # NEW: Storage optimization
  
  - exec:
    - hardwareconfig      # NEW: Apply hardware settings
    - mount
    - unpackfs
    - zfsrootselect
    - machineid
    - fstab
    - locale
    - keyboard
    - localecfg
    - users
    - displaymanager
    - networkcfg
    - securityhardening
    - hwclock
    - initramfscfg
    - initramfs
    - grubcfg
    - bootloader
    - opencoreinstall     # NEW: OpenCore for NVMe boot
    - umount
    - telemetryjob
    
  - show:
    - finished
```

## Hardware Database Integration

### Supported Hardware (19 Profiles)

#### Dell Servers (4)
- PowerEdge R730/R730xd
- PowerEdge R740/R740xd
- PowerEdge R640
- PowerEdge T30

#### HP Servers (1)
- ProLiant DL380 Gen10

#### Supermicro Servers (1)
- X11DPH-T

#### Workstations (4)
- Dell Precision G8
- AMD Ryzen 9 5950X System
- Intel Core i9-13900K System
- Sabrent Rocket NVMe System

#### Storage Systems (4)
- WD Ultrastar SAS System
- Dell EMC SAS System
- HP Enterprise SAS System
- Seagate Exos SAS System

#### RAID Controllers (5)
- Dell PERC H730
- Dell PERC H740P
- HP Smart Array P440ar
- LSI MegaRAID 9361-8i
- Adaptec ASR-8805

## GUI Features

### Hardware Detection Display
- Shows detected vendor and model
- Displays CPU, memory, and storage info
- Highlights matched hardware profile
- Shows optimal settings for the hardware

### RAID Controller Options
- IT/HBA mode recommendation for ZFS
- Management tool installation options
- Cache and BBU configuration
- JBOD mode selection

### Storage Configuration
- Drive type detection and display
- Per-drive optimization settings
- Scheduler selection (none, mq-deadline)
- Queue depth and read-ahead tuning

### OpenCore Installation
- Target device selection dropdown
- Priority-based recommendations
- vFlash detection for Dell servers
- USB and secondary drive options

## Dependencies Added

```yaml
# Hardware detection tools
- pciutils
- usbutils  
- dmidecode
- lshw
- hdparm
- smartmontools
- nvme-cli
- python3-pyudev

# RAID management
- mdadm
- lvm2
```

## Configuration Files

### `/etc/calamares/modules/hardwaredetect.conf`
```yaml
displayProfiles: true
showRAIDControllers: true
showStorageOptimizations: true
enableOpenCore: true
hardwareDatabase:
  enableDatabaseLookup: true
  showOptimalSettings: true
  categories:
    - servers
    - workstations
    - storage_systems
    - raid_controllers
```

### `/etc/calamares/modules/raidcontroller.conf`
```yaml
detectControllers: true
showITModeWarning: true
managementTools:
  dell_perc: perccli
  hp_smartarray: ssacli
  lsi_megaraid: megacli
  adaptec: arcconf
recommendedMode: IT
allowJBODMode: true
```

### `/etc/calamares/modules/storageconfig.conf`
```yaml
detectDriveTypes: [nvme, sas, sata, usb]
showDriveDetails: true
optimizationProfiles:
  nvme:
    scheduler: none
    nr_requests: 2048
  sas:
    scheduler: mq-deadline
    nr_requests: 256
    read_ahead_kb: 512
  sata:
    scheduler: mq-deadline
    nr_requests: 128
    read_ahead_kb: 256
zfsOptimizations: true
```

### `/etc/calamares/modules/opencoreinstall.conf`
```yaml
enabled: true
version: 0.9.9
installTargets:
  vFlash:
    enabled: true
    priority: 10
    description: Dell vFlash/IDSDM embedded storage
  usb:
    enabled: true
    priority: 7
    description: USB storage device
  secondary:
    enabled: true
    priority: 5
    description: Secondary internal drive
  sdcard:
    enabled: true
    priority: 6
    description: Internal SD card storage
features:
  nvmeSupport: true
  raidSupport: true
  chainloadZFS: true
```

## Branding Updates

- Product name: "Z-Forge Proxmox VE Enterprise"
- Welcome slide highlights:
  - Enterprise-ready with automatic hardware detection
  - Supports: Dell, HP, Supermicro servers
  - NVMe, SAS, RAID controller support
  - ZFS 2.3.3 with full encryption

## Benefits

1. **Automatic Hardware Detection** - No manual configuration needed
2. **Optimal Performance** - Hardware-specific tuning applied automatically
3. **Enterprise Support** - RAID controllers, SAS drives, server platforms
4. **Flexible Boot Options** - OpenCore with multiple installation targets
5. **User-Friendly** - Clear GUI options for all hardware features

The Calamares installer now provides a complete enterprise installation experience with full hardware awareness and optimization!