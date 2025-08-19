#!/usr/bin/env python3
# z-forge/builder/modules/proxmox_network_config.py

"""
Proxmox VE 9 Network Configuration Module for Debian Trixie.
Configures networking for Proxmox VE 9 on Trixie.
"""

import subprocess
import logging
from pathlib import Path
from typing import Dict, Any, Optional

class ProxmoxNetworkConfig:
    """Configures Proxmox VE 9 networking for Debian Trixie."""
    
    def __init__(self, workspace: Path, config: Dict[str, Any]) -> None:
        self.workspace = workspace
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)
        self.chroot_path = workspace / "chroot"
        
    def execute(self, resume_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Execute Proxmox VE 9 network configuration for Trixie."""
        self.logger.info("Configuring Proxmox VE 9 networking for Debian Trixie...")
        
        try:
            self._configure_bridge_networking()
            self._setup_firewall_rules()
            self._configure_dhcp_server()
            
            return {
                'status': 'success',
                'network_configured': True,
                'bridge': 'vmbr0',
                'firewall': 'enabled'
            }
            
        except Exception as e:
            self.logger.error(f"Network configuration failed: {e}")
            return {
                'status': 'error',
                'error': str(e),
                'module': self.__class__.__name__
            }
    
    def _configure_bridge_networking(self):
        """Configure bridge networking for VMs/containers"""
        self.logger.info("Configuring bridge networking...")
        
        # Create network configuration for Trixie
        interfaces_file = self.chroot_path / "etc/network/interfaces"
        interfaces_content = """# Proxmox VE 9 Network Configuration for Trixie
# This file describes the network interfaces available on your system
# and how to activate them.

source /etc/network/interfaces.d/*

# The loopback network interface
auto lo
iface lo inet loopback

# The primary network interface (bridged for VMs)
auto vmbr0
iface vmbr0 inet dhcp
        bridge_ports eth0
        bridge_stp off
        bridge_fd 0
        bridge_maxwait 0
        # Trixie bridge optimizations
        bridge_hello 2
        bridge_maxage 12

# VM/Container bridge (internal)
auto vmbr1
iface vmbr1 inet static
        address 192.168.100.1/24
        bridge_ports none
        bridge_stp off
        bridge_fd 0
        # Internal bridge for VMs/containers
        post-up echo 1 > /proc/sys/net/ipv4/ip_forward
        post-up iptables -t nat -A POSTROUTING -s '192.168.100.0/24' -o vmbr0 -j MASQUERADE
        post-down iptables -t nat -D POSTROUTING -s '192.168.100.0/24' -o vmbr0 -j MASQUERADE
"""
        interfaces_file.write_text(interfaces_content)
        
        # Create systemd network service for PVE 9
        self._create_network_service()
    
    def _create_network_service(self):
        """Create systemd network service for PVE 9"""
        systemd_dir = self.chroot_path / "etc/systemd/system"
        systemd_dir.mkdir(parents=True, exist_ok=True)
        
        network_service = systemd_dir / "pve-network.service"
        network_service.write_text("""[Unit]
Description=Proxmox VE 9 Network Setup (Trixie)
After=network.target
Before=libvirtd.service

[Service]
Type=oneshot
ExecStart=/usr/share/zforge/pve-network-setup.sh
RemainAfterExit=yes

[Install]
WantedBy=multi-user.target
""")
        
        # Create network setup script
        script_dir = self.chroot_path / "usr/share/zforge"
        script_dir.mkdir(parents=True, exist_ok=True)
        
        network_script = script_dir / "pve-network-setup.sh"
        network_script.write_text("""#!/bin/bash
# Proxmox VE 9 Network Setup for Trixie

echo "Setting up Proxmox VE 9 networking on Trixie..."

# Ensure bridge module is loaded
modprobe bridge 2>/dev/null || true

# Create bridges if they don't exist
ip link show vmbr0 >/dev/null 2>&1 || {
    echo "Creating vmbr0 bridge..."
    ip link add name vmbr0 type bridge
    ip link set vmbr0 up
}

ip link show vmbr1 >/dev/null 2>&1 || {
    echo "Creating vmbr1 bridge..."
    ip link add name vmbr1 type bridge
    ip link set vmbr1 up
    ip addr add 192.168.100.1/24 dev vmbr1 2>/dev/null || true
}

# Enable IP forwarding
echo 1 > /proc/sys/net/ipv4/ip_forward

# Set up NAT for internal network
iptables -t nat -A POSTROUTING -s 192.168.100.0/24 -o vmbr0 -j MASQUERADE 2>/dev/null || true

echo "Proxmox VE 9 networking configured"
""")
        network_script.chmod(0o755)
    
    def _setup_firewall_rules(self):
        """Setup firewall rules for Proxmox VE 9"""
        self.logger.info("Setting up firewall rules...")
        
        firewall_dir = self.chroot_path / "etc/pve/firewall"
        firewall_dir.mkdir(parents=True, exist_ok=True)
        
        # Cluster firewall config
        cluster_fw = firewall_dir / "cluster.fw"
        cluster_fw.write_text("""# Proxmox VE 9 Cluster Firewall Configuration for Trixie
[OPTIONS]
enable: 1
policy_in: ACCEPT
policy_out: ACCEPT

[RULES]
# SSH access
IN SSH(ACCEPT) -source +management
# Web interface
IN ACCEPT -p tcp -dport 8006
# VNC/SPICE for VMs
IN ACCEPT -p tcp -dport 5900:5999
# Live migration
IN ACCEPT -p tcp -dport 60000:60050

# Internal cluster communication
GROUP management {
    10.0.0.0/8
    172.16.0.0/12
    192.168.0.0/16
}
""")
        
        # Host firewall config
        host_fw = firewall_dir / "host.fw"
        host_fw.write_text("""# Proxmox VE 9 Host Firewall Configuration for Trixie
[OPTIONS]
enable: 1
ndp: 1
nf_conntrack_allow_invalid: 0
nf_conntrack_max: 262144
nf_conntrack_tcp_timeout_established: 432000

[RULES]
# Basic services
IN SSH(ACCEPT)
IN ACCEPT -p tcp -dport 8006 -comment "PVE Web Interface"
IN ACCEPT -p tcp -dport 111 -comment "Portmapper"
IN ACCEPT -p tcp -dport 5404:5405 -comment "Corosync"
IN ACCEPT -p udp -dport 5404:5405 -comment "Corosync"
""")
    
    def _configure_dhcp_server(self):
        """Configure DHCP server for VM network"""
        self.logger.info("Configuring DHCP server...")
        
        # Install and configure dnsmasq for DHCP
        dhcp_config = self.chroot_path / "etc/dnsmasq.d/pve-dhcp.conf"
        dhcp_config.parent.mkdir(parents=True, exist_ok=True)
        
        dhcp_config.write_text("""# Proxmox VE 9 DHCP Configuration for VM network
# DHCP server for internal VM network on vmbr1
interface=vmbr1
dhcp-range=192.168.100.100,192.168.100.200,12h
dhcp-option=3,192.168.100.1
dhcp-option=6,192.168.100.1
domain=pve.local
# Don't listen on vmbr0 (host network)
except-interface=vmbr0
bind-interfaces
""")
        
        self.logger.info("DHCP server configured for VM network")