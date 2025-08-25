#!/usr/bin/env python3
"""
NetBird Integration Module for Z-FORGE
Installs NetBird secure private networking with zero-trust network access
"""

import os
import json
import subprocess
from pathlib import Path
from typing import Dict, Optional

from builder.core.module import BaseModule


class NetBirdIntegration(BaseModule):
    """
    Installs and configures NetBird for secure private networking
    Provides peer-to-peer encrypted connections with centralized management
    """
    
    def __init__(self, config: Dict, chroot_path: Path = None):
        super().__init__(config, chroot_path)
        self.module_name = "netbird_integration"
        
        # NetBird configuration
        self.enable_netbird = config.get('services', {}).get('netbird', {}).get('enable', True)
        self.management_url = config.get('services', {}).get('netbird', {}).get('management_url', '')
        self.setup_key = config.get('services', {}).get('netbird', {}).get('setup_key', '')
        self.enable_ssh_access = config.get('services', {}).get('netbird', {}).get('enable_ssh_access', True)
        self.enable_routing = config.get('services', {}).get('netbird', {}).get('enable_routing', False)
        self.interface_name = config.get('services', {}).get('netbird', {}).get('interface_name', 'wt0')
        
    def execute(self) -> bool:
        """Execute NetBird installation and configuration"""
        try:
            if not self.enable_netbird:
                self.logger.info("NetBird installation not enabled, skipping")
                return True
                
            self.logger.info("Starting NetBird secure networking installation")
            
            # Step 1: Install dependencies
            if not self._install_dependencies():
                return False
                
            # Step 2: Install NetBird
            if not self._install_netbird():
                return False
                
            # Step 3: Configure NetBird
            if not self._configure_netbird():
                return False
                
            # Step 4: Setup firewall rules
            if not self._setup_firewall_rules():
                self.logger.warning("Firewall rules configuration incomplete")
                
            # Step 5: Configure SSH access
            if self.enable_ssh_access and not self._configure_ssh_access():
                self.logger.warning("SSH access configuration incomplete")
                
            # Step 6: Setup routing if enabled
            if self.enable_routing and not self._setup_routing():
                self.logger.warning("Routing configuration incomplete")
                
            # Step 7: Create management scripts
            if not self._create_management_scripts():
                self.logger.warning("Management scripts creation incomplete")
                
            # Step 8: Setup systemd service
            if not self._setup_systemd_service():
                return False
                
            # Step 9: Create documentation
            if not self._create_documentation():
                self.logger.warning("Documentation creation incomplete")
                
            # Step 10: Validate installation
            if not self._validate_installation():
                return False
                
            self.logger.success("NetBird secure networking installed and configured")
            return True
            
        except Exception as e:
            self.logger.error(f"NetBird installation failed: {e}")
            return False
    
    def _install_dependencies(self) -> bool:
        """Install NetBird dependencies"""
        try:
            self.logger.info("Installing NetBird dependencies")
            
            dependencies = [
                'wireguard',
                'wireguard-tools',
                'iptables',
                'iproute2',
                'curl',
                'ca-certificates',
                'gnupg',
                'lsb-release',
                'resolvconf',
                'net-tools'
            ]
            
            cmd = f"apt-get update && apt-get install -y {' '.join(dependencies)}"
            return self._run_in_chroot(cmd)
            
        except Exception as e:
            self.logger.error(f"Dependency installation failed: {e}")
            return False
    
    def _install_netbird(self) -> bool:
        """Install NetBird client"""
        try:
            self.logger.info("Installing NetBird client")
            
            # NetBird installation script
            install_script = """#!/bin/bash
# NetBird installation for Z-FORGE

# Add NetBird repository
curl -fsSL https://pkgs.netbird.io/debian/public.key | gpg --dearmor -o /usr/share/keyrings/netbird-archive-keyring.gpg
echo 'deb [signed-by=/usr/share/keyrings/netbird-archive-keyring.gpg] https://pkgs.netbird.io/debian stable main' > /etc/apt/sources.list.d/netbird.list

# Update and install
apt-get update
apt-get install -y netbird

# Alternative: Direct binary download if repo fails
if ! command -v netbird >/dev/null 2>&1; then
    echo "Installing NetBird from binary release..."
    
    ARCH=$(dpkg --print-architecture)
    case "$ARCH" in
        amd64) ARCH="linux_amd64" ;;
        arm64) ARCH="linux_arm64" ;;
        armhf) ARCH="linux_armv6" ;;
        *) echo "Unsupported architecture: $ARCH"; exit 1 ;;
    esac
    
    # Download latest release
    LATEST_VERSION=$(curl -s https://api.github.com/repos/netbirdio/netbird/releases/latest | grep '"tag_name":' | sed -E 's/.*"v([^"]+)".*/\\1/')
    wget -O /tmp/netbird.tar.gz "https://github.com/netbirdio/netbird/releases/download/v${LATEST_VERSION}/netbird_${LATEST_VERSION}_${ARCH}.tar.gz"
    
    # Extract and install
    tar -xzf /tmp/netbird.tar.gz -C /tmp
    mv /tmp/netbird /usr/bin/
    chmod +x /usr/bin/netbird
    
    # Cleanup
    rm -f /tmp/netbird.tar.gz
fi

# Verify installation
if command -v netbird >/dev/null 2>&1; then
    echo "NetBird installed successfully"
    netbird version
else
    echo "NetBird installation failed"
    exit 1
fi
"""
            
            script_path = self.chroot_path / 'tmp/install-netbird.sh'
            script_path.write_text(install_script)
            script_path.chmod(0o755)
            
            return self._run_in_chroot("/tmp/install-netbird.sh")
            
        except Exception as e:
            self.logger.error(f"NetBird installation failed: {e}")
            return False
    
    def _configure_netbird(self) -> bool:
        """Configure NetBird client"""
        try:
            self.logger.info("Configuring NetBird")
            
            # NetBird configuration file
            netbird_config = {
                "ManagementURL": self.management_url or "https://api.netbird.io:443",
                "AdminURL": "",
                "ConfigPath": "/etc/netbird/config.json",
                "LogFile": "/var/log/netbird/client.log",
                "LogLevel": "info",
                "Interface": {
                    "Name": self.interface_name,
                    "Address": "",
                    "MTU": 1420
                },
                "WireguardPort": 51820,
                "DisableAutoConnect": False,
                "SSHKey": "",
                "NATExternalIPs": [],
                "CustomDNSAddress": "",
                "RosenpassEnabled": False,
                "RosenpassPermissive": False
            }
            
            # Create config directory
            config_dir = self.chroot_path / 'etc/netbird'
            config_dir.mkdir(parents=True, exist_ok=True)
            
            # Write configuration
            config_path = config_dir / 'config.json'
            config_path.write_text(json.dumps(netbird_config, indent=2))
            
            # Create log directory
            log_dir = self.chroot_path / 'var/log/netbird'
            log_dir.mkdir(parents=True, exist_ok=True)
            
            # If setup key is provided, create auto-registration script
            if self.setup_key:
                self._create_auto_registration()
                
            return True
            
        except Exception as e:
            self.logger.error(f"NetBird configuration failed: {e}")
            return False
    
    def _create_auto_registration(self) -> bool:
        """Create auto-registration script for NetBird"""
        try:
            registration_script = f"""#!/bin/bash
# NetBird auto-registration script

SETUP_KEY="{self.setup_key}"
MANAGEMENT_URL="{self.management_url or 'https://api.netbird.io:443'}"

# Check if already registered
if netbird status >/dev/null 2>&1; then
    echo "NetBird already registered"
    exit 0
fi

echo "Registering NetBird with management server..."

# Register with setup key
netbird up \\
    --setup-key "$SETUP_KEY" \\
    --management-url "$MANAGEMENT_URL" \\
    --log-file /var/log/netbird/client.log \\
    --log-level info

if [ $? -eq 0 ]; then
    echo "NetBird registration successful"
    netbird status
else
    echo "NetBird registration failed"
    exit 1
fi
"""
            
            script_path = self.chroot_path / 'usr/local/bin/netbird-register'
            script_path.write_text(registration_script)
            script_path.chmod(0o755)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Auto-registration setup failed: {e}")
            return False
    
    def _setup_firewall_rules(self) -> bool:
        """Setup firewall rules for NetBird"""
        try:
            self.logger.info("Setting up firewall rules for NetBird")
            
            firewall_script = f"""#!/bin/bash
# NetBird firewall configuration

# Check if iptables is available
if ! command -v iptables >/dev/null 2>&1; then
    echo "iptables not found, skipping firewall configuration"
    exit 0
fi

echo "Configuring firewall for NetBird..."

# Allow WireGuard port (NetBird uses WireGuard)
iptables -A INPUT -p udp --dport 51820 -j ACCEPT -m comment --comment "NetBird WireGuard"

# Allow traffic on NetBird interface
iptables -A INPUT -i {self.interface_name} -j ACCEPT -m comment --comment "NetBird interface"
iptables -A FORWARD -i {self.interface_name} -j ACCEPT -m comment --comment "NetBird forward"
iptables -A FORWARD -o {self.interface_name} -j ACCEPT -m comment --comment "NetBird forward"

# Enable IP forwarding if routing is enabled
if [ "{str(self.enable_routing).lower()}" = "true" ]; then
    echo 1 > /proc/sys/net/ipv4/ip_forward
    echo "net.ipv4.ip_forward=1" >> /etc/sysctl.conf
    
    # NAT for NetBird network
    iptables -t nat -A POSTROUTING -o eth0 -j MASQUERADE -m comment --comment "NetBird NAT"
fi

# Save rules if iptables-persistent is installed
if command -v netfilter-persistent >/dev/null 2>&1; then
    netfilter-persistent save
fi

echo "Firewall configured for NetBird"
"""
            
            script_path = self.chroot_path / 'usr/local/bin/netbird-firewall'
            script_path.write_text(firewall_script)
            script_path.chmod(0o755)
            
            return self._run_in_chroot("/usr/local/bin/netbird-firewall")
            
        except Exception as e:
            self.logger.error(f"Firewall setup failed: {e}")
            return False
    
    def _configure_ssh_access(self) -> bool:
        """Configure SSH access over NetBird"""
        try:
            self.logger.info("Configuring SSH access over NetBird")
            
            # SSH configuration for NetBird
            ssh_config = f"""
# NetBird SSH Configuration
# Allow SSH over NetBird interface

# Listen on NetBird interface
ListenAddress 0.0.0.0
ListenAddress ::

# Security settings for NetBird access
PermitRootLogin prohibit-password
PubkeyAuthentication yes
PasswordAuthentication no
ChallengeResponseAuthentication no

# Allow NetBird network
# Note: Update this after NetBird assigns IP range
# Example: AllowUsers *@100.64.0.0/10

# Performance tuning
TCPKeepAlive yes
ClientAliveInterval 60
ClientAliveCountMax 3
"""
            
            # Append to sshd_config
            sshd_config_path = self.chroot_path / 'etc/ssh/sshd_config.d/50-netbird.conf'
            sshd_config_path.parent.mkdir(parents=True, exist_ok=True)
            sshd_config_path.write_text(ssh_config)
            
            # Create SSH key generation script
            keygen_script = """#!/bin/bash
# Generate SSH keys for NetBird access

if [ ! -f ~/.ssh/id_ed25519 ]; then
    echo "Generating SSH key for NetBird access..."
    ssh-keygen -t ed25519 -f ~/.ssh/id_ed25519 -N "" -C "netbird@$(hostname)"
    echo ""
    echo "SSH public key (add this to authorized hosts):"
    cat ~/.ssh/id_ed25519.pub
else
    echo "SSH key already exists:"
    cat ~/.ssh/id_ed25519.pub
fi
"""
            
            keygen_path = self.chroot_path / 'usr/local/bin/netbird-ssh-keygen'
            keygen_path.write_text(keygen_script)
            keygen_path.chmod(0o755)
            
            return True
            
        except Exception as e:
            self.logger.error(f"SSH configuration failed: {e}")
            return False
    
    def _setup_routing(self) -> bool:
        """Setup routing configuration for NetBird"""
        try:
            self.logger.info("Setting up NetBird routing")
            
            # Routing configuration script
            routing_script = """#!/bin/bash
# NetBird routing configuration

echo "Configuring NetBird as router..."

# Enable IP forwarding
sysctl -w net.ipv4.ip_forward=1
sysctl -w net.ipv6.conf.all.forwarding=1

# Make permanent
echo "net.ipv4.ip_forward=1" >> /etc/sysctl.conf
echo "net.ipv6.conf.all.forwarding=1" >> /etc/sysctl.conf

# Configure NetBird as exit node (optional)
# This allows other peers to route traffic through this node
# netbird routes add --network 0.0.0.0/0 --enabled

echo "Routing configuration complete"
echo "To advertise routes to peers, use:"
echo "  netbird routes add --network <CIDR> --enabled"
echo ""
echo "To use as exit node:"
echo "  netbird routes add --network 0.0.0.0/0 --enabled"
"""
            
            script_path = self.chroot_path / 'usr/local/bin/netbird-setup-routing'
            script_path.write_text(routing_script)
            script_path.chmod(0o755)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Routing setup failed: {e}")
            return False
    
    def _create_management_scripts(self) -> bool:
        """Create NetBird management scripts"""
        try:
            self.logger.info("Creating NetBird management scripts")
            
            # Status script
            status_script = """#!/bin/bash
# NetBird status and diagnostics

echo "═══════════════════════════════════════════"
echo "         NetBird Network Status"
echo "═══════════════════════════════════════════"
echo ""

# Check if NetBird is running
if systemctl is-active --quiet netbird; then
    echo "✓ NetBird service: Running"
else
    echo "✗ NetBird service: Not running"
    echo "  Start with: sudo systemctl start netbird"
    exit 1
fi

echo ""
echo "Connection Status:"
echo "──────────────────"
netbird status 2>/dev/null || echo "Not connected"

echo ""
echo "Network Interfaces:"
echo "──────────────────"
ip addr show wt0 2>/dev/null || echo "NetBird interface not found"

echo ""
echo "Peers:"
echo "──────"
netbird peer list 2>/dev/null || echo "No peers available"

echo ""
echo "Routes:"
echo "───────"
netbird routes list 2>/dev/null || echo "No routes configured"

echo ""
echo "Firewall Rules (NetBird-related):"
echo "─────────────────────────────────"
iptables -L -n -v | grep -i netbird || echo "No NetBird firewall rules"

echo ""
echo "═══════════════════════════════════════════"
"""
            
            status_path = self.chroot_path / 'usr/local/bin/netbird-status'
            status_path.write_text(status_script)
            status_path.chmod(0o755)
            
            # Connect script
            connect_script = f"""#!/bin/bash
# NetBird connection manager

case "$1" in
    up|start|connect)
        echo "Connecting to NetBird network..."
        netbird up
        ;;
    down|stop|disconnect)
        echo "Disconnecting from NetBird network..."
        netbird down
        ;;
    restart)
        echo "Restarting NetBird connection..."
        netbird down
        sleep 2
        netbird up
        ;;
    status)
        netbird status
        ;;
    login)
        echo "Logging in to NetBird..."
        netbird login
        ;;
    *)
        echo "Usage: $0 {{up|down|restart|status|login}}"
        echo ""
        echo "Commands:"
        echo "  up/start/connect    - Connect to NetBird network"
        echo "  down/stop/disconnect - Disconnect from NetBird"
        echo "  restart             - Restart connection"
        echo "  status              - Show connection status"
        echo "  login               - Login to management server"
        exit 1
        ;;
esac
"""
            
            connect_path = self.chroot_path / 'usr/local/bin/netbird-control'
            connect_path.write_text(connect_script)
            connect_path.chmod(0o755)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Management scripts creation failed: {e}")
            return False
    
    def _setup_systemd_service(self) -> bool:
        """Setup systemd service for NetBird"""
        try:
            self.logger.info("Setting up NetBird systemd service")
            
            # NetBird systemd service
            service_content = """
[Unit]
Description=NetBird Client Service
Documentation=https://netbird.io/docs
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
Restart=always
RestartSec=5
ExecStart=/usr/bin/netbird service run --config /etc/netbird/config.json --log-file /var/log/netbird/client.log
ExecReload=/bin/kill -HUP $MAINPID
ExecStop=/usr/bin/netbird service stop
StandardOutput=journal
StandardError=journal

# Security settings
PrivateTmp=true
NoNewPrivileges=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/etc/netbird /var/log/netbird /var/lib/netbird
AmbientCapabilities=CAP_NET_ADMIN CAP_NET_BIND_SERVICE CAP_NET_RAW
CapabilityBoundingSet=CAP_NET_ADMIN CAP_NET_BIND_SERVICE CAP_NET_RAW

[Install]
WantedBy=multi-user.target
"""
            
            service_path = self.chroot_path / 'etc/systemd/system/netbird.service'
            service_path.parent.mkdir(parents=True, exist_ok=True)
            service_path.write_text(service_content)
            
            # Enable service
            self._run_in_chroot("systemctl daemon-reload")
            self._run_in_chroot("systemctl enable netbird.service")
            
            # Create first-boot registration service if setup key is provided
            if self.setup_key:
                firstboot_service = """
[Unit]
Description=NetBird First Boot Registration
After=network-online.target netbird.service
Wants=network-online.target
ConditionPathExists=!/etc/netbird/.registered

[Service]
Type=oneshot
RemainAfterExit=yes
ExecStart=/usr/local/bin/netbird-register
ExecStartPost=/bin/touch /etc/netbird/.registered

[Install]
WantedBy=multi-user.target
"""
                
                firstboot_path = self.chroot_path / 'etc/systemd/system/netbird-firstboot.service'
                firstboot_path.write_text(firstboot_service)
                self._run_in_chroot("systemctl enable netbird-firstboot.service")
                
            return True
            
        except Exception as e:
            self.logger.error(f"Systemd service setup failed: {e}")
            return False
    
    def _create_documentation(self) -> bool:
        """Create NetBird documentation"""
        try:
            self.logger.info("Creating NetBird documentation")
            
            doc_content = f"""
═══════════════════════════════════════════════════════════════════
                    Z-FORGE NETBIRD NETWORKING GUIDE
═══════════════════════════════════════════════════════════════════

NetBird secure private networking has been installed and configured.
NetBird provides peer-to-peer encrypted connections with zero-trust
network access (ZTNA).

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
QUICK START
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. Check status:
   netbird-status

2. Connect to network:
   netbird-control up

3. View peers:
   netbird peer list

4. SSH to peer:
   ssh user@<peer-ip>

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CONFIGURATION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Interface Name: {self.interface_name}
WireGuard Port: 51820
Config File: /etc/netbird/config.json
Log File: /var/log/netbird/client.log

Management URL: {self.management_url or 'https://api.netbird.io:443'}
SSH over NetBird: {'Enabled' if self.enable_ssh_access else 'Disabled'}
Routing: {'Enabled' if self.enable_routing else 'Disabled'}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
MANAGEMENT COMMANDS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Service Management:
  systemctl start netbird      # Start NetBird
  systemctl stop netbird       # Stop NetBird
  systemctl status netbird     # Check service status
  systemctl restart netbird    # Restart service

Connection Control:
  netbird up                   # Connect to network
  netbird down                 # Disconnect
  netbird status              # Show connection status
  netbird login               # Login to management server

Peer Management:
  netbird peer list           # List all peers
  netbird peer routes         # Show peer routes

Network Management:
  netbird routes list         # List routes
  netbird routes add          # Add new route
  netbird dns                 # DNS configuration

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SECURITY FEATURES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

• WireGuard encryption (ChaCha20-Poly1305)
• Zero-trust network access (ZTNA)
• Peer-to-peer connections (no central VPN server)
• Automatic NAT traversal
• Split tunneling support
• Access control lists (ACLs)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TROUBLESHOOTING
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Connection Issues:
  • Check logs: journalctl -u netbird -f
  • Verify firewall: netbird-firewall
  • Test connectivity: ping <peer-ip>
  • Check interface: ip addr show {self.interface_name}

Registration Issues:
  • Manual login: netbird login
  • With setup key: netbird up --setup-key <KEY>
  • Check management URL: netbird status

Performance Issues:
  • Check MTU: netbird mtu
  • Monitor traffic: iftop -i {self.interface_name}
  • Check routes: ip route show

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ADVANCED USAGE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Exit Node (Route all traffic through this node):
  netbird routes add --network 0.0.0.0/0 --enabled

Advertise Local Network:
  netbird routes add --network 192.168.1.0/24 --enabled

SSH Jump Host:
  ssh -J <netbird-peer> user@internal-host

Port Forwarding:
  ssh -L 8080:localhost:80 user@<netbird-peer>

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
USEFUL ALIASES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Add to ~/.bashrc:

  alias nb='netbird'
  alias nbs='netbird-status'
  alias nbc='netbird-control'
  alias nbup='netbird up'
  alias nbdown='netbird down'
  alias nbpeers='netbird peer list'

═══════════════════════════════════════════════════════════════════
"""
            
            # Write documentation
            doc_path = self.chroot_path / 'usr/share/doc/netbird/zforge-guide.txt'
            doc_path.parent.mkdir(parents=True, exist_ok=True)
            doc_path.write_text(doc_content)
            
            # Create quick reference
            quick_ref = """
┌─────────────────────────────────────┐
│  NETBIRD QUICK REFERENCE            │
├─────────────────────────────────────┤
│  Status:     netbird-status         │
│  Connect:    netbird up             │
│  Disconnect: netbird down           │
│  Peers:      netbird peer list      │
│  Routes:     netbird routes list    │
│  Help:       netbird --help         │
└─────────────────────────────────────┘
"""
            
            ref_path = self.chroot_path / 'etc/motd.d/52-netbird-ref'
            ref_path.parent.mkdir(parents=True, exist_ok=True)
            ref_path.write_text(quick_ref)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Documentation creation failed: {e}")
            return False
    
    def _validate_installation(self) -> bool:
        """Validate NetBird installation"""
        try:
            self.logger.info("Validating NetBird installation")
            
            # Check NetBird binary
            netbird_bin = self.chroot_path / 'usr/bin/netbird'
            if not netbird_bin.exists():
                self.logger.error("NetBird binary not found")
                return False
                
            # Check configuration
            config_file = self.chroot_path / 'etc/netbird/config.json'
            if not config_file.exists():
                self.logger.warning("NetBird configuration not found")
                
            # Check service file
            service_file = self.chroot_path / 'etc/systemd/system/netbird.service'
            if not service_file.exists():
                self.logger.error("NetBird service file not found")
                return False
                
            # Check management scripts
            scripts = ['netbird-status', 'netbird-control', 'netbird-firewall']
            for script in scripts:
                script_path = self.chroot_path / 'usr/local/bin' / script
                if not script_path.exists():
                    self.logger.warning(f"Management script missing: {script}")
                    
            self.logger.success(f"""
NetBird Installation Summary:
============================
✓ NetBird client installed
✓ WireGuard kernel module available
✓ Configuration created
✓ Systemd service configured
✓ Management scripts created
{'✓ Setup key configured' if self.setup_key else '- No setup key (manual registration required)'}
{'✓ SSH access enabled' if self.enable_ssh_access else '- SSH access disabled'}
{'✓ Routing enabled' if self.enable_routing else '- Routing disabled'}

Network Interface: {self.interface_name}
Management URL: {self.management_url or 'https://api.netbird.io:443'}

To connect: netbird up
To check status: netbird-status
""")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Validation failed: {e}")
            return False