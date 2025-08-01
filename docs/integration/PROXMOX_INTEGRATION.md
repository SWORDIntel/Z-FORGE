# Z-FORGE Proxmox VE Integration

## Overview

Z-FORGE now supports direct installation as a **Proxmox VE node**, combining the power of:
- **ZFS-on-root** for advanced storage features
- **Proxmox VE** for enterprise virtualization
- **Automated optimization** for virtualization workloads

## Quick Start

### Build Proxmox VE ISO
```bash
sudo ./build.sh --config config/proxmox_node.yaml
```

### Installation Options
1. **Standalone Node**: Single Proxmox server
2. **Cluster-Ready**: Pre-configured for cluster joining

## Features

### ✅ Completed by UltraThink Agent Team

#### Core Modules (6 modules created)
- **ProxmoxRepoSetup**: Repository configuration and GPG keys
- **ProxmoxPackageInstall**: Proxmox VE package installation  
- **ProxmoxStorageConfig**: ZFS storage optimization for VMs
- **ProxmoxNetworkConfig**: Bridge and VLAN configuration
- **ProxmoxServiceConfig**: Web UI and service management
- **ProxmoxClusterSetup**: Cluster preparation and HA support

#### Storage Architecture
```
rpool (ZFS Root Pool)
├── ROOT/pve-1      # Root filesystem
├── data/           # VM/Container storage
│   ├── vm/         # Virtual machine zvols (16k volblocksize)
│   └── ct/         # Container datasets (128k recordsize)
└── backup/         # Backup storage
```

#### Network Setup
- **vmbr0**: Management bridge (DHCP/Static)
- **VLAN-aware**: 802.1q VLAN support
- **Cluster-ready**: Pre-configured for Corosync

#### Optimization Features
- **ZFS tuning**: VM-specific volblocksize and recordsize
- **Kernel parameters**: IOMMU, virtualization features
- **Performance**: LZ4 compression, optimized ARC

### Test Suite (3 test types)
- **Unit tests**: Module functionality testing
- **Integration tests**: Full build process validation
- **Performance tests**: ZFS and network benchmarks

### Documentation (4 guides)
- **User Guide**: Installation and basic usage
- **Admin Guide**: Production deployment and tuning
- **Developer Guide**: Module development and API
- **API Reference**: Configuration schema and hooks

## Usage Examples

### Basic Proxmox Node
```bash
# Build with default Proxmox configuration
sudo ./build.sh --config config/proxmox_node.yaml
```

### Custom Configuration
```yaml
proxmox_config:
  hostname: "pve-node01"
  domain: "company.local"
  repository: "enterprise"  # Requires subscription
  storage_config:
    local-zfs:
      pool: "tank/proxmox"  # Custom ZFS pool
```

### Cluster Deployment
```yaml
proxmox_config:
  cluster_name: "production-cluster"
  network_config:
    cluster_network: true
    management_bridge: "vmbr0"
```

## Post-Installation

### Access Web Interface
```
https://<server-ip>:8006
Login: root@pam
```

### Create First VM
1. Upload ISO to `local` storage
2. Create VM with `local-zfs` disk storage
3. Enjoy ZFS snapshots and compression!

### Join Cluster
```bash
# On existing cluster node
pvecm create cluster-name

# On new node
pvecm join <cluster-ip>
```

## Architecture Details

### Integration with Z-FORGE
The Proxmox integration seamlessly extends Z-FORGE's module system:

```python
# Build sequence automatically includes Proxmox modules
PROXMOX_SEQUENCE = [
    'SystemPrerequisites',    # Base system
    'ZFSBuild',              # ZFS installation
    'ProxmoxRepoSetup',      # Add Proxmox repos
    'ProxmoxPackageInstall', # Install Proxmox VE
    'ProxmoxStorageConfig',  # Configure ZFS for VMs
    'ProxmoxNetworkConfig',  # Setup bridges
    'ProxmoxServiceConfig',  # Enable services
    'ProxmoxClusterSetup',   # Cluster preparation
    'ISOGeneration'          # Create bootable ISO
]
```

### Storage Benefits
- **Snapshots**: Instant VM snapshots with ZFS
- **Compression**: LZ4 compression reduces storage usage
- **Deduplication**: Optional for template storage
- **Encryption**: Native ZFS encryption support
- **Replication**: Built-in disaster recovery

### Performance Optimizations
- **VM Zvols**: 16k volblocksize for database workloads
- **Container Datasets**: 128k recordsize for file storage
- **ARC Tuning**: Optimized for virtualization workloads
- **L2ARC**: Optional SSD cache configuration

## Files Created

### Modules
```
builder/modules/
├── proxmox_repo_setup.py      # Repository configuration
├── proxmox_package_install.py # Package installation
├── proxmox_storage_config.py  # Storage setup
├── proxmox_network_config.py  # Network configuration
├── proxmox_service_config.py  # Service management
└── proxmox_cluster_setup.py   # Cluster preparation
```

### Configuration
```
config/
└── proxmox_node.yaml         # Proxmox build configuration
```

### Tests
```
proxmox_integration/
├── test_proxmox_integration.py  # Unit tests
├── test_proxmox_build.sh       # Integration tests
├── validate_proxmox_install.py # Validation tests
└── proxmox_perf_test.sh        # Performance tests
```

### Documentation
```
proxmox_integration/
├── PROXMOX_USER_GUIDE.md      # User installation guide
├── PROXMOX_ADMIN_GUIDE.md     # Administrator guide  
├── PROXMOX_DEVELOPER_GUIDE.md # Developer documentation
└── PROXMOX_API_REFERENCE.md   # API and configuration reference
```

## Requirements

### Hardware
- **CPU**: 64-bit with VT-x/AMD-V support
- **RAM**: Minimum 8GB, recommended 32GB+
- **Storage**: 100GB+, enterprise SSDs recommended
- **Network**: Gigabit Ethernet minimum

### Software
- Supports all Z-FORGE target hardware
- UEFI and Legacy BIOS support
- Secure Boot compatible (with MOK)

## Development

The integration was developed by a **6-agent UltraThink team**:

1. **Architect**: Designed the integration layers
2. **Researcher**: Analyzed Proxmox requirements  
3. **Developer**: Created the 6 core modules
4. **Integrator**: Integrated with Z-FORGE build system
5. **Tester**: Created comprehensive test suite
6. **Documenter**: Generated complete documentation

### Contributing
1. Follow Z-FORGE module patterns
2. Add tests for new features
3. Update documentation
4. Maintain ZFS optimization focus

## Future Enhancements

From the main roadmap (`FUTURE_TODO.md`):
- [ ] **GPU Passthrough**: Automated configuration
- [ ] **Live Migration**: ZFS-aware VM migration
- [ ] **HA Templates**: Pre-configured HA resources
- [ ] **Backup Integration**: Time Machine style backups
- [ ] **Cloud Integration**: Hybrid cloud support

## Support

- **Issues**: Use Z-FORGE issue tracker
- **Documentation**: See `proxmox_integration/` guides
- **Community**: Proxmox community forums
- **Enterprise**: Proxmox subscription support

---

**Generated by UltraThink Multi-Agent System**  
*Architecture • Research • Development • Integration • Testing • Documentation*