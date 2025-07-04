#!/usr/bin/env python3
# calamares/modules/proxmoxconfig/main.py

"""
Proxmox Configuration Module
Configures Proxmox VE on the target system
Includes special optimizations for PowerEdge R420 and R730xd
"""

import subprocess
import os
import socket
import json
import shutil
from pathlib import Path
import libcalamares
from libcalamares.utils import check_target_env_call, target_env_call

def pretty_name():
    return "Configuring Proxmox VE"

def pretty_status_message():
    return "Setting up Proxmox VE environment..."

def run():
    """Configure Proxmox VE installation"""
    
    pool_name = libcalamares.globalstorage.value("install_pool")
    dataset = libcalamares.globalstorage.value("install_dataset")
    
    libcalamares.utils.debug(f"Configuring Proxmox on {pool_name}/{dataset}")
    
    try:
        # Detect Dell PowerEdge servers
        is_dell_r420 = detect_dell_r420()
        is_dell_r730xd = detect_dell_r730xd()
        
        if is_dell_r420:
            libcalamares.utils.debug("Dell PowerEdge R420 detected, applying specific optimizations")
        elif is_dell_r730xd:
            libcalamares.utils.debug("Dell PowerEdge R730xd detected, applying specific optimizations")
        
        # Configure networking
        configure_network(is_dell_r420, is_dell_r730xd)
        
        # Configure storage
        configure_storage(pool_name, is_dell_r420, is_dell_r730xd)
        
        # Setup Proxmox cluster
        setup_proxmox_cluster()
        
        # Apply ZFS tuning
        apply_zfs_tuning(is_dell_r420, is_dell_r730xd)
        
        # Configure services
        configure_services()
        
        # PowerEdge specific optimizations
        if is_dell_r420:
            optimize_for_dell_r420()
        elif is_dell_r730xd:
            optimize_for_dell_r730xd()
        
        # Write post-install notes
        create_post_install_notes(is_dell_r420, is_dell_r730xd)
        
        libcalamares.utils.debug("Proxmox configuration complete")
        return None
        
    except Exception as e:
        libcalamares.utils.error(f"Proxmox configuration failed: {str(e)}")
        return (f"Configuration failed",
                f"Failed to configure Proxmox VE: {str(e)}")

def detect_dell_r420():
    """Detect if we're running on a Dell PowerEdge R420"""
    
    # Check DMI information
    try:
        # Check product name from DMI
        if os.path.exists("/sys/class/dmi/id/product_name"):
            with open("/sys/class/dmi/id/product_name", "r") as f:
                product_name = f.read().strip()
                if "PowerEdge R420" in product_name:
                    return True

        # Check system vendor from DMI
        if os.path.exists("/sys/class/dmi/id/sys_vendor"):
            with open("/sys/class/dmi/id/sys_vendor", "r") as f:
                vendor = f.read().strip()
                if "Dell" in vendor:
                    # Check with dmidecode
                    try:
                        result = subprocess.run(["dmidecode", "-t", "system"], capture_output=True, text=True)
                        if "R420" in result.stdout:
                            return True
                    except Exception:
                        pass
    except Exception:
        pass
    
    # Check using IPMI if available
    try:
        result = subprocess.run(["ipmi-fru"], capture_output=True, text=True)
        if "R420" in result.stdout:
            return True
    except Exception:
        pass
    
    return False

def detect_dell_r730xd():
    """Detect if we're running on a Dell PowerEdge R730xd"""
    
    # Check DMI information
    try:
        # Check product name from DMI
        if os.path.exists("/sys/class/dmi/id/product_name"):
            with open("/sys/class/dmi/id/product_name", "r") as f:
                product_name = f.read().strip()
                if "PowerEdge R730xd" in product_name:
                    return True

        # Check system vendor from DMI
        if os.path.exists("/sys/class/dmi/id/sys_vendor"):
            with open("/sys/class/dmi/id/sys_vendor", "r") as f:
                vendor = f.read().strip()
                if "Dell" in vendor:
                    # Check with dmidecode
                    try:
                        result = subprocess.run(["dmidecode", "-t", "system"], capture_output=True, text=True)
                        if "R730xd" in result.stdout or "R730 XD" in result.stdout:
                            return True
                    except Exception:
                        pass
    except Exception:
        pass
    
    # Check using IPMI if available
    try:
        result = subprocess.run(["ipmi-fru"], capture_output=True, text=True)
        if "R730xd" in result.stdout or "R730 XD" in result.stdout:
            return True
    except Exception:
        pass
    
    return False

def configure_network(is_dell_r420=False, is_dell_r730xd=False):
    """Configure network for Proxmox"""
    
    libcalamares.utils.debug("Configuring network")
    
    # Get current hostname
    hostname = socket.gethostname()
    
    # Write hostname
    check_target_env_call(["hostnamectl", "set-hostname", hostname])
    
    # Configure hosts file
    hosts_content = f"""127.0.0.1    localhost
127.0.1.1    {hostname}.localdomain {hostname}

# IPv6
::1          localhost ip6-localhost ip6-loopback
ff02::1      ip6-allnodes
ff02::2      ip6-allrouters
"""
    
    target_hosts_path = os.path.join(libcalamares.globalstorage.value("rootMountPoint"), "etc/hosts")
    with open(target_hosts_path, 'w') as f:
        f.write(hosts_content)
    
    # Configure interfaces based on detected server model
    if is_dell_r420:
        # Dell R420 specific configuration
        interfaces_content = """# Network interfaces managed by Proxmox VE
# Special configuration for Dell PowerEdge R420

auto lo
iface lo inet loopback

# Default bridge configuration
auto vmbr0
iface vmbr0 inet dhcp
    bridge_ports em1
    bridge_stp off
    bridge_fd 0

# Additional bridges can be added as needed
# Uncomment and adjust the below examples if needed
#
#auto vmbr1
#iface vmbr1 inet static
#    address 192.168.1.1
#    netmask 255.255.255.0
#    bridge_ports em2
#    bridge_stp off
#    bridge_fd 0
"""
    elif is_dell_r730xd:
        # Dell R730xd typically has Intel X710/I350 NICs
        interfaces_content = """# Network interfaces managed by Proxmox VE
# Special configuration for Dell PowerEdge R730xd

auto lo
iface lo inet loopback

# Default bridge configuration
auto vmbr0
iface vmbr0 inet dhcp
    bridge_ports eno1
    bridge_stp off
    bridge_fd 0

# Additional bridges can be added as needed
# Typical R730xd has 4 network ports
#
#auto vmbr1
#iface vmbr1 inet static
#    address 192.168.1.1
#    netmask 255.255.255.0
#    bridge_ports eno2
#    bridge_stp off
#    bridge_fd 0
"""
    else:
        # Standard configuration
        interfaces_content = """# Network interfaces managed by Proxmox VE
auto lo
iface lo inet loopback

auto vmbr0
iface vmbr0 inet dhcp
    bridge_ports eth0
    bridge_stp off
    bridge_fd 0
"""
    
    target_interfaces_path = os.path.join(libcalamares.globalstorage.value("rootMountPoint"), "etc/network/interfaces")
    with open(target_interfaces_path, 'w') as f:
        f.write(interfaces_content)
    
    # Configure serial console for Dell servers
    if is_dell_r420 or is_dell_r730xd:
        # Configure GRUB for serial console
        grub_defaults = os.path.join(libcalamares.globalstorage.value("rootMountPoint"), "etc/default/grub")
        
        if os.path.exists(grub_defaults):
            # Backup original
            shutil.copy2(grub_defaults, f"{grub_defaults}.bak")
            
            # Read current content
            with open(grub_defaults, 'r') as f:
                grub_content = f.read()
            
            # Configure with specific parameters for each server
            if is_dell_r420:
                # R420 serial console config
                grub_content = grub_content.replace('GRUB_CMDLINE_LINUX=""', 
                                                  'GRUB_CMDLINE_LINUX="console=tty0 console=ttyS0,115200n8"')
            elif is_dell_r730xd:
                # R730xd has more CPU cores, add mitigations=auto,nosmt for better performance
                grub_content = grub_content.replace('GRUB_CMDLINE_LINUX=""', 
                                                  'GRUB_CMDLINE_LINUX="console=tty0 console=ttyS0,115200n8 mitigations=auto,nosmt"')
            
            # Common serial console settings
            grub_content = grub_content.replace('#GRUB_TERMINAL=console', 
                                              'GRUB_TERMINAL="console serial"')
            
            # Add serial command if not present
            if "GRUB_SERIAL_COMMAND" not in grub_content:
                grub_content += '\nGRUB_SERIAL_COMMAND="serial --speed=115200 --unit=0 --word=8 --parity=no --stop=1"\n'
                
            # Write updated content
            with open(grub_defaults, 'w') as f:
                f.write(grub_content)

def configure_storage(pool_name, is_dell_r420=False, is_dell_r730xd=False):
    """Configure ZFS storage for Proxmox"""
    
    libcalamares.utils.debug(f"Setting up storage with pool {pool_name}")
    
    # Create Proxmox storage configuration based on server model
    if is_dell_r420:
        # Dell R420 specific configuration with optimized settings
        storage_cfg = f"""# ZFS storage configuration for Proxmox VE on Dell PowerEdge R420
# Generated by Z-Forge installer

dir: local
    path /var/lib/vz
    content iso,vztmpl,backup

zfspool: {pool_name}
    pool {pool_name}
    sparse 1
    content images,rootdir
    nodes localhost

# Additional storage configurations for Dell R420
# Uncommend and modify as needed if you have hardware RAID

#lvmthin: local-lvm
#    thinpool data
#    vgname pve
#    content rootdir,images
#    nodes localhost
"""
    elif is_dell_r730xd:
        # Dell R730xd has more drive bays and often has both NVMe and SATA/SAS
        storage_cfg = f"""# ZFS storage configuration for Proxmox VE on Dell PowerEdge R730xd
# Generated by Z-Forge installer

dir: local
    path /var/lib/vz
    content iso,vztmpl,backup

zfspool: {pool_name}
    pool {pool_name}
    sparse 1
    content images,rootdir
    nodes localhost

# R730xd typical configurations - uncomment and modify as needed

# Local directory for ISO/template storage
#dir: local-fast
#    path /mnt/nvme/vz
#    content iso,vztmpl,backup

# NVME for high-performance VMs
#zfspool: nvmepool
#    pool nvmepool
#    sparse 1
#    content images
#    nodes localhost

# Hardware RAID if present
#lvmthin: local-raid
#    thinpool data
#    vgname pve
#    content rootdir,images
#    nodes localhost
"""
    else:
        # Standard configuration
        storage_cfg = f"""# ZFS storage configuration for Proxmox VE
# Generated by Z-Forge installer

dir: local
    path /var/lib/vz
    content iso,vztmpl,backup

zfspool: {pool_name}
    pool {pool_name}
    content images,rootdir
    nodes localhost
"""
    
    # Write storage.cfg
    target_storage_dir = os.path.join(libcalamares.globalstorage.value("rootMountPoint"), "etc/pve")
    os.makedirs(target_storage_dir, exist_ok=True)
    
    target_storage_path = os.path.join(target_storage_dir, "storage.cfg")
    with open(target_storage_path, 'w') as f:
        f.write(storage_cfg)
    
    # Create directory for VM storage
    target_vz_dir = os.path.join(libcalamares.globalstorage.value("rootMountPoint"), "var/lib/vz")
    os.makedirs(target_vz_dir, exist_ok=True)
    
    # Create VM images directory
    target_images_dir = os.path.join(libcalamares.globalstorage.value("rootMountPoint"), "var/lib/vz/images")
    os.makedirs(target_images_dir, exist_ok=True)
    
    # Configure storage for Dell servers
    if is_dell_r420:
        # Add optimized configuration for Dell PERC RAID controller
        target_udev_rules = os.path.join(libcalamares.globalstorage.value("rootMountPoint"), 
                                        "etc/udev/rules.d/60-dell-raid.rules")
        
        udev_rules = """# Optimized settings for Dell PowerEdge R420 RAID controllers
ACTION=="add", SUBSYSTEM=="block", ATTRS{vendor}=="DELL", ATTRS{model}=="PERC*", ATTR{queue/scheduler}="deadline"
ACTION=="add", SUBSYSTEM=="block", ATTRS{vendor}=="DELL", ATTRS{model}=="PERC*", ATTR{queue/read_ahead_kb}="1024"
ACTION=="add", SUBSYSTEM=="block", ATTRS{vendor}=="DELL", ATTRS{model}=="PERC*", ATTR{queue/nr_requests}="256"
"""
        
        with open(target_udev_rules, 'w') as f:
            f.write(udev_rules)
            
    elif is_dell_r730xd:
        # R730xd has more modern RAID controller and likely NVMe SSDs
        target_udev_rules = os.path.join(libcalamares.globalstorage.value("rootMountPoint"), 
                                        "etc/udev/rules.d/60-dell-r730xd.rules")
        
        udev_rules = """# Optimized settings for Dell PowerEdge R730xd storage
# PERC RAID controllers (H730, H730P)
ACTION=="add", SUBSYSTEM=="block", ATTRS{vendor}=="DELL", ATTRS{model}=="PERC*", ATTR{queue/scheduler}="mq-deadline"
ACTION=="add", SUBSYSTEM=="block", ATTRS{vendor}=="DELL", ATTRS{model}=="PERC*", ATTR{queue/read_ahead_kb}="2048"
ACTION=="add", SUBSYSTEM=="block", ATTRS{vendor}=="DELL", ATTRS{model}=="PERC*", ATTR{queue/nr_requests}="1024"

# NVMe drives
ACTION=="add", SUBSYSTEM=="block", KERNEL=="nvme*", ATTR{queue/scheduler}="none"
ACTION=="add", SUBSYSTEM=="block", KERNEL=="nvme*", ATTR{queue/read_ahead_kb}="4096"
ACTION=="add", SUBSYSTEM=="block", KERNEL=="nvme*", ATTR{queue/nr_requests}="4096"

# SSD drives 
ACTION=="add", SUBSYSTEM=="block", KERNEL=="sd*", ATTR{queue/rotational}=="0", ATTR{queue/scheduler}="mq-deadline"
ACTION=="add", SUBSYSTEM=="block", KERNEL=="sd*", ATTR{queue/rotational}=="0", ATTR{queue/read_ahead_kb}="256"
"""
        
        with open(target_udev_rules, 'w') as f:
            f.write(udev_rules)

def setup_proxmox_cluster():
    """Initialize Proxmox cluster"""
    
    # [No changes needed to this function]
    libcalamares.utils.debug("Setting up Proxmox cluster")
    
    # Create post-install script to set up cluster
    cluster_script = """#!/bin/bash
# Proxmox cluster setup script

# Create cluster if not exists
if [ ! -f /etc/pve/corosync.conf ]; then
    pvecm create zforge-cluster
fi

# Ensure services are enabled
systemctl enable pve-cluster
systemctl enable pvedaemon
systemctl enable pveproxy
systemctl enable pvestatd
systemctl enable pvenetcommit
systemctl enable spiceproxy
"""
    
    # Write script
    target_script_dir = os.path.join(libcalamares.globalstorage.value("rootMountPoint"), "usr/local/bin")
    os.makedirs(target_script_dir, exist_ok=True)
    
    target_script_path = os.path.join(target_script_dir, "pve-setup-cluster.sh")
    with open(target_script_path, 'w') as f:
        f.write(cluster_script)
    os.chmod(target_script_path, 0o755)
    
    # Add to startup
    rc_local_content = """#!/bin/bash
# rc.local for Proxmox VE setup

# Setup Proxmox cluster on first boot
if [ -f /usr/local/bin/pve-setup-cluster.sh ]; then
    /usr/local/bin/pve-setup-cluster.sh
    # Remove script after execution
    rm /usr/local/bin/pve-setup-cluster.sh
fi

exit 0
"""
    
    target_rc_local = os.path.join(libcalamares.globalstorage.value("rootMountPoint"), "etc/rc.local")
    with open(target_rc_local, 'w') as f:
        f.write(rc_local_content)
    os.chmod(target_rc_local, 0o755)

def apply_zfs_tuning(is_dell_r420=False, is_dell_r730xd=False):
    """Apply ZFS performance tuning"""
    
    libcalamares.utils.debug("Applying ZFS tuning")
    
    # Get benchmark results if available
    benchmark_results = libcalamares.globalstorage.value("zfs_benchmark_results")
    
    # Default tuning params based on system type
    if is_dell_r420:
        # R420 has typically 32-64GB RAM, adjust accordingly
        arc_max = "20G"  # Conservative setting for server with limited RAM
        compression = "zstd-3"  # Good balance between compression and CPU usage
    elif is_dell_r730xd:
        # R730xd typically has 64-384GB RAM, can use more for ARC
        arc_max = "32G"  # More generous for server with more RAM
        compression = "zstd-6"  # Better compression with more CPU cores
    else:
        # Default values for other systems
        arc_max = "8G"  # Default to 8GB ARC
        compression = "zstd-3"  # Default compression
    
    # Apply benchmark results if available
    if benchmark_results:
        if "compression" in benchmark_results:
            compression = benchmark_results["compression"]
    
    # Create modprobe config
    modprobe_content = f"""# ZFS module parameters
options zfs zfs_arc_max={arc_max}
"""

    # Add Dell R420 specific optimizations
    if is_dell_r420:
        modprobe_content += """
# Dell PowerEdge R420 specific optimizations
options zfs zfs_prefetch_disable=1
options zfs zio_delay_max=10000
"""
    elif is_dell_r730xd:
        # R730xd can handle prefetch and has more memory
        modprobe_content += """
# Dell PowerEdge R730xd specific optimizations
options zfs zfs_prefetch_disable=0
options zfs zio_delay_max=5000
options zfs zfs_dirty_data_max_percent=30
"""
    
    target_modprobe_dir = os.path.join(libcalamares.globalstorage.value("rootMountPoint"), "etc/modprobe.d")
    os.makedirs(target_modprobe_dir, exist_ok=True)
    
    target_modprobe_path = os.path.join(target_modprobe_dir, "zfs.conf")
    with open(target_modprobe_path, 'w') as f:
        f.write(modprobe_content)
    
    # Create sysctl config - different optimizations for different servers
    if is_dell_r420:
        # R420 is a server, optimize for stability and throughput
        sysctl_content = """# ZFS performance tuning for Dell PowerEdge R420
vm.swappiness=10
vm.min_free_kbytes=1048576
vm.dirty_background_ratio=5
vm.dirty_ratio=10
vm.dirty_writeback_centisecs=500
kernel.sched_migration_cost_ns=5000000
kernel.sched_autogroup_enabled=0
"""
    elif is_dell_r730xd:
        # R730xd has more CPU cores and RAM, optimize for performance
        sysctl_content = """# ZFS performance tuning for Dell PowerEdge R730xd
vm.swappiness=5
vm.min_free_kbytes=2097152
vm.dirty_background_ratio=10
vm.dirty_ratio=20
vm.dirty_expire_centisecs=3000
vm.dirty_writeback_centisecs=300
kernel.sched_migration_cost_ns=5000000
kernel.sched_autogroup_enabled=0
# Network tuning for server workload
net.core.somaxconn=4096
net.core.netdev_max_backlog=4000
net.ipv4.tcp_max_syn_backlog=4096
net.ipv4.tcp_fin_timeout=30
net.ipv4.tcp_keepalive_time=300
"""
    else:
        # Standard configuration
        sysctl_content = """# ZFS performance tuning
vm.swappiness=10
vm.min_free_kbytes=524288
vm.dirty_background_ratio=10
vm.dirty_ratio=20
kernel.sched_migration_cost_ns=5000000
"""
    
    target_sysctl_dir = os.path.join(libcalamares.globalstorage.value("rootMountPoint"), "etc/sysctl.d")
    os.makedirs(target_sysctl_dir, exist_ok=True)
    
    target_sysctl_path = os.path.join(target_sysctl_dir, "zfs-tuning.conf")
    with open(target_sysctl_path, 'w') as f:
        f.write(sysctl_content)
    
    # Create script to set ZFS properties after pool import
    zfs_tuning_script = f"""#!/bin/bash
# ZFS properties tuning script

# Set compression on datasets
zfs set compression={compression} rpool
"""
    
    # Add server-specific optimizations
    if is_dell_r420:
        zfs_tuning_script += """
# Dell PowerEdge R420 specific optimizations
zfs set atime=off rpool
zfs set primarycache=metadata rpool  # Server typically has smaller L1ARC for metadata
zfs set recordsize=128K rpool
"""
    elif is_dell_r730xd:
        zfs_tuning_script += """
# Dell PowerEdge R730xd specific optimizations
zfs set atime=off rpool
zfs set primarycache=all rpool  # R730xd has more RAM for caching
zfs set recordsize=128K rpool
zfs set logbias=throughput rpool

# Create specific dataset settings for VMs and containers if they exist
if zfs list -r rpool | grep -q "/vms"; then
    zfs set recordsize=64K rpool/vms
    zfs set logbias=throughput rpool/vms
fi

if zfs list -r rpool | grep -q "/ct"; then
    zfs set recordsize=16K rpool/ct
fi
"""
    
    target_script_path = os.path.join(libcalamares.globalstorage.value("rootMountPoint"), "usr/local/bin/zfs-tune.sh")
    with open(target_script_path, 'w') as f:
        f.write(zfs_tuning_script)
    os.chmod(target_script_path, 0o755)
    
    # Add to rc.local
    rc_local = os.path.join(libcalamares.globalstorage.value("rootMountPoint"), "etc/rc.local")
    with open(rc_local, 'r') as f:
        content = f.read()
    
    if "/usr/local/bin/zfs-tune.sh" not in content:
        new_content = content.replace("exit 0", "/usr/local/bin/zfs-tune.sh\nexit 0")
        with open(rc_local, 'w') as f:
            f.write(new_content)
    
    # Configure NVMe if available
    if os.path.exists("/dev/nvme0") or is_dell_r420 or is_dell_r730xd:
        # Configure NVMe parameters - different for each server
        if is_dell_r420:
            nvme_conf = """# NVMe optimizations for R420
options nvme_core io_timeout=4294967295
options nvme_core max_host_mem_size_mb=256
"""
        elif is_dell_r730xd:
            nvme_conf = """# NVMe optimizations for R730xd
options nvme_core io_timeout=4294967295
options nvme_core max_host_mem_size_mb=1024
options nvme_core admin_timeout=30
"""
        else:
            nvme_conf = """# NVMe optimizations
options nvme_core io_timeout=4294967295
options nvme_core max_host_mem_size_mb=512
"""
        
        target_nvme_path = os.path.join(target_modprobe_dir, "nvme.conf")
        with open(target_nvme_path, 'w') as f:
            f.write(nvme_conf)

def configure_services():
    """Configure system services"""
    
    # [No changes needed to this function]
    libcalamares.utils.debug("Configuring services")
    
    # Enable required services
    services = [
        "pve-cluster",
        "pvedaemon",
        "pveproxy",
        "pvestatd",
        "pvenetcommit",
        "spiceproxy"
    ]
    
    for service in services:
        check_target_env_call(["systemctl", "enable", service])
    
    # Disable subscription notice
    js_path = os.path.join(libcalamares.globalstorage.value("rootMountPoint"), 
                           "usr/share/javascript/proxmox-widget-toolkit/proxmoxlib.js")
    
    if os.path.exists(js_path):
        # Backup original file
        shutil.copy2(js_path, f"{js_path}.bak")
        
        # Disable subscription nag
        check_target_env_call(["sed", "-i", 
                               "s/.*Ext.Msg.show.*No valid subscription.*/void 0;/", 
                               js_path])

def optimize_for_dell_r420():
    """Apply Dell PowerEdge R420 specific optimizations"""
    
    # [Keep your existing R420 optimization function]
    libcalamares.utils.debug("Applying Dell PowerEdge R420 optimizations")
    
    target_root = libcalamares.globalstorage.value("rootMountPoint")
    
    # Install Dell tools
    check_target_env_call(["apt-get", "update"])
    check_target_env_call(["apt-get", "install", "-y", 
                           "ipmitools", "srvadmin-all", "lm-sensors", "megacli"])
    
    # Create Dell R420 optimization script
    dell_script = """#!/bin/bash
# Dell PowerEdge R420 Optimization Script

# Enable Dell services
if command -v srvadmin-services.sh &>/dev/null; then
    srvadmin-services.sh start || true
    systemctl enable dataeng || true
    systemctl enable dsm_om_connsvc || true
fi

# Configure IPMI
if command -v ipmitool &>/dev/null; then
    # Enable Serial Over LAN
    ipmitool sol set enabled true
    ipmitool sol set force-encryption false
    
    # Set serial port for system
    ipmitool raw 0x30 0x0 0x0 0x0 0x0 0x5
fi

# Configure CPU for performance
for cpu in /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor; do
    echo performance > $cpu
done

# Optimize NVMe if present
if [ -e /dev/nvme0n1 ]; then
    # Configure device parameters
    nvme set-feature /dev/nvme0n1 -f 7 -v 0  # Disable write-cache
    nvme set-feature /dev/nvme0n1 -f 10 -v 1 # Enable host memory buffer
    
    # Create cron job for regular SMART checks
    cat > /etc/cron.weekly/nvme-check << 'EOT'
#!/bin/bash
# Weekly NVMe health check
nvme smart-log /dev/nvme0n1 > /var/log/nvme-smart-log.txt
nvme health-check /dev/nvme0n1 || echo "NVMe health check failed"
EOT
    chmod +x /etc/cron.weekly/nvme-check
fi

# Configure RAID controller if present
if lspci | grep -i "PERC"; then
    # Create RAID monitoring script
    cat > /usr/local/bin/check_raid.sh << 'EOT'
#!/bin/bash
# Check RAID status
if command -v megacli &>/dev/null; then
    RAID_STATUS=$(megacli -LDInfo -Lall -aALL | grep "State" | awk '{print $3}')
    if [[ "$RAID_STATUS" != "Optimal" ]]; then
        logger -t raid_check "WARNING: RAID status is not optimal: $RAID_STATUS"
        echo "WARNING: RAID status is not optimal: $RAID_STATUS" | mail -s "RAID Warning on $(hostname)" root
    fi
fi
EOT
    chmod +x /usr/local/bin/check_raid.sh
    
    # Add to crontab
    echo "0 * * * * root /usr/local/bin/check_raid.sh" > /etc/cron.d/raid_check
fi

# Configure hardware sensors
if command -v sensors-detect &>/dev/null; then
    yes | sensors-detect
    systemctl enable lm-sensors
    systemctl start lm-sensors
fi

echo "Dell PowerEdge R420 optimization completed."
"""
    
    # Save script
    script_path = os.path.join(target_root, "usr/local/bin/r420-optimize.sh")
    with open(script_path, 'w') as f:
        f.write(dell_script)
    os.chmod(script_path, 0o755)
    
    # Add to rc.local
    rc_local = os.path.join(target_root, "etc/rc.local")
    with open(rc_local, 'r') as f:
        content = f.read()
    
    if "/usr/local/bin/r420-optimize.sh" not in content:
        new_content = content.replace("exit 0", "/usr/local/bin/r420-optimize.sh\nexit 0")
        with open(rc_local, 'w') as f:
            f.write(new_content)
    
    # Create udev rules for PCIe NVMe on Dell R420
    nvme_udev = """# Optimization for PCIe NVMe on Dell PowerEdge R420
ACTION=="add", SUBSYSTEM=="block", KERNEL=="nvme*", ATTR{queue/scheduler}="none"
ACTION=="add", SUBSYSTEM=="block", KERNEL=="nvme*", ATTR{queue/read_ahead_kb}="2048"
ACTION=="add", SUBSYSTEM=="block", KERNEL=="nvme*", ATTR{queue/nr_requests}="512"
"""
    
    udev_path = os.path.join(target_root, "etc/udev/rules.d/60-nvme-dell.rules")
    with open(udev_path, 'w') as f:
        f.write(nvme_udev)

def optimize_for_dell_r730xd():
    """Apply Dell PowerEdge R730xd specific optimizations"""
    
    libcalamares.utils.debug("Applying Dell PowerEdge R730xd optimizations")
    
    target_root = libcalamares.globalstorage.value("rootMountPoint")
    
    # Install Dell tools and other utilities
    check_target_env_call(["apt-get", "update"])
    check_target_env_call(["apt-get", "install", "-y", 
                         "ipmitool", "openipmi", "srvadmin-all", "lm-sensors", 
                         "nvme-cli", "smartmontools", "megacli", "snmp"])
    
    # Create R730xd optimization script
    dell_script = """#!/bin/bash
# Dell PowerEdge R730xd Optimization Script

# Enable Dell services
if command -v srvadmin-services.sh &>/dev/null; then
    srvadmin-services.sh start || true
    systemctl enable dataeng || true
    systemctl enable dsm_om_connsvc || true
fi

# Configure IPMI and iDRAC
if command -v ipmitool &>/dev/null; then
    # Enable Serial Over LAN
    ipmitool sol set enabled true
    ipmitool sol set privilege-level admin
    ipmitool sol set force-encryption false
    ipmitool sol set character-accumulate-level 5
    ipmitool sol set character-send-threshold 1
    
    # Configure iDRAC network if needed
    # Uncomment and modify as needed
    # ipmitool lan set 1 ipsrc dhcp
    
    # Set power profile to Performance
    ipmitool raw 0x30 0xce 0x00 0x00 0x05 0x00 0x00 0x00
fi

# Configure CPU for performance
for cpu in /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor; do
    echo performance > $cpu
done

# Create CPU performance service
cat > /etc/systemd/system/cpu-performance.service << 'EOT'
[Unit]
Description=Set CPU Governor to Performance
After=multi-user.target

[Service]
Type=oneshot
ExecStart=/bin/bash -c "echo performance | tee /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor"
RemainAfterExit=yes

[Install]
WantedBy=multi-user.target
EOT
systemctl enable cpu-performance.service

# Optimize NVMe if present
if [ -e /dev/nvme0 ]; then
    # Set up NVMe monitoring
    cat > /usr/local/bin/check_nvme.sh << 'EOT'
#!/bin/bash
# Check NVMe health
for nvme_dev in $(nvme list | grep "^/dev/nvme" | awk '{print $1}'); do
    # Get health info
    SMART=$(nvme smart-log $nvme_dev)
    CRITICAL=$(echo "$SMART" | grep critical_warning | awk '{print $3}')
    TEMP=$(echo "$SMART" | grep temperature | awk '{print $3}')
    USED=$(echo "$SMART" | grep percentage_used | awk '{print $3}')
    
    # Log status
    logger -t nvme-check "$nvme_dev: Temp=${TEMP}C, Used=${USED}%, Warning=${CRITICAL}"
    
    # Check for problems
    if [ "$CRITICAL" != "0" ]; then
        mail -s "NVMe Warning on $(hostname)" root <<< "Critical warning detected on $nvme_dev"
        exit 1
    fi
    
    if [ "$TEMP" -gt 75 ]; then
        mail -s "NVMe Temperature Warning on $(hostname)" root <<< "High temperature (${TEMP}C) on $nvme_dev"
    fi
    
    if [ "$USED" -gt 85 ]; then
        mail -s "NVMe Usage Warning on $(hostname)" root <<< "High usage (${USED}%) on $nvme_dev"
    fi
done
EOT
    chmod +x /usr/local/bin/check_nvme.sh
    
    # Add to crontab
    echo "0 */2 * * * root /usr/local/bin/check_nvme.sh" > /etc/cron.d/nvme_check
fi

# Configure RAID controller if present
if lspci | grep -i "PERC"; then
    # Create RAID monitoring script
    cat > /usr/local/bin/check_raid.sh << 'EOT'
#!/bin/bash
# Check RAID status
if command -v megacli &>/dev/null; then
    RAID_STATUS=$(megacli -LDInfo -Lall -aALL | grep "State" | awk '{print $3}')
    if [[ "$RAID_STATUS" != "Optimal" ]]; then
        logger -t raid_check "WARNING: RAID status is not optimal: $RAID_STATUS"
        mail -s "RAID Warning on $(hostname)" root <<< "RAID status: $RAID_STATUS"
        exit 1
    fi
    
    # Check for rebuilding arrays
    REBUILD=$(megacli -PDList -aALL | grep "Firmware state" | grep "Rebuild")
    if [ ! -z "$REBUILD" ]; then
        logger -t raid_check "RAID array is rebuilding; monitoring progress"
        PROGRESS=$(megacli -PDRbld -ShowProg -aALL | grep "Rebuilding")
        mail -s "RAID Rebuilding on $(hostname)" root <<< "$PROGRESS"
    fi
fi
EOT
    chmod +x /usr/local/bin/check_raid.sh
    
    # Add to crontab
    echo "0 * * * * root /usr/local/bin/check_raid.sh" > /etc/cron.d/raid_check
fi

# Create fan control script for R730xd
cat > /usr/local/bin/fan_control.sh << 'EOT'
#!/bin/bash
# Fan control for PowerEdge R730xd

# Get current temperature (average of all cores)
get_cpu_temp() {
    sensors | grep -i "Core" | grep "+" | awk '{sum+=$3} END {print sum/NR}' | sed 's/+//g' | sed 's/°C//g'
}

# Set minimum fan speed
set_min_fan_speed() {
    ipmitool raw 0x30 0x30 0x01 0x00
    ipmitool raw 0x30 0x30 0x02 0xff 0x10
}

# Set medium fan speed
set_med_fan_speed() {
    ipmitool raw 0x30 0x30 0x01 0x00
    ipmitool raw 0x30 0x30 0x02 0xff 0x20
}

# Set high fan speed
set_high_fan_speed() {
    ipmitool raw 0x30 0x30 0x01 0x00
    ipmitool raw 0x30 0x30 0x02 0xff 0x30
}

# Return to automatic fan control
set_auto_fan_control() {
    ipmitool raw 0x30 0x30 0x01 0x01
}

# Get current temperature
TEMP=$(get_cpu_temp)

# Apply fan profile based on temperature
if [ ! -z "$TEMP" ]; then
    if (( $(echo "$TEMP < 40" | bc -l) )); then
        set_min_fan_speed
    elif (( $(echo "$TEMP < 65" | bc -l) )); then
        set_med_fan_speed
    elif (( $(echo "$TEMP < 75" | bc -l) )); then
        set_high_fan_speed
    else
        set_auto_fan_control
    fi
else
    # If we can't get temp, use auto control
    set_auto_fan_control
fi
EOT
chmod +x /usr/local/bin/fan_control.sh

# Add fan control to cron
echo "*/5 * * * * root /usr/local/bin/fan_control.sh > /dev/null 2>&1" > /etc/cron.d/fan_control

# Set up hardware monitoring with lm-sensors
yes | sensors-detect
systemctl enable lm-sensors
systemctl start lm-sensors

# Create diagnostics script
cat > /usr/local/bin/r730xd-diag.sh << 'EOT'
#!/bin/bash
# PowerEdge R730xd Diagnostics Utility

echo "Dell PowerEdge R730xd Diagnostics"
echo "================================"
echo ""

echo "System Information:"
echo "------------------"
echo "Hostname: $(hostname)"
echo "OS: $(cat /etc/os-release | grep PRETTY_NAME | cut -d'"' -f2)"
echo "Kernel: $(uname -r)"
echo ""

echo "CPU Information:"
echo "---------------"
echo "$(lscpu | grep 'Model name\\|CPU(s)\\|Thread' | sed 's/^/  /')"
echo ""

echo "Memory Information:"
echo "------------------"
echo "$(free -h | sed 's/^/  /')"
echo ""

echo "Storage Devices:"
echo "---------------"
echo "$(lsblk -o NAME,SIZE,MODEL,SERIAL | sed 's/^/  /')"
echo ""

if command -v nvme &>/dev/null && [ -e /dev/nvme0 ]; then
    echo "NVMe Devices:"
    echo "------------"
    echo "$(nvme list | sed 's/^/  /')"
    echo ""
    
    # Show NVMe health
    echo "NVMe Health:"
    echo "-----------"
    for nvme_dev in $(nvme list | grep "^/dev" | awk '{print $1}'); do
        echo "  $nvme_dev:"
        nvme smart-log $nvme_dev | grep -E "critical_warning|temperature|percentage_used" | sed 's/^/    /'
        echo ""
    done
fi

if command -v megacli &>/dev/null; then
    echo "RAID Controller:"
    echo "--------------"
    echo "  RAID Status:"
    megacli -LDInfo -Lall -aALL | grep "State" | sed 's/^/    /'
    echo ""
    echo "  Physical Disks:"
    megacli -PDList -aALL | grep -E "Slot|Firmware state" | sed 's/^/    /'
    echo ""
fi

echo "ZFS Status:"
echo "-----------"
echo "$(zpool status | sed 's/^/  /')"
echo ""

echo "Network Interfaces:"
echo "-----------------"
echo "$(ip -br addr | sed 's/^/  /')"
echo ""

echo "Proxmox Status:"
echo "--------------"
echo "  Version: $(pveversion 2>/dev/null || echo "Proxmox not installed")"
echo ""

echo "System Diagnostics Completed"
EOT
chmod +x /usr/local/bin/r730xd-diag.sh

echo "Dell PowerEdge R730xd optimization completed."
"""
    
    # Save script
    script_path = os.path.join(target_root, "usr/local/bin/r730xd-optimize.sh")
    with open(script_path, 'w') as f:
        f.write(dell_script)
    os.chmod(script_path, 0o755)
    
    # Add to rc.local
    rc_local = os.path.join(target_root, "etc/rc.local")
    with open(rc_local, 'r') as f:
        content = f.read()
    
    if "/usr/local/bin/r730xd-optimize.sh" not in content:
        new_content = content.replace("exit 0", "/usr/local/bin/r730xd-optimize.sh\nexit 0")
        with open(rc_local, 'w') as f:
            f.write(new_content)
    
    # Create diagnostic desktop shortcut
    desktop_dir = os.path.join(target_root, "root/Desktop")
    os.makedirs(desktop_dir, exist_ok=True)
    
    shortcut = """[Desktop Entry]
Type=Application
Name=R730xd Diagnostics
Comment=Run system diagnostics
Exec=x-terminal-emulator -e "/usr/local/bin/r730xd-diag.sh; read -p 'Press Enter to close...'"
Icon=utilities-terminal
Terminal=false
Categories=System;
"""
    
    shortcut_path = os.path.join(desktop_dir, "r730xd-diagnostics.desktop")
    with open(shortcut_path, 'w') as f:
        f.write(shortcut)
    os.chmod(shortcut_path, 0o755)

def create_post_install_notes(is_dell_r420=False, is_dell_r730xd=False):
    """Create post-installation notes"""
    
    libcalamares.utils.debug("Creating post-install notes")
    
    post_install_notes = """# Z-Forge Proxmox VE - Post-Installation Notes

## System Configuration

Your Proxmox VE system has been installed with ZFS. The following configurations have been applied:

- ZFS pool with compression and optimized settings
- Network bridge (vmbr0) configured for VM networking
- Proxmox cluster initialized as 'zforge-cluster'
- Performance tuning applied for ZFS and system
"""

    if is_dell_r420:
        post_install_notes += """
## Dell PowerEdge R420 Specific Configuration

The following R420-specific optimizations have been applied:

- Serial console enabled (115200 baud, ttyS0)
- Dell OpenManage tools installed
- IPMI and iDRAC configuration
- NVMe PCIe optimizations
- CPU governor set to performance mode
- RAID controller monitoring (if detected)
"""
    elif is_dell_r730xd:
        post_install_notes += """
## Dell PowerEdge R730xd Specific Configuration

The following R730xd-specific optimizations have been applied:

- Serial console enabled (115200 baud, ttyS0)
- Dell OpenManage Server Administrator installed
- IPMI and iDRAC configuration with fan control
- NVMe and SSD optimizations
- CPU performance tuning with SMT optimizations
- RAID monitoring and alerts configured
- Hardware sensor monitoring enabled
"""

    post_install_notes += """
## First Steps

1. **Access the Web Interface**:
   - Open a browser and navigate to: https://<your-ip>:8006
   - Login with root credentials you set during installation

2. **Update System**:
   - From shell: `apt update && apt dist-upgrade`
   - Reboot after updates: `reboot`

3. **Create VMs and Containers**:
   - Use the web interface to create your first VM or container
   - Templates are automatically downloaded from Proxmox repositories

## Network Configuration

The system is configured with a bridge interface (vmbr0) that uses DHCP.
To configure static IP, edit `/etc/network/interfaces`.

## Storage

ZFS storage has been configured for VM and container storage.
Pool health can be monitored with: `zpool status`

## Backup and Recovery

- Recovery scripts are available in `/root/zforge-recovery/`
- Use `zfs snapshot` for point-in-time backups
- Explore Proxmox backup functionality through the web UI

## Additional Resources

- Proxmox Documentation: https://pve.proxmox.com/wiki/
- ZFS Documentation: https://openzfs.github.io/openzfs-docs/
"""

    if is_dell_r420:
        post_install_notes += """
## Dell PowerEdge R420 Resources

- Dell Server Documentation: https://www.dell.com/support/home/en-us/product-support/product/poweredge-r420/docs
- iDRAC User Guide: https://www.dell.com/support/home/en-us/product-support/product/idrac7-8-lifecycle-controller-v2.00.00.00/docs
- Hardware diagnostics are available in `/root/zforge-recovery/r420-diag.sh`
"""
    elif is_dell_r730xd:
        post_install_notes += """
## Dell PowerEdge R730xd Resources

- Dell Server Documentation: https://www.dell.com/support/home/en-us/product-support/product/poweredge-r730/docs
- iDRAC 8 User Guide: https://www.dell.com/support/home/en-us/product-support/product/idrac8-with-lc-v2.05.05.05/docs
- System diagnostics: Run `/usr/local/bin/r730xd-diag.sh` or use desktop shortcut
- Fan control can be adjusted in `/usr/local/bin/fan_control.sh`
"""

    post_install_notes += """
Thank you for using Z-Forge Proxmox VE!
"""
    
    notes_path = os.path.join(libcalamares.globalstorage.value("rootMountPoint"), "root/POST_INSTALL.md")
    with open(notes_path, 'w') as f:
        f.write(post_install_notes)
