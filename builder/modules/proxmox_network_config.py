#!/usr/bin/env python3
# z-forge/builder/modules/proxmox_network_config.py

"""
Proxmox VE Network Configuration Module for Z-Forge.

This module configures networking for Proxmox VE.
"""

import subprocess
import logging
import re
from pathlib import Path
from typing import Dict, Any, Optional, List

class ProxmoxNetworkConfig:
    """Configures networking for Proxmox VE."""
    
    def __init__(self, workspace: Path, config: Dict[str, Any]) -> None:
        self.workspace = workspace
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)
        self.chroot_path = workspace / "chroot"
        
    def execute(self, resume_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Execute Proxmox network configuration."""
        self.logger.info("Configuring Proxmox VE networking...")
        
        try:
            # Detect network interfaces
            interfaces = self._detect_interfaces()
            
            # Configure network
            self._configure_network(interfaces)
            
            # Configure hostname
            self._configure_hostname()
            
            return {
                'status': 'success',
                'network_configured': True,
                'bridges': ['vmbr0'],
                'primary_interface': interfaces[0] if interfaces else None
            }
            
        except Exception as e:
            self.logger.error(f"Network configuration failed: {e}")
            return {
                'status': 'error',
                'error': str(e),
                'module': self.__class__.__name__
            }
            
    def _detect_interfaces(self) -> List[str]:
        """Detect available network interfaces"""
        self.logger.info("Detecting network interfaces...")
        
        # This would run in the live environment during installation
        # For now, return a default
        return ['eth0']
        
    def _configure_network(self, interfaces: List[str]):
        """Configure network interfaces"""
        network_cfg = self.chroot_path / "etc/network/interfaces"
        
        primary_if = interfaces[0] if interfaces else 'eth0'
        
        config_content = f"""# Network interface configuration
auto lo
iface lo inet loopback

auto {primary_if}
iface {primary_if} inet manual

auto vmbr0
iface vmbr0 inet dhcp
    bridge-ports {primary_if}
    bridge-stp off
    bridge-fd 0
    bridge-vlan-aware yes
    bridge-vids 2-4094

# Cluster network (optional)
#auto vmbr1
#iface vmbr1 inet static
#    address 10.10.10.1/24
#    bridge-ports none
#    bridge-stp off
#    bridge-fd 0
"""
        
        with open(network_cfg, 'w') as f:
            f.write(config_content)
            
        self.logger.info("Configured network interfaces")
        
    def _configure_hostname(self):
        """Configure hostname for Proxmox"""
        hostname = self.config.get('proxmox_config', {}).get('hostname', 'pve')
        domain = self.config.get('proxmox_config', {}).get('domain', 'local')
        
        # Set hostname
        hostname_file = self.chroot_path / "etc/hostname"
        with open(hostname_file, 'w') as f:
            f.write(f"{hostname}\n")
            
        # Update hosts file
        hosts_file = self.chroot_path / "etc/hosts"
        hosts_content = f"""127.0.0.1       localhost
127.0.1.1       {hostname}.{domain} {hostname}

# IPv6
::1             localhost ip6-localhost ip6-loopback
ff02::1         ip6-allnodes
ff02::2         ip6-allrouters
"""
        
        with open(hosts_file, 'w') as f:
            f.write(hosts_content)
