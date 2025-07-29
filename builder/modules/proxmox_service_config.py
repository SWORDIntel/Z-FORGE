#!/usr/bin/env python3
# z-forge/builder/modules/proxmox_service_config.py

"""
Proxmox VE Service Configuration Module for Z-Forge.

This module configures and enables Proxmox VE services.
"""

import subprocess
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List

class ProxmoxServiceConfig:
    """Configures services for Proxmox VE."""
    
    def __init__(self, workspace: Path, config: Dict[str, Any]) -> None:
        self.workspace = workspace
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)
        self.chroot_path = workspace / "chroot"
        
    def execute(self, resume_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Execute Proxmox service configuration."""
        self.logger.info("Configuring Proxmox VE services...")
        
        try:
            # Configure systemd services
            self._configure_services()
            
            # Set up web interface certificate
            self._setup_certificates()
            
            # Configure firewall
            self._configure_firewall()
            
            # Create initial admin user
            self._create_admin_user()
            
            return {
                'status': 'success',
                'services_configured': True,
                'web_port': 8006,
                'admin_user': 'root@pam'
            }
            
        except Exception as e:
            self.logger.error(f"Service configuration failed: {e}")
            return {
                'status': 'error',
                'error': str(e),
                'module': self.__class__.__name__
            }
            
    def _configure_services(self):
        """Configure and enable Proxmox services"""
        services = [
            'pve-cluster',
            'pvedaemon',
            'pveproxy',
            'pvestatd',
            'pvescheduler',
            'pve-ha-lrm',
            'pve-ha-crm'
        ]
        
        for service in services:
            self.logger.info(f"Enabling service: {service}")
            subprocess.run([
                "chroot", str(self.chroot_path),
                "systemctl", "enable", service
            ], check=False)
            
    def _setup_certificates(self):
        """Set up SSL certificates for web interface"""
        self.logger.info("Setting up SSL certificates...")
        
        # Create certificate directory
        cert_dir = self.chroot_path / "etc/pve/nodes/pve"
        cert_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate self-signed certificate (will be replaced on first boot)
        subprocess.run([
            "chroot", str(self.chroot_path),
            "pvecm", "updatecerts", "--force"
        ], check=False)
        
    def _configure_firewall(self):
        """Configure Proxmox firewall"""
        self.logger.info("Configuring firewall...")
        
        # Enable firewall at datacenter level
        fw_cfg = self.chroot_path / "etc/pve/firewall/cluster.fw"
        fw_cfg.parent.mkdir(parents=True, exist_ok=True)
        
        with open(fw_cfg, 'w') as f:
            f.write("""[OPTIONS]
enable: 1
policy_in: DROP
policy_out: ACCEPT

[RULES]
IN ACCEPT -p tcp -dport 8006 -log nolog # Proxmox Web GUI
IN ACCEPT -p tcp -dport 22 -log nolog # SSH
IN ACCEPT -p tcp -dport 5900:5999 -log nolog # VNC Console
IN ACCEPT -p tcp -dport 3128 -log nolog # SPICE Console
""")
            
    def _create_admin_user(self):
        """Create initial admin user configuration"""
        self.logger.info("Setting up admin user...")
        
        # Create user.cfg
        user_cfg = self.chroot_path / "etc/pve/user.cfg"
        user_cfg.parent.mkdir(parents=True, exist_ok=True)
        
        with open(user_cfg, 'w') as f:
            f.write("""user:root@pam:1:0::::root@pam::::
""")
