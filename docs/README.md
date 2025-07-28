# Z-FORGE Documentation Hub

**AI Agent Navigation Guide** - All project documentation organized for easy access

## Quick Navigation

| Category | Directory | Contents |
|----------|-----------|----------|
| 🏗️ **Build System** | [`build/`](./build/) | Build process, readiness checks, recovery procedures |
| 🔧 **Hardware** | [`hardware/`](./hardware/) | Hardware support, integrations, compatibility |
| 💾 **ZFS** | [`zfs/`](./zfs/) | ZFS configuration, RAID, integration details |
| 🔗 **Integration** | [`integration/`](./integration/) | System integration verification and summaries |
| 📁 **Project** | [`project/`](./project/) | Core project documentation and instructions |
| 📊 **Reports** | [`reports/`](./reports/) | Build reports, progress summaries, status updates |

## Essential Files for AI Agents

### Project Core
- **[`project/CLAUDE.md`](./project/CLAUDE.md)** - Complete build system instructions and fixes
- **[`project/README.md`](./project/README.md)** - Main project overview

### Build System
- **[`build/BUILD_READY.md`](./build/BUILD_READY.md)** - Current build readiness status
- **[`build/POST_REBOOT_RESUME.md`](./build/POST_REBOOT_RESUME.md)** - Post-reboot recovery instructions

### Hardware Support
- **[`hardware/SUPPORTED_HARDWARE.md`](./hardware/SUPPORTED_HARDWARE.md)** - Complete hardware compatibility list
- **[`hardware/HARDWARE_DATABASE_INVENTORY.md`](./hardware/HARDWARE_DATABASE_INVENTORY.md)** - Hardware detection database

### Integration Status
- **[`integration/FINAL_INTEGRATION_VERIFICATION.md`](./integration/FINAL_INTEGRATION_VERIFICATION.md)** - Latest integration status
- **[`integration/FULL_INTEGRATION_SUMMARY.md`](./integration/FULL_INTEGRATION_SUMMARY.md)** - Complete integration overview

## Directory Structure

```
docs/
├── README.md                    # This navigation file
├── build/                      # Build system documentation
│   ├── BUILD_READY.md          # Build readiness status
│   └── POST_REBOOT_RESUME.md   # Recovery procedures
├── hardware/                   # Hardware support docs
│   ├── CALAMARES_HARDWARE_INTEGRATION.md
│   ├── HARDWARE_DATABASE_INVENTORY.md
│   ├── SAS_INTEGRATION_VERIFICATION.md
│   ├── STORAGE_SUPPORT_INVENTORY.md
│   └── SUPPORTED_HARDWARE.md
├── integration/                # Integration documentation
│   ├── FINAL_INTEGRATION_VERIFICATION.md
│   └── FULL_INTEGRATION_SUMMARY.md
├── project/                    # Core project files
│   ├── CLAUDE.md              # Build system instructions
│   └── README.md              # Project overview
├── reports/                    # Historical reports
│   └── [Various progress reports]
└── zfs/                       # ZFS-specific docs
    ├── ZFS_2.3.3_INTEGRATION.md
    ├── ZFS_BUILD_COMPLIANCE.md
    └── ZFS_RAID_CONFIGURATION.md
```

## For AI Agents: Key Information

### Build System Status
- **Last Known Issue**: DracutConfig module failure - 90zforge-toram module missing
- **Critical Files**: [`project/CLAUDE.md`](./project/CLAUDE.md) contains complete fix history
- **Recovery**: [`build/POST_REBOOT_RESUME.md`](./build/POST_REBOOT_RESUME.md) for network issues

### Hardware Support
- **Dell Servers**: R730xd, R420, R320 with specific optimizations
- **Storage**: RAID, NVMe, ZFS pools with hardware detection
- **Integration**: Calamares installer with hardware-aware modules

### Current Focus Areas
1. **Dracut Module Installation** - Primary build blocker
2. **Network Configuration** - USB tether DNS issues resolved
3. **Hardware Detection** - Auto-optimization system active

## Quick Commands for AI Agents

```bash
# View current build status
cat docs/build/BUILD_READY.md

# Check hardware support
cat docs/hardware/SUPPORTED_HARDWARE.md

# Review latest integration
cat docs/integration/FINAL_INTEGRATION_VERIFICATION.md

# Access build instructions
cat docs/project/CLAUDE.md
```

---
*This documentation hub is organized for efficient AI agent navigation and human readability.*