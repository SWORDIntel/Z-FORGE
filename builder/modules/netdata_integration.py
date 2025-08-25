#!/usr/bin/env python3
"""
Netdata Integration Module for Z-FORGE
Installs and configures Netdata monitoring with ZFS support
"""

import os
import json
import urllib.request
import tarfile
from pathlib import Path
from typing import Dict, Optional

from builder.modules.base_module import BaseModule
from builder.utils.logger import Logger
from builder.utils.command_runner import CommandRunner


class NetdataIntegration(BaseModule):
    """
    Installs Netdata monitoring system with optimized configuration for ZFS systems
    """
    
    def __init__(self, config: Dict, logger: Logger, chroot_path: Path):
        super().__init__(config, logger, chroot_path)
        self.module_name = "netdata_integration"
        self.logger = logger
        self.cmd_runner = CommandRunner(logger, chroot_path)
        
        # Netdata configuration
        self.netdata_version = "latest"
        self.netdata_port = config.get('services', {}).get('netdata', {}).get('port', 19999)
        self.enable_zfs = config.get('services', {}).get('netdata', {}).get('enable_zfs_monitoring', True)
        self.memory_limit = config.get('services', {}).get('netdata', {}).get('memory_limit', '512M')
        
    def execute(self) -> bool:
        """Execute Netdata installation and configuration"""
        try:
            self.logger.info("Starting Netdata Integration")
            
            # Step 1: Install dependencies
            if not self._install_dependencies():
                return False
                
            # Step 2: Install Netdata
            if not self._install_netdata():
                return False
                
            # Step 3: Configure Netdata
            if not self._configure_netdata():
                return False
                
            # Step 4: Setup ZFS monitoring
            if self.enable_zfs and not self._setup_zfs_monitoring():
                self.logger.warning("ZFS monitoring setup incomplete")
                
            # Step 5: Configure firewall
            if not self._configure_firewall():
                self.logger.warning("Firewall configuration skipped")
                
            # Step 6: Create custom dashboards
            if not self._create_dashboards():
                self.logger.warning("Dashboard creation skipped")
                
            # Step 7: Setup systemd service
            if not self._setup_systemd_service():
                return False
                
            self.logger.success(f"Netdata installed and configured on port {self.netdata_port}")
            return True
            
        except Exception as e:
            self.logger.error(f"Netdata integration failed: {e}")
            return False
    
    def _install_dependencies(self) -> bool:
        """Install Netdata dependencies"""
        try:
            self.logger.info("Installing Netdata dependencies")
            
            dependencies = [
                'curl',
                'wget',
                'gcc',
                'make',
                'autoconf',
                'automake',
                'pkg-config',
                'zlib1g-dev',
                'uuid-dev',
                'libuv1-dev',
                'liblz4-dev',
                'libjudy-dev',
                'libssl-dev',
                'libmnl-dev',
                'python3',
                'python3-yaml',
                'python3-mysqldb',
                'python3-psycopg2',
                'netcat-openbsd',
                'lm-sensors',
                'libipmimonitoring-dev',
                'libjson-c-dev'
            ]
            
            cmd = f"apt-get update && apt-get install -y {' '.join(dependencies)}"
            return self.cmd_runner.run_in_chroot(cmd)
            
        except Exception as e:
            self.logger.error(f"Dependency installation failed: {e}")
            return False
    
    def _install_netdata(self) -> bool:
        """Install Netdata using kickstart script"""
        try:
            self.logger.info("Installing Netdata")
            
            # Use Netdata's official installation script
            install_script = """#!/bin/bash
# Netdata installation script for Z-FORGE

# Download and run the official installer
export NETDATA_CLAIM_TOKEN=""
export NETDATA_CLAIM_ROOMS=""
export NETDATA_CLAIM_URL=""
export DISABLE_TELEMETRY=1

# Install Netdata without claiming to cloud
curl -s https://get.netdata.cloud/kickstart.sh > /tmp/netdata-kickstart.sh
bash /tmp/netdata-kickstart.sh --dont-wait --dont-start-it --disable-telemetry

# Ensure installation succeeded
if [ ! -f /usr/sbin/netdata ]; then
    echo "Netdata installation failed"
    exit 1
fi

echo "Netdata installed successfully"
"""
            
            script_path = self.chroot_path / 'tmp/install-netdata.sh'
            script_path.write_text(install_script)
            script_path.chmod(0o755)
            
            # Run installation
            if not self.cmd_runner.run_in_chroot("/tmp/install-netdata.sh"):
                # Fallback: Install from package repository
                self.logger.info("Trying package repository installation")
                return self.cmd_runner.run_in_chroot("apt-get install -y netdata netdata-plugins-bash")
                
            return True
            
        except Exception as e:
            self.logger.error(f"Netdata installation failed: {e}")
            return False
    
    def _configure_netdata(self) -> bool:
        """Configure Netdata for optimal performance"""
        try:
            self.logger.info("Configuring Netdata")
            
            # Main configuration
            netdata_config = f"""
# Netdata Configuration for Z-FORGE
# Generated by netdata_integration.py

[global]
    # Performance settings
    update every = 1
    memory mode = dbengine
    page cache size = 32M
    dbengine multihost disk space = 256
    
    # Network settings
    bind to = *
    default port = {self.netdata_port}
    disconnect idle clients after seconds = 3600
    
    # Security
    enable running new plugins = yes
    
[web]
    # Web server settings
    web files owner = root
    web files group = netdata
    enable gzip compression = yes
    gzip compression strategy = default
    gzip compression level = 3

[plugins]
    # Enable all plugins for comprehensive monitoring
    apps = yes
    cgroups = yes
    tc = yes
    idlejitter = yes
    proc = yes
    diskspace = yes
    python.d = yes
    charts.d = yes
    node.d = yes
    statsd = yes
    
[health]
    # Health monitoring
    enabled = yes
    default repeat warning = never
    default repeat critical = never
"""
            
            config_dir = self.chroot_path / 'etc/netdata'
            config_dir.mkdir(parents=True, exist_ok=True)
            
            config_file = config_dir / 'netdata.conf'
            config_file.write_text(netdata_config)
            
            # Python.d plugin configuration for additional monitoring
            python_config = """
# Python.d plugin configuration

# Enable these python.d modules
apache: no
nginx: yes
mysql: yes
postgres: yes
redis: yes
memcached: yes
mongodb: yes
elasticsearch: yes
docker: yes
"""
            
            python_dir = config_dir / 'python.d'
            python_dir.mkdir(parents=True, exist_ok=True)
            (python_dir / 'python.d.conf').write_text(python_config)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Netdata configuration failed: {e}")
            return False
    
    def _setup_zfs_monitoring(self) -> bool:
        """Setup ZFS-specific monitoring"""
        try:
            self.logger.info("Setting up ZFS monitoring for Netdata")
            
            # ZFS collector configuration
            zfs_config = """
# ZFS monitoring configuration for Netdata

# Enable ZFS statistics collection
[plugin:proc:/proc/spl/kstat/zfs]
    # ARC statistics
    arcstats = yes
    arc size = yes
    arc efficiency = yes
    
    # Pool statistics  
    pool state = yes
    pool space = yes
    pool health = yes
    
    # Dataset statistics
    dataset space = yes
    dataset quota = yes
    
    # ZIL statistics
    zil = yes
    
    # L2ARC statistics
    l2arc = yes

[plugin:proc:/sys/fs/zfs]
    # Enable all ZFS monitoring
    enabled = yes
    update every = 1
"""
            
            proc_dir = self.chroot_path / 'etc/netdata/conf.d'
            proc_dir.mkdir(parents=True, exist_ok=True)
            (proc_dir / 'proc.plugin.conf').write_text(zfs_config)
            
            # Create ZFS monitoring script
            zfs_monitor_script = """#!/bin/bash
# ZFS monitoring helper for Netdata

# Function to get ZFS pool status
get_pool_status() {
    if command -v zpool >/dev/null 2>&1; then
        zpool list -H -o name,health,size,alloc,free,cap
    fi
}

# Function to get ZFS ARC stats
get_arc_stats() {
    if [ -f /proc/spl/kstat/zfs/arcstats ]; then
        grep -E "^size|^c_max|^hits|^misses" /proc/spl/kstat/zfs/arcstats
    fi
}

# Function to get dataset stats
get_dataset_stats() {
    if command -v zfs >/dev/null 2>&1; then
        zfs list -H -o name,used,avail,refer,mountpoint
    fi
}

# Output for Netdata
case "$1" in
    pools)
        get_pool_status
        ;;
    arc)
        get_arc_stats
        ;;
    datasets)
        get_dataset_stats
        ;;
    *)
        echo "Usage: $0 {pools|arc|datasets}"
        ;;
esac
"""
            
            script_path = self.chroot_path / 'usr/libexec/netdata/plugins.d/zfs-stats.sh'
            script_path.parent.mkdir(parents=True, exist_ok=True)
            script_path.write_text(zfs_monitor_script)
            script_path.chmod(0o755)
            
            # Create custom ZFS dashboard configuration
            self._create_zfs_dashboard()
            
            return True
            
        except Exception as e:
            self.logger.error(f"ZFS monitoring setup failed: {e}")
            return False
    
    def _create_zfs_dashboard(self) -> bool:
        """Create custom ZFS dashboard for Netdata"""
        try:
            dashboard_config = """
# Custom ZFS Dashboard for Netdata
# This creates a dedicated ZFS monitoring section

[zfs_overview]
    name = ZFS Overview
    title = ZFS Storage System
    units = pools
    family = zfs
    context = zfs.pools
    priority = 1000

[zfs_arc]
    name = ZFS ARC Cache
    title = Adaptive Replacement Cache
    units = bytes
    family = zfs
    context = zfs.arc
    priority = 1001
    
[zfs_io]
    name = ZFS I/O
    title = ZFS Read/Write Operations
    units = operations/s
    family = zfs
    context = zfs.io
    priority = 1002
"""
            
            dashboard_dir = self.chroot_path / 'usr/share/netdata/web/dashboards'
            dashboard_dir.mkdir(parents=True, exist_ok=True)
            (dashboard_dir / 'zfs.html').write_text(dashboard_config)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Dashboard creation failed: {e}")
            return False
    
    def _configure_firewall(self) -> bool:
        """Configure firewall rules for Netdata"""
        try:
            self.logger.info(f"Configuring firewall for Netdata on port {self.netdata_port}")
            
            # Create iptables rules script
            firewall_script = f"""#!/bin/bash
# Firewall configuration for Netdata

# Check if iptables is available
if ! command -v iptables >/dev/null 2>&1; then
    echo "iptables not found, skipping firewall configuration"
    exit 0
fi

# Allow Netdata port
iptables -A INPUT -p tcp --dport {self.netdata_port} -j ACCEPT -m comment --comment "Netdata Web UI"

# Save rules if iptables-persistent is installed
if command -v netfilter-persistent >/dev/null 2>&1; then
    netfilter-persistent save
fi

echo "Firewall configured for Netdata on port {self.netdata_port}"
"""
            
            script_path = self.chroot_path / 'usr/local/bin/netdata-firewall'
            script_path.write_text(firewall_script)
            script_path.chmod(0o755)
            
            # Run firewall configuration
            self.cmd_runner.run_in_chroot("/usr/local/bin/netdata-firewall")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Firewall configuration failed: {e}")
            return False
    
    def _create_dashboards(self) -> bool:
        """Create custom monitoring dashboards"""
        try:
            self.logger.info("Creating custom Netdata dashboards")
            
            # System overview dashboard
            system_dashboard = """
<!DOCTYPE html>
<html>
<head>
    <title>Z-FORGE System Monitor</title>
    <meta charset="utf-8">
    <script type="text/javascript" src="dashboard.js"></script>
</head>
<body>
    <div class="netdata-container">
        <h1>Z-FORGE System Overview</h1>
        
        <!-- CPU Usage -->
        <div data-netdata="system.cpu"
             data-chart-library="dygraph"
             data-width="49%"
             data-height="200px"
             data-title="CPU Usage"></div>
             
        <!-- Memory Usage -->
        <div data-netdata="system.ram"
             data-chart-library="dygraph"
             data-width="49%"
             data-height="200px"
             data-title="Memory Usage"></div>
             
        <!-- Disk I/O -->
        <div data-netdata="system.io"
             data-chart-library="dygraph"
             data-width="49%"
             data-height="200px"
             data-title="Disk I/O"></div>
             
        <!-- Network Traffic -->
        <div data-netdata="system.net"
             data-chart-library="dygraph"
             data-width="49%"
             data-height="200px"
             data-title="Network Traffic"></div>
             
        <!-- ZFS ARC -->
        <div data-netdata="zfs.arc_size"
             data-chart-library="dygraph"
             data-width="100%"
             data-height="200px"
             data-title="ZFS ARC Cache"></div>
    </div>
</body>
</html>
"""
            
            dashboard_dir = self.chroot_path / 'usr/share/netdata/web/custom'
            dashboard_dir.mkdir(parents=True, exist_ok=True)
            (dashboard_dir / 'zforge-overview.html').write_text(system_dashboard)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Dashboard creation failed: {e}")
            return False
    
    def _setup_systemd_service(self) -> bool:
        """Setup systemd service for Netdata"""
        try:
            self.logger.info("Setting up Netdata systemd service")
            
            # Create systemd service file
            service_content = f"""
[Unit]
Description=Real time performance monitoring
Documentation=man:netdata
Documentation=https://github.com/netdata/netdata
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=netdata
Group=netdata
RuntimeDirectory=netdata
RuntimeDirectoryMode=0755
CacheDirectory=netdata
CacheDirectoryMode=0755
StateDirectory=netdata
StateDirectoryMode=0755
LogsDirectory=netdata
LogsDirectoryMode=0755
ExecStart=/usr/sbin/netdata -P /run/netdata/netdata.pid -D
ExecReload=/bin/kill -HUP $MAINPID
ExecStop=/bin/kill -TERM $MAINPID
Restart=on-failure
RestartSec=30
TimeoutStopSec=60

# Security settings
PrivateTmp=true
ProtectSystem=full
ProtectHome=true
NoNewPrivileges=true

# Resource limits
MemoryLimit={self.memory_limit}
CPUQuota=25%

# Capabilities
CapabilityBoundingSet=CAP_DAC_OVERRIDE CAP_SYS_PTRACE CAP_SYS_ADMIN
AmbientCapabilities=CAP_DAC_OVERRIDE CAP_SYS_PTRACE CAP_SYS_ADMIN

[Install]
WantedBy=multi-user.target
"""
            
            service_path = self.chroot_path / 'etc/systemd/system/netdata.service'
            service_path.parent.mkdir(parents=True, exist_ok=True)
            service_path.write_text(service_content)
            
            # Enable service
            self.cmd_runner.run_in_chroot("systemctl daemon-reload")
            self.cmd_runner.run_in_chroot("systemctl enable netdata.service")
            
            # Create Netdata user if not exists
            self.cmd_runner.run_in_chroot("useradd -r -g netdata -s /usr/sbin/nologin netdata 2>/dev/null || true")
            self.cmd_runner.run_in_chroot("groupadd -r netdata 2>/dev/null || true")
            
            # Set permissions
            self.cmd_runner.run_in_chroot("chown -R netdata:netdata /etc/netdata /var/lib/netdata /var/cache/netdata /var/log/netdata 2>/dev/null || true")
            
            self.logger.success(f"Netdata service configured and enabled on port {self.netdata_port}")
            return True
            
        except Exception as e:
            self.logger.error(f"Systemd service setup failed: {e}")
            return False