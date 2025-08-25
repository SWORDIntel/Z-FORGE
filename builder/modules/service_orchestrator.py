#!/usr/bin/env python3
"""
Service Orchestrator Module for Z-FORGE
Manages service deployment, configuration, and dependencies for enhanced builds
"""

import os
import json
import subprocess
from typing import Dict, List, Optional, Tuple
from pathlib import Path

from builder.core.module import BaseModule


class ServiceOrchestrator(BaseModule):
    """
    Orchestrates service installation and configuration for Z-FORGE builds
    Manages Netdata, Docker/Portainer, and optional KDE desktop environment
    """
    
    def __init__(self, config: Dict, chroot_path: Path = None):
        super().__init__(config, chroot_path)
        self.module_name = "service_orchestrator"
        
        # Service tiers define startup order and dependencies
        self.service_tiers = {
            'essential': ['netdata', 'docker'],
            'optional': ['kde'],
            'custom': []
        }
        
        # Service configurations
        self.service_configs = {
            'netdata': {
                'package': 'netdata',
                'service_name': 'netdata',
                'port': 19999,
                'autostart': True,
                'memory_limit': '512M',
                'requires': ['network-online.target']
            },
            'docker': {
                'package': 'docker.io',
                'service_name': 'docker',
                'autostart': True,
                'storage_driver': 'zfs',
                'requires': ['network.target', 'zfs.target']
            },
            'portainer': {
                'container': True,
                'image': 'portainer/portainer-ce:latest',
                'port': 9000,
                'autostart': True,
                'depends_on': 'docker'
            },
            'kde': {
                'packages': ['kde-plasma-desktop', 'sddm', 'xserver-xorg'],
                'service_name': 'sddm',
                'autostart': False,  # Critical: KDE must NOT autostart
                'display_manager': 'sddm'
            }
        }
        
        # Track service installation status
        self.installed_services = []
        self.failed_services = []
        
    def execute(self) -> bool:
        """Execute service orchestration"""
        try:
            self.logger.info("Starting Service Orchestrator")
            
            # Step 1: Prepare service environment
            if not self._prepare_environment():
                return False
                
            # Step 2: Install essential services
            if not self._install_essential_services():
                return False
                
            # Step 3: Install optional services based on config
            if not self._install_optional_services():
                self.logger.warning("Optional services installation had issues")
                
            # Step 4: Configure service dependencies
            if not self._configure_service_dependencies():
                return False
                
            # Step 5: Setup service monitoring
            if not self._setup_service_monitoring():
                self.logger.warning("Service monitoring setup incomplete")
                
            # Step 6: Validate service configuration
            if not self._validate_services():
                return False
                
            self.logger.success(f"Service Orchestrator completed: {len(self.installed_services)} services installed")
            return True
            
        except Exception as e:
            self.logger.error(f"Service Orchestrator failed: {e}")
            return False
    
    def _prepare_environment(self) -> bool:
        """Prepare chroot environment for service installation"""
        try:
            self.logger.info("Preparing service environment")
            
            # Create service directories
            service_dirs = [
                '/etc/systemd/system',
                '/etc/systemd/system/multi-user.target.wants',
                '/etc/docker',
                '/usr/local/bin',
                '/var/lib/netdata',
                '/var/lib/docker',
                '/opt/services'
            ]
            
            for dir_path in service_dirs:
                full_path = self.chroot_path / dir_path.lstrip('/')
                full_path.mkdir(parents=True, exist_ok=True)
                
            # Setup systemd for services
            if not self._setup_systemd_environment():
                self.logger.warning("Systemd setup incomplete")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Environment preparation failed: {e}")
            return False
    
    def _install_essential_services(self) -> bool:
        """Install essential services (Netdata, Docker)"""
        try:
            self.logger.info("Installing essential services")
            
            for service_name in self.service_tiers['essential']:
                if service_name in self.service_configs:
                    if self._install_service(service_name):
                        self.installed_services.append(service_name)
                    else:
                        self.failed_services.append(service_name)
                        self.logger.error(f"Failed to install essential service: {service_name}")
                        
            # Install Portainer after Docker
            if 'docker' in self.installed_services:
                if self._setup_portainer():
                    self.installed_services.append('portainer')
                    
            return len(self.failed_services) == 0
            
        except Exception as e:
            self.logger.error(f"Essential services installation failed: {e}")
            return False
    
    def _install_optional_services(self) -> bool:
        """Install optional services based on configuration"""
        try:
            self.logger.info("Installing optional services")
            
            # Check if KDE is enabled in config
            if self.config.get('services', {}).get('kde', {}).get('enable', False):
                if self._install_kde_desktop():
                    self.installed_services.append('kde')
                else:
                    self.logger.warning("KDE installation failed, continuing...")
                    
            return True
            
        except Exception as e:
            self.logger.error(f"Optional services installation failed: {e}")
            return False
    
    def _install_service(self, service_name: str) -> bool:
        """Install and configure a specific service"""
        try:
            config = self.service_configs[service_name]
            self.logger.info(f"Installing service: {service_name}")
            
            # Install package(s)
            if 'package' in config:
                cmd = f"apt-get install -y {config['package']}"
                if not self._run_in_chroot(cmd):
                    return False
            elif 'packages' in config:
                packages = ' '.join(config['packages'])
                cmd = f"apt-get install -y {packages}"
                if not self._run_in_chroot(cmd):
                    return False
                    
            # Configure service
            if 'service_name' in config:
                if config.get('autostart', True):
                    # Enable service for autostart
                    self._run_in_chroot(f"systemctl enable {config['service_name']}")
                else:
                    # Disable service autostart
                    self._run_in_chroot(f"systemctl disable {config['service_name']}")
                    
            # Service-specific configuration
            if service_name == 'netdata':
                self._configure_netdata()
            elif service_name == 'docker':
                self._configure_docker()
                
            return True
            
        except Exception as e:
            self.logger.error(f"Service installation failed for {service_name}: {e}")
            return False
    
    def _configure_netdata(self) -> bool:
        """Configure Netdata for ZFS monitoring"""
        try:
            self.logger.info("Configuring Netdata for ZFS monitoring")
            
            # Netdata configuration
            netdata_config = """
[global]
    memory mode = dbengine
    page cache size = 32M
    dbengine multihost disk space = 256

[plugins]
    python.d = yes
    charts.d = yes
    apps = yes
    
[plugin:proc:/sys/fs/zfs]
    zfs arcstats = yes
    zfs pool state = yes
"""
            
            config_path = self.chroot_path / 'etc/netdata/netdata.conf'
            config_path.parent.mkdir(parents=True, exist_ok=True)
            config_path.write_text(netdata_config)
            
            # Create systemd override for memory limit
            systemd_override = f"""
[Service]
MemoryLimit={self.service_configs['netdata']['memory_limit']}
Restart=on-failure
RestartSec=10s
"""
            override_dir = self.chroot_path / 'etc/systemd/system/netdata.service.d'
            override_dir.mkdir(parents=True, exist_ok=True)
            (override_dir / 'zforge.conf').write_text(systemd_override)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Netdata configuration failed: {e}")
            return False
    
    def _configure_docker(self) -> bool:
        """Configure Docker with ZFS storage driver"""
        try:
            self.logger.info("Configuring Docker with ZFS storage")
            
            # Docker daemon configuration
            docker_config = {
                "storage-driver": "zfs",
                "storage-opts": [
                    "zfs.fsname=rpool/docker"
                ],
                "log-driver": "json-file",
                "log-opts": {
                    "max-size": "10m",
                    "max-file": "3"
                },
                "live-restore": True,
                "userland-proxy": False
            }
            
            config_path = self.chroot_path / 'etc/docker/daemon.json'
            config_path.parent.mkdir(parents=True, exist_ok=True)
            config_path.write_text(json.dumps(docker_config, indent=2))
            
            # Create Docker ZFS dataset setup script
            setup_script = """#!/bin/bash
# Docker ZFS dataset setup
if command -v zfs >/dev/null 2>&1; then
    if ! zfs list rpool/docker >/dev/null 2>&1; then
        zfs create -o mountpoint=/var/lib/docker rpool/docker
        zfs set compression=lz4 rpool/docker
        zfs set atime=off rpool/docker
    fi
fi
"""
            script_path = self.chroot_path / 'usr/local/bin/docker-zfs-setup'
            script_path.write_text(setup_script)
            script_path.chmod(0o755)
            
            # Add to Docker service dependencies
            systemd_override = """
[Unit]
After=zfs.target
Wants=zfs.target

[Service]
ExecStartPre=/usr/local/bin/docker-zfs-setup
"""
            override_dir = self.chroot_path / 'etc/systemd/system/docker.service.d'
            override_dir.mkdir(parents=True, exist_ok=True)
            (override_dir / 'zfs-storage.conf').write_text(systemd_override)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Docker configuration failed: {e}")
            return False
    
    def _setup_portainer(self) -> bool:
        """Setup Portainer container management"""
        try:
            self.logger.info("Setting up Portainer CE")
            
            # Create Portainer startup script
            portainer_script = """#!/bin/bash
# Portainer CE startup script
docker volume create portainer_data 2>/dev/null || true
docker run -d \\
    -p 8000:8000 \\
    -p 9000:9000 \\
    --name=portainer \\
    --restart=always \\
    -v /var/run/docker.sock:/var/run/docker.sock \\
    -v portainer_data:/data \\
    portainer/portainer-ce:latest
"""
            
            script_path = self.chroot_path / 'usr/local/bin/start-portainer'
            script_path.write_text(portainer_script)
            script_path.chmod(0o755)
            
            # Create systemd service for Portainer
            portainer_service = """
[Unit]
Description=Portainer Container Management
After=docker.service
Requires=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
ExecStart=/usr/local/bin/start-portainer
ExecStop=docker stop portainer
ExecStopPost=docker rm portainer

[Install]
WantedBy=multi-user.target
"""
            
            service_path = self.chroot_path / 'etc/systemd/system/portainer.service'
            service_path.write_text(portainer_service)
            
            # Enable Portainer service
            self._run_in_chroot("systemctl enable portainer.service")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Portainer setup failed: {e}")
            return False
    
    def _install_kde_desktop(self) -> bool:
        """Install KDE Plasma desktop with manual startup"""
        try:
            self.logger.info("Installing KDE Plasma desktop (manual start only)")
            
            # Install KDE packages
            kde_packages = [
                'kde-plasma-desktop',
                'sddm',
                'xserver-xorg',
                'xserver-xorg-video-all',
                'xserver-xorg-input-all',
                'fonts-noto',
                'firefox-esr',
                'konsole',
                'dolphin'
            ]
            
            cmd = f"apt-get install -y {' '.join(kde_packages)}"
            if not self._run_in_chroot(cmd):
                return False
                
            # CRITICAL: Disable SDDM autostart
            self._run_in_chroot("systemctl disable sddm")
            self._run_in_chroot("systemctl mask sddm")
            
            # Create startx wrapper for KDE
            startx_script = """#!/bin/bash
# Start KDE Plasma desktop manually

echo "Starting KDE Plasma Desktop..."
echo "This may take a moment..."

# Ensure X server can start
export DISPLAY=:0

# Start KDE Plasma
exec startplasma-x11
"""
            
            script_path = self.chroot_path / 'usr/local/bin/start-kde'
            script_path.write_text(startx_script)
            script_path.chmod(0o755)
            
            # Create .xinitrc for KDE
            xinitrc_content = """#!/bin/sh
# .xinitrc for KDE Plasma

userresources=$HOME/.Xresources
usermodmap=$HOME/.Xmodmap
sysresources=/etc/X11/xinit/.Xresources
sysmodmap=/etc/X11/xinit/.Xmodmap

# Merge in defaults and keymaps
if [ -f $sysresources ]; then
    xrdb -merge $sysresources
fi

if [ -f $sysmodmap ]; then
    xmodmap $sysmodmap
fi

if [ -f "$userresources" ]; then
    xrdb -merge "$userresources"
fi

if [ -f "$usermodmap" ]; then
    xmodmap "$usermodmap"
fi

# Start KDE Plasma
exec startplasma-x11
"""
            
            xinitrc_path = self.chroot_path / 'etc/skel/.xinitrc'
            xinitrc_path.write_text(xinitrc_content)
            xinitrc_path.chmod(0o755)
            
            # Create startup instructions
            instructions = """
===========================================
KDE PLASMA DESKTOP INSTALLATION COMPLETE
===========================================

KDE Plasma has been installed but will NOT start automatically.
The system will boot to a text console (TTY) by default.

To start the KDE desktop environment:

1. Login at the console
2. Run one of these commands:
   - startx              (standard X11 startup)
   - start-kde           (custom KDE launcher)

To return to console:
   - Logout from KDE
   - Or press Ctrl+Alt+F2 for another TTY

===========================================
"""
            
            instructions_path = self.chroot_path / 'etc/motd.d/50-kde-instructions'
            instructions_path.parent.mkdir(parents=True, exist_ok=True)
            instructions_path.write_text(instructions)
            
            self.logger.success("KDE installed - manual startup only via 'startx' or 'start-kde'")
            return True
            
        except Exception as e:
            self.logger.error(f"KDE installation failed: {e}")
            return False
    
    def _configure_service_dependencies(self) -> bool:
        """Configure service dependency chains"""
        try:
            self.logger.info("Configuring service dependencies")
            
            # Create dependency management script
            dep_script = """#!/bin/bash
# Service dependency manager for Z-FORGE

check_service() {
    systemctl is-active --quiet "$1"
}

wait_for_service() {
    local service=$1
    local timeout=${2:-30}
    local count=0
    
    while ! check_service "$service"; do
        if [ $count -ge $timeout ]; then
            echo "Timeout waiting for $service"
            return 1
        fi
        sleep 1
        ((count++))
    done
    
    echo "$service is ready"
    return 0
}

# Service startup order
echo "Starting Z-FORGE services..."

# Start essential services
if systemctl is-enabled netdata >/dev/null 2>&1; then
    systemctl start netdata
fi

if systemctl is-enabled docker >/dev/null 2>&1; then
    wait_for_service "network-online.target"
    systemctl start docker
    
    if wait_for_service "docker"; then
        # Start Portainer after Docker
        if systemctl is-enabled portainer >/dev/null 2>&1; then
            systemctl start portainer
        fi
    fi
fi

echo "Service startup complete"
"""
            
            script_path = self.chroot_path / 'usr/local/bin/zforge-services'
            script_path.write_text(dep_script)
            script_path.chmod(0o755)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Dependency configuration failed: {e}")
            return False
    
    def _setup_service_monitoring(self) -> bool:
        """Setup monitoring for installed services"""
        try:
            self.logger.info("Setting up service monitoring")
            
            # Create health check script
            health_script = """#!/bin/bash
# Service health monitoring for Z-FORGE

SERVICES="netdata docker portainer"
FAILED_SERVICES=""

echo "Z-FORGE Service Health Check"
echo "============================"

for service in $SERVICES; do
    if systemctl is-enabled "$service" >/dev/null 2>&1; then
        if systemctl is-active --quiet "$service"; then
            echo "✓ $service: Running"
        else
            echo "✗ $service: Not running"
            FAILED_SERVICES="$FAILED_SERVICES $service"
        fi
    else
        echo "- $service: Not enabled"
    fi
done

# Check ports
echo ""
echo "Port Status:"
echo "-----------"

check_port() {
    local port=$1
    local service=$2
    if nc -z localhost $port 2>/dev/null; then
        echo "✓ Port $port ($service): Open"
    else
        echo "✗ Port $port ($service): Closed"
    fi
}

check_port 19999 "Netdata"
check_port 9000 "Portainer"

if [ -n "$FAILED_SERVICES" ]; then
    echo ""
    echo "Failed services:$FAILED_SERVICES"
    exit 1
fi

echo ""
echo "All services healthy!"
"""
            
            script_path = self.chroot_path / 'usr/local/bin/zforge-health'
            script_path.write_text(health_script)
            script_path.chmod(0o755)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Monitoring setup failed: {e}")
            return False
    
    def _setup_systemd_environment(self) -> bool:
        """Setup systemd environment for services"""
        try:
            # Create systemd-resolved stub if needed
            resolved_conf = self.chroot_path / 'etc/systemd/resolved.conf'
            if not resolved_conf.exists():
                resolved_conf.parent.mkdir(parents=True, exist_ok=True)
                resolved_conf.write_text("[Resolve]\nDNS=8.8.8.8 8.8.4.4\n")
                
            return True
            
        except Exception as e:
            self.logger.error(f"Systemd setup failed: {e}")
            return False
    
    def _validate_services(self) -> bool:
        """Validate service installations and configurations"""
        try:
            self.logger.info("Validating service configuration")
            
            validation_passed = True
            
            for service in self.installed_services:
                self.logger.info(f"Validating {service}")
                
                # Check service files exist
                if service in ['netdata', 'docker', 'portainer']:
                    service_file = self.chroot_path / f'etc/systemd/system/{service}.service'
                    lib_service = self.chroot_path / f'lib/systemd/system/{service}.service'
                    
                    if not service_file.exists() and not lib_service.exists():
                        if service != 'portainer':  # Portainer is custom
                            self.logger.warning(f"Service file missing for {service}")
                            validation_passed = False
                            
            # Summary
            self.logger.info(f"""
Service Installation Summary:
============================
Installed: {', '.join(self.installed_services) or 'None'}
Failed: {', '.join(self.failed_services) or 'None'}
Validation: {'PASSED' if validation_passed else 'FAILED'}

Access Points:
- Netdata: http://localhost:19999
- Portainer: http://localhost:9000
- KDE: Run 'startx' or 'start-kde' after login
""")
            
            return validation_passed
            
        except Exception as e:
            self.logger.error(f"Service validation failed: {e}")
            return False