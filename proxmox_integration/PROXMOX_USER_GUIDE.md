# Z-FORGE Proxmox VE Installation Guide

## Overview

Z-FORGE now supports direct installation as a Proxmox VE node, combining the power of ZFS-on-root with Proxmox's virtualization capabilities.

## Installation Options

### 1. Standalone Proxmox Node

Boot from the Z-FORGE ISO and select "Install as Proxmox VE Node" from the installation menu.

#### Features:
- Full Proxmox VE installation
- ZFS as primary storage backend
- Optimized for virtualization workloads
- Web interface on port 8006

### 2. Cluster-Ready Node

Select "Install as Proxmox Cluster Node" for systems that will join an existing cluster.

#### Features:
- Pre-configured for cluster joining
- Corosync already set up
- SSH keys generated
- Network bridges configured

## Post-Installation

### Accessing Proxmox

1. Open web browser to: https://<server-ip>:8006
2. Login with root credentials set during installation
3. Accept the self-signed certificate (or configure Let's Encrypt)

### Storage Configuration

Z-FORGE automatically configures:
- **local**: Directory storage for ISOs, templates, and backups
- **local-zfs**: ZFS storage for VMs and containers

### Creating Your First VM

1. Upload ISO to local storage
2. Create VM using the web interface
3. Select local-zfs for the VM disk
4. Start and enjoy ZFS features like snapshots!

## Advanced Features

### ZFS Optimization

The installation automatically optimizes ZFS for virtualization:
- 16K volblocksize for VM zvols
- LZ4 compression enabled
- ARC tuned for virtualization workloads

### Cluster Setup

To create a cluster:
```bash
pvecm create <cluster-name>
```

To join a cluster:
```bash
pvecm join <existing-node-ip>
```

## Troubleshooting

### Common Issues

1. **Web interface not accessible**
   - Check firewall: `pve-firewall status`
   - Verify services: `systemctl status pveproxy`

2. **Storage issues**
   - Check ZFS health: `zpool status`
   - Verify datasets: `zfs list`

3. **Network issues**
   - Check bridges: `ip addr show vmbr0`
   - Verify configuration: `/etc/network/interfaces`
