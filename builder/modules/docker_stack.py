#!/usr/bin/env python3
"""
Docker Stack Module for Z-FORGE
Installs Docker CE and Portainer with ZFS storage driver integration
"""

import os
import json
import subprocess
from pathlib import Path
from typing import Dict, List, Optional

from builder.modules.base_module import BaseModule
from builder.utils.logger import Logger
from builder.utils.command_runner import CommandRunner


class DockerStack(BaseModule):
    """
    Installs and configures Docker CE with Portainer management interface
    Optimized for ZFS storage backend
    """
    
    def __init__(self, config: Dict, logger: Logger, chroot_path: Path):
        super().__init__(config, logger, chroot_path)
        self.module_name = "docker_stack"
        self.logger = logger
        self.cmd_runner = CommandRunner(logger, chroot_path)
        
        # Docker configuration
        self.storage_driver = config.get('services', {}).get('docker', {}).get('storage_driver', 'zfs')
        self.data_root = config.get('services', {}).get('docker', {}).get('data_root', '/var/lib/docker')
        self.enable_portainer = config.get('services', {}).get('docker', {}).get('enable_portainer', True)
        self.portainer_port = config.get('services', {}).get('docker', {}).get('portainer_port', 9000)
        self.compose_version = config.get('services', {}).get('docker', {}).get('compose_version', 'v2.24.0')
        
        # ZFS dataset for Docker
        self.zfs_pool = config.get('zfs', {}).get('pool_name', 'rpool')
        self.docker_dataset = f"{self.zfs_pool}/docker"
        
    def execute(self) -> bool:
        """Execute Docker stack installation and configuration"""
        try:
            self.logger.info("Starting Docker Stack installation")
            
            # Step 1: Install prerequisites
            if not self._install_prerequisites():
                return False
                
            # Step 2: Setup Docker repository
            if not self._setup_docker_repository():
                return False
                
            # Step 3: Install Docker CE
            if not self._install_docker_ce():
                return False
                
            # Step 4: Configure Docker with ZFS
            if not self._configure_docker_zfs():
                return False
                
            # Step 5: Install Docker Compose
            if not self._install_docker_compose():
                return False
                
            # Step 6: Setup Portainer
            if self.enable_portainer and not self._setup_portainer():
                self.logger.warning("Portainer setup incomplete")
                
            # Step 7: Configure systemd services
            if not self._configure_systemd():
                return False
                
            # Step 8: Create convenience scripts
            if not self._create_convenience_scripts():
                self.logger.warning("Convenience scripts not created")
                
            # Step 9: Validate installation
            if not self._validate_installation():
                return False
                
            self.logger.success("Docker stack installed and configured successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Docker stack installation failed: {e}")
            return False
    
    def _install_prerequisites(self) -> bool:
        """Install Docker prerequisites"""
        try:
            self.logger.info("Installing Docker prerequisites")
            
            prerequisites = [
                'apt-transport-https',
                'ca-certificates',
                'curl',
                'gnupg',
                'lsb-release',
                'software-properties-common',
                'iptables',
                'uidmap',
                'dbus-user-session',
                'fuse-overlayfs',
                'slirp4netns'
            ]
            
            cmd = f"apt-get update && apt-get install -y {' '.join(prerequisites)}"
            return self.cmd_runner.run_in_chroot(cmd)
            
        except Exception as e:
            self.logger.error(f"Prerequisites installation failed: {e}")
            return False
    
    def _setup_docker_repository(self) -> bool:
        """Setup Docker CE repository"""
        try:
            self.logger.info("Setting up Docker repository")
            
            # Add Docker's official GPG key
            gpg_setup = """#!/bin/bash
# Setup Docker repository

# Create keyrings directory
mkdir -p /etc/apt/keyrings

# Add Docker's official GPG key
curl -fsSL https://download.docker.com/linux/debian/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
chmod a+r /etc/apt/keyrings/docker.gpg

# Setup repository
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/debian $(lsb_release -cs) stable" > /etc/apt/sources.list.d/docker.list

# Update package index
apt-get update
"""
            
            script_path = self.chroot_path / 'tmp/setup-docker-repo.sh'
            script_path.write_text(gpg_setup)
            script_path.chmod(0o755)
            
            return self.cmd_runner.run_in_chroot("/tmp/setup-docker-repo.sh")
            
        except Exception as e:
            self.logger.error(f"Repository setup failed: {e}")
            return False
    
    def _install_docker_ce(self) -> bool:
        """Install Docker CE"""
        try:
            self.logger.info("Installing Docker CE")
            
            docker_packages = [
                'docker-ce',
                'docker-ce-cli',
                'containerd.io',
                'docker-buildx-plugin',
                'docker-compose-plugin'
            ]
            
            # Try official Docker CE first
            cmd = f"apt-get install -y {' '.join(docker_packages)}"
            if not self.cmd_runner.run_in_chroot(cmd):
                # Fallback to distribution Docker
                self.logger.info("Falling back to distribution Docker package")
                fallback_packages = [
                    'docker.io',
                    'docker-compose',
                    'containerd'
                ]
                cmd = f"apt-get install -y {' '.join(fallback_packages)}"
                if not self.cmd_runner.run_in_chroot(cmd):
                    return False
                    
            # Create docker group
            self.cmd_runner.run_in_chroot("groupadd docker 2>/dev/null || true")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Docker CE installation failed: {e}")
            return False
    
    def _configure_docker_zfs(self) -> bool:
        """Configure Docker with ZFS storage driver"""
        try:
            self.logger.info("Configuring Docker with ZFS storage")
            
            # Create ZFS dataset setup script
            zfs_setup_script = f"""#!/bin/bash
# Docker ZFS storage setup

# Check if ZFS is available
if ! command -v zfs >/dev/null 2>&1; then
    echo "ZFS not available, using default storage driver"
    exit 0
fi

# Create Docker dataset if it doesn't exist
if ! zfs list {self.docker_dataset} >/dev/null 2>&1; then
    echo "Creating ZFS dataset for Docker: {self.docker_dataset}"
    
    # Create parent dataset if needed
    if ! zfs list {self.zfs_pool} >/dev/null 2>&1; then
        echo "Warning: ZFS pool {self.zfs_pool} not found"
        echo "Docker will use default storage driver"
        exit 0
    fi
    
    # Create Docker dataset with optimal settings
    zfs create -o mountpoint={self.data_root} {self.docker_dataset}
    zfs set compression=lz4 {self.docker_dataset}
    zfs set atime=off {self.docker_dataset}
    zfs set xattr=sa {self.docker_dataset}
    zfs set acltype=posixacl {self.docker_dataset}
    
    echo "ZFS dataset created successfully"
fi

# Set permissions
chmod 700 {self.data_root}
"""
            
            script_path = self.chroot_path / 'usr/local/bin/docker-zfs-setup'
            script_path.write_text(zfs_setup_script)
            script_path.chmod(0o755)
            
            # Docker daemon configuration
            daemon_config = {
                "storage-driver": self.storage_driver,
                "storage-opts": [],
                "log-driver": "json-file",
                "log-opts": {
                    "max-size": "10m",
                    "max-file": "3"
                },
                "live-restore": True,
                "userland-proxy": False,
                "ip-forward": True,
                "iptables": True,
                "features": {
                    "buildkit": True
                },
                "default-ulimits": {
                    "nofile": {
                        "Name": "nofile",
                        "Hard": 64000,
                        "Soft": 64000
                    }
                }
            }
            
            # Add ZFS-specific options if using ZFS
            if self.storage_driver == "zfs":
                daemon_config["storage-opts"] = [
                    f"zfs.fsname={self.docker_dataset}"
                ]
            
            # Write daemon.json
            daemon_config_path = self.chroot_path / 'etc/docker/daemon.json'
            daemon_config_path.parent.mkdir(parents=True, exist_ok=True)
            daemon_config_path.write_text(json.dumps(daemon_config, indent=2))
            
            # Create systemd override for ZFS dependency
            systemd_override = """
[Unit]
After=zfs.target network-online.target
Wants=zfs.target network-online.target
RequiresMountsFor=/var/lib/docker

[Service]
# Run ZFS setup before starting Docker
ExecStartPre=/usr/local/bin/docker-zfs-setup
# Increase startup timeout for ZFS operations
TimeoutStartSec=180
"""
            
            override_dir = self.chroot_path / 'etc/systemd/system/docker.service.d'
            override_dir.mkdir(parents=True, exist_ok=True)
            (override_dir / 'zfs-override.conf').write_text(systemd_override)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Docker ZFS configuration failed: {e}")
            return False
    
    def _install_docker_compose(self) -> bool:
        """Install Docker Compose"""
        try:
            self.logger.info(f"Installing Docker Compose {self.compose_version}")
            
            # Create installation script
            compose_install = f"""#!/bin/bash
# Docker Compose installation

# Check if docker-compose plugin is already installed
if docker compose version >/dev/null 2>&1; then
    echo "Docker Compose plugin already installed"
    exit 0
fi

# Download Docker Compose standalone
COMPOSE_VERSION={self.compose_version}
ARCH=$(uname -m)

case "$ARCH" in
    x86_64)
        ARCH="x86_64"
        ;;
    aarch64)
        ARCH="aarch64"
        ;;
    *)
        echo "Unsupported architecture: $ARCH"
        exit 1
        ;;
esac

# Download binary
curl -L "https://github.com/docker/compose/releases/download/${{COMPOSE_VERSION}}/docker-compose-linux-${{ARCH}}" -o /usr/local/bin/docker-compose

# Make executable
chmod +x /usr/local/bin/docker-compose

# Create symlink for compatibility
ln -sf /usr/local/bin/docker-compose /usr/bin/docker-compose

# Verify installation
docker-compose --version || exit 1

echo "Docker Compose installed successfully"
"""
            
            script_path = self.chroot_path / 'tmp/install-compose.sh'
            script_path.write_text(compose_install)
            script_path.chmod(0o755)
            
            return self.cmd_runner.run_in_chroot("/tmp/install-compose.sh")
            
        except Exception as e:
            self.logger.error(f"Docker Compose installation failed: {e}")
            return False
    
    def _setup_portainer(self) -> bool:
        """Setup Portainer CE for Docker management"""
        try:
            self.logger.info("Setting up Portainer CE")
            
            # Portainer deployment script
            portainer_script = f"""#!/bin/bash
# Portainer CE deployment script

# Create Portainer volume
docker volume create portainer_data 2>/dev/null || true

# Stop and remove existing Portainer container if any
docker stop portainer 2>/dev/null || true
docker rm portainer 2>/dev/null || true

# Deploy Portainer CE
docker run -d \\
    -p 8000:8000 \\
    -p {self.portainer_port}:9000 \\
    -p 9443:9443 \\
    --name=portainer \\
    --restart=always \\
    -v /var/run/docker.sock:/var/run/docker.sock \\
    -v portainer_data:/data \\
    portainer/portainer-ce:latest

# Check if Portainer is running
sleep 5
if docker ps | grep -q portainer; then
    echo "Portainer deployed successfully"
    echo "Access Portainer at: http://localhost:{self.portainer_port}"
else
    echo "Portainer deployment failed"
    exit 1
fi
"""
            
            script_path = self.chroot_path / 'usr/local/bin/deploy-portainer'
            script_path.write_text(portainer_script)
            script_path.chmod(0o755)
            
            # Portainer systemd service
            portainer_service = f"""
[Unit]
Description=Portainer Container Management Platform
Documentation=https://docs.portainer.io/
After=docker.service
Requires=docker.service
PartOf=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/usr/local/bin
ExecStart=/usr/local/bin/deploy-portainer
ExecStop=/usr/bin/docker stop portainer
ExecStopPost=/usr/bin/docker rm -f portainer
Restart=on-failure
RestartSec=30

[Install]
WantedBy=multi-user.target
"""
            
            service_path = self.chroot_path / 'etc/systemd/system/portainer.service'
            service_path.write_text(portainer_service)
            
            # Portainer initialization script (runs on first boot)
            init_script = f"""#!/bin/bash
# Initialize Portainer on first boot

if [ ! -f /etc/portainer-initialized ]; then
    echo "Initializing Portainer..."
    
    # Wait for Docker to be ready
    for i in {{1..30}}; do
        if docker version >/dev/null 2>&1; then
            break
        fi
        sleep 2
    done
    
    # Deploy Portainer
    systemctl start portainer
    
    # Mark as initialized
    touch /etc/portainer-initialized
    
    echo "Portainer initialization complete"
fi
"""
            
            init_path = self.chroot_path / 'usr/local/bin/portainer-init'
            init_path.write_text(init_script)
            init_path.chmod(0o755)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Portainer setup failed: {e}")
            return False
    
    def _configure_systemd(self) -> bool:
        """Configure systemd services for Docker stack"""
        try:
            self.logger.info("Configuring systemd services")
            
            # Enable Docker service
            self.cmd_runner.run_in_chroot("systemctl enable docker.service")
            self.cmd_runner.run_in_chroot("systemctl enable containerd.service")
            
            # Enable Portainer if configured
            if self.enable_portainer:
                self.cmd_runner.run_in_chroot("systemctl enable portainer.service")
            
            # Create Docker startup verification script
            verify_script = """#!/bin/bash
# Verify Docker stack is operational

echo "Verifying Docker stack..."

# Check Docker daemon
if ! docker version >/dev/null 2>&1; then
    echo "ERROR: Docker daemon not responding"
    exit 1
fi

# Check Docker network
if ! docker network ls >/dev/null 2>&1; then
    echo "ERROR: Docker networking not functional"
    exit 1
fi

# Check ZFS storage (if configured)
if docker info 2>/dev/null | grep -q "Storage Driver: zfs"; then
    echo "✓ Docker using ZFS storage driver"
else
    echo "ℹ Docker using default storage driver"
fi

# Check Portainer
if docker ps 2>/dev/null | grep -q portainer; then
    echo "✓ Portainer is running"
else
    echo "ℹ Portainer not running (start with: systemctl start portainer)"
fi

echo "Docker stack verification complete"
"""
            
            verify_path = self.chroot_path / 'usr/local/bin/verify-docker-stack'
            verify_path.write_text(verify_script)
            verify_path.chmod(0o755)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Systemd configuration failed: {e}")
            return False
    
    def _create_convenience_scripts(self) -> bool:
        """Create convenience scripts for Docker management"""
        try:
            self.logger.info("Creating Docker convenience scripts")
            
            # Docker cleanup script
            cleanup_script = """#!/bin/bash
# Docker cleanup utility

echo "Docker Cleanup Utility"
echo "====================="

# Remove stopped containers
echo "Removing stopped containers..."
docker container prune -f

# Remove unused images
echo "Removing unused images..."
docker image prune -a -f

# Remove unused volumes
echo "Removing unused volumes..."
docker volume prune -f

# Remove unused networks
echo "Removing unused networks..."
docker network prune -f

# Show disk usage
echo ""
echo "Docker disk usage:"
docker system df

echo ""
echo "Cleanup complete!"
"""
            
            cleanup_path = self.chroot_path / 'usr/local/bin/docker-cleanup'
            cleanup_path.write_text(cleanup_script)
            cleanup_path.chmod(0o755)
            
            # Docker stats script
            stats_script = f"""#!/bin/bash
# Docker statistics dashboard

echo "Docker System Statistics"
echo "========================"

# System info
echo ""
echo "Docker Version:"
docker version --format "Server: {{{{.Server.Version}}}}"

# Storage info
echo ""
echo "Storage Driver:"
docker info --format "{{{{.Driver}}}}"

if docker info 2>/dev/null | grep -q "Storage Driver: zfs"; then
    echo "ZFS Dataset: {self.docker_dataset}"
    if command -v zfs >/dev/null 2>&1; then
        echo "ZFS Usage:"
        zfs list -H -o name,used,avail,refer {self.docker_dataset} 2>/dev/null
    fi
fi

# Container stats
echo ""
echo "Containers:"
echo "  Running: $(docker ps -q | wc -l)"
echo "  Total: $(docker ps -aq | wc -l)"

# Image stats
echo ""
echo "Images:"
echo "  Total: $(docker images -q | wc -l)"

# Volume stats
echo ""
echo "Volumes:"
echo "  Total: $(docker volume ls -q | wc -l)"

# Network stats
echo ""
echo "Networks:"
echo "  Total: $(docker network ls -q | wc -l)"

# Resource usage
echo ""
echo "Container Resource Usage:"
docker stats --no-stream --format "table {{{{.Container}}}}\\t{{{{.CPUPerc}}}}\\t{{{{.MemUsage}}}}"

# Portainer status
if docker ps | grep -q portainer; then
    echo ""
    echo "Portainer Status: ✓ Running on port {self.portainer_port}"
else
    echo ""
    echo "Portainer Status: ✗ Not running"
fi
"""
            
            stats_path = self.chroot_path / 'usr/local/bin/docker-stats'
            stats_path.write_text(stats_script)
            stats_path.chmod(0o755)
            
            # Docker quick start guide
            guide_content = f"""
========================================
Docker & Portainer Quick Start Guide
========================================

Docker has been installed with the following configuration:
- Storage Driver: {self.storage_driver}
- Data Root: {self.data_root}
- Portainer Port: {self.portainer_port}

BASIC COMMANDS:
--------------
docker ps                    # List running containers
docker images               # List images
docker run [image]          # Run a container
docker-compose up           # Start compose stack
docker-stats                # Show Docker statistics
docker-cleanup              # Clean unused resources

PORTAINER ACCESS:
----------------
Web UI: http://localhost:{self.portainer_port}
First-time setup:
1. Create admin user
2. Select "Docker" environment
3. Connect to local Docker

USEFUL ALIASES:
--------------
Add to ~/.bashrc:
alias dps='docker ps'
alias dimg='docker images'
alias dexec='docker exec -it'
alias dlog='docker logs -f'
alias dclean='docker-cleanup'

ZFS OPTIMIZATION:
----------------
Docker is configured to use ZFS datasets for optimal performance.
Dataset: {self.docker_dataset}

TROUBLESHOOTING:
---------------
verify-docker-stack         # Verify installation
systemctl status docker     # Check Docker service
systemctl status portainer  # Check Portainer service
docker info                 # Docker system information

========================================
"""
            
            guide_path = self.chroot_path / 'usr/share/doc/docker-ce/zforge-quickstart.txt'
            guide_path.parent.mkdir(parents=True, exist_ok=True)
            guide_path.write_text(guide_content)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Convenience scripts creation failed: {e}")
            return False
    
    def _validate_installation(self) -> bool:
        """Validate Docker stack installation"""
        try:
            self.logger.info("Validating Docker stack installation")
            
            # Check Docker binary
            docker_bin = self.chroot_path / 'usr/bin/docker'
            if not docker_bin.exists():
                self.logger.error("Docker binary not found")
                return False
                
            # Check Docker service file
            service_file = self.chroot_path / 'lib/systemd/system/docker.service'
            if not service_file.exists():
                service_file = self.chroot_path / 'etc/systemd/system/docker.service'
                if not service_file.exists():
                    self.logger.warning("Docker service file not found")
                    
            # Check daemon.json
            daemon_json = self.chroot_path / 'etc/docker/daemon.json'
            if not daemon_json.exists():
                self.logger.warning("Docker daemon.json not configured")
                
            # Validate configuration
            if daemon_json.exists():
                try:
                    config = json.loads(daemon_json.read_text())
                    self.logger.info(f"Docker configured with storage driver: {config.get('storage-driver', 'default')}")
                except json.JSONDecodeError:
                    self.logger.error("Invalid daemon.json configuration")
                    return False
                    
            self.logger.success(f"""
Docker Stack Installation Summary:
==================================
✓ Docker CE installed
✓ Storage driver: {self.storage_driver}
✓ Docker Compose installed
{'✓ Portainer configured on port ' + str(self.portainer_port) if self.enable_portainer else '- Portainer not enabled'}
✓ Systemd services configured
✓ Convenience scripts created

Access Points:
- Portainer: http://localhost:{self.portainer_port}
- Docker socket: /var/run/docker.sock
""")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Validation failed: {e}")
            return False