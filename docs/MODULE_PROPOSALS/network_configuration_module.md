# Network Configuration Module for Z-FORGE

## Overview
A comprehensive Calamares module for network configuration during installation, essential for server deployments.

## Features

### Basic Configuration
- **Interface Detection**: Automatically detect all network interfaces
- **IP Configuration**: Static IP or DHCP selection per interface
- **DNS Settings**: Primary/secondary DNS servers
- **Gateway Configuration**: Default gateway setup
- **IPv6 Support**: Full IPv6 configuration options

### Advanced Features
- **VLAN Support**: 802.1Q VLAN tagging
- **Bridge Configuration**: Essential for Proxmox VMs
- **Network Bonding**: 802.3ad LACP, active-backup, balance-rr
- **MTU Settings**: Jumbo frame support
- **WiFi Configuration**: WPA2/WPA3 support for wireless interfaces

### Proxmox-Specific
```
auto vmbr0
iface vmbr0 inet static
    address 192.168.1.100/24
    gateway 192.168.1.1
    bridge-ports eno1
    bridge-stp off
    bridge-fd 0
    bridge-vlan-aware yes
    bridge-vids 2-4094
```

## UI Mockup
```
┌─────────────────────────────────────────────┐
│ Network Configuration                        │
├─────────────────────────────────────────────┤
│ Interface: eno1 (1 Gbps - Connected)        │
│ ○ DHCP                                      │
│ ● Static IP                                 │
│   IP Address: [192.168.1.100/24_____]      │
│   Gateway:    [192.168.1.1__________]      │
│   DNS 1:      [8.8.8.8______________]      │
│   DNS 2:      [8.8.4.4______________]      │
│                                             │
│ [x] Create bridge (vmbr0) for VMs          │
│ [ ] Enable VLAN awareness                   │
│                                             │
│ Additional Interfaces:                      │
│ eno2: [Configure] [Add to Bond]            │
│ eno3: [Configure] [Add to Bond]            │
│ eno4: [Configure] [Add to Bond]            │
└─────────────────────────────────────────────┘
```

## Implementation Priority: HIGH
Essential for headless server installations where network access is critical.