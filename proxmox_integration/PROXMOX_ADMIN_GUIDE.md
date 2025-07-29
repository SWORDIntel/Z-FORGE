# Proxmox VE on Z-FORGE Administrator Guide

## System Requirements

### Hardware
- CPU: 64-bit processor with virtualization support (Intel VT-x/AMD-V)
- RAM: Minimum 8GB, recommended 32GB+
- Storage: Minimum 100GB, recommended 500GB+ enterprise SSDs
- Network: Gigabit Ethernet, 10GbE recommended

### BIOS Settings
- Enable VT-x/AMD-V
- Enable VT-d/IOMMU for PCI passthrough
- Disable Secure Boot (or configure MOK)

## Deployment Options

### Single Node Deployment
Perfect for:
- Home labs
- Development environments
- Small production workloads

### Cluster Deployment
Recommended for:
- Production environments
- High availability requirements
- Load balancing needs

## Storage Best Practices

### ZFS Pool Design
```
rpool (mirror/raidz1/raidz2)
├── ROOT/pve-1      # Root filesystem
├── data            # VM/Container storage
│   ├── vm          # Virtual machine zvols
│   └── ct          # Container datasets
└── backup          # Backup storage
```

### Performance Tuning
```bash
# Set ARC max (50% of RAM)
echo "options zfs zfs_arc_max=17179869184" > /etc/modprobe.d/zfs.conf

# VM-specific settings
zfs set volblocksize=16k rpool/data/vm
zfs set compression=lz4 rpool/data
```

## Network Configuration

### Basic Bridge Setup
```
auto vmbr0
iface vmbr0 inet static
    address 192.168.1.10/24
    gateway 192.168.1.1
    bridge-ports eno1
    bridge-stp off
    bridge-fd 0
```

### VLAN Configuration
```
auto vmbr0.100
iface vmbr0.100 inet static
    address 10.100.0.1/24
    vlan-raw-device vmbr0
```

## Security Hardening

### Firewall Rules
```bash
# Enable firewall
pve-firewall enable

# Add management rule
pvesh create /cluster/firewall/rules   -type in -action ACCEPT   -source 192.168.1.0/24   -dest 192.168.1.10   -dport 8006   -proto tcp   -comment "Management access"
```

### Two-Factor Authentication
```bash
# Enable TOTP
pvesh set /access/users/root@pam -tfa type=totp
```

## Monitoring

### Built-in Monitoring
- CPU, Memory, Storage usage in web UI
- Task history and logs
- Cluster status dashboard

### External Monitoring
```bash
# Enable metrics export
pvesh set /cluster/options -metrics influxdb:server=192.168.1.50,port=8086
```

## Backup Strategy

### vzdump Configuration
```bash
# Create backup job
pvesh create /cluster/backup   -schedule "0 2 * * *"   -storage local   -mode snapshot   -compress zstd
```

### ZFS Snapshots
```bash
# Automated snapshots
zfs set com.sun:auto-snapshot=true rpool/data
```
