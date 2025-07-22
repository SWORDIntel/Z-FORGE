#!/usr/bin/env python3
# calamares/modules/zforgefinalize/main.py

"""
Z-Forge Finalization Module
Performs final system configuration and cleanup
"""

import subprocess
import os
import shutil
import json
from pathlib import Path
import libcalamares
from libcalamares.utils import check_target_env_call, target_env_call

def pretty_name():
    return "Finalizing Z-Forge Installation"

def pretty_status_message():
    return "Performing final configuration and cleanup..."

def run():
    """Finalize the installation"""

    libcalamares.utils.debug("Starting finalization")

    try:
        # Create logs directory
        create_logs_directory()

        # Capture system information
        capture_system_info()

        # Configure automatic updates
        setup_auto_updates()

        # Configure SSH security
        secure_ssh()

        # Create shortcuts
        create_shortcuts()

        # Final cleanup
        cleanup_installation()

        libcalamares.utils.debug("Finalization complete")
        return None

    except Exception as e:
        libcalamares.utils.error(f"Finalization failed: {str(e)}")
        return (f"Finalization failed",
                f"Failed to complete system setup: {str(e)}")

def create_logs_directory():
    """Create directory for logs and capture install log"""

    libcalamares.utils.debug("Creating logs directory")

    target_logs_dir = os.path.join(libcalamares.globalstorage.value("rootMountPoint"), "var/log/zforge")
    os.makedirs(target_logs_dir, exist_ok=True)

    # Copy Calamares logs
    if os.path.exists("/var/log/calamares/"):
        os.system(f"cp -r /var/log/calamares/* {target_logs_dir}/")

    # Create install summary
    summary_path = os.path.join(target_logs_dir, "installation-summary.txt")

    summary_content = f"""Z-Forge Installation Summary
===========================
Date: {subprocess.check_output(['date'], text=True).strip()}
Hostname: {subprocess.check_output(['hostname'], text=True).strip()}

Installation Parameters:
-----------------------
"""

    # Add global storage values to summary
    for key in libcalamares.globalstorage.keys():
        value = libcalamares.globalstorage.value(key)
        if key in ["rootMountPoint", "bogus"]:
            continue

        if isinstance(value, (str, int, float, bool)):
            summary_content += f"{key}: {value}\n"
        elif isinstance(value, (dict, list)):
            try:
                summary_content += f"{key}: {json.dumps(value, indent=2)}\n"
            except:
                summary_content += f"{key}: [complex data]\n"

    with open(summary_path, 'w') as f:
        f.write(summary_content)

    # Link to root's home for easy access
    target_root_log_link = os.path.join(libcalamares.globalstorage.value("rootMountPoint"), "root/installation-logs")
    os.symlink("/var/log/zforge", target_root_log_link)

def capture_system_info():
    """Capture detailed system information"""

    libcalamares.utils.debug("Capturing system information")

    target_sysinfo_dir = os.path.join(libcalamares.globalstorage.value("rootMountPoint"), "var/log/zforge/sysinfo")
    os.makedirs(target_sysinfo_dir, exist_ok=True)

    # Commands to capture system information
    info_commands = {
        "cpu-info.txt": "lscpu",
        "memory-info.txt": "free -h",
        "disk-info.txt": "lsblk -o NAME,SIZE,TYPE,FSTYPE,MOUNTPOINT,UUID",
        "zfs-pools.txt": "zpool list",
        "zfs-datasets.txt": "zfs list",
        "network-info.txt": "ip addr show",
        "pci-devices.txt": "lspci",
    }

    # Capture information
    for filename, command in info_commands.items():
        try:
            output = subprocess.check_output(command.split(), text=True)
            with open(os.path.join(target_sysinfo_dir, filename), 'w') as f:
                f.write(output)
        except Exception as e:
            libcalamares.utils.debug(f"Error capturing {filename}: {str(e)}")

def setup_auto_updates():
    """Configure automatic security updates"""

    libcalamares.utils.debug("Setting up automatic updates")

    # Install unattended-upgrades if not already installed
    check_target_env_call(["apt-get", "update"])
    check_target_env_call(["apt-get", "install", "-y", "unattended-upgrades", "apt-listchanges"])

    # Configure unattended-upgrades
    auto_upgrades_content = """APT::Periodic::Update-Package-Lists "1";
APT::Periodic::Unattended-Upgrade "1";
APT::Periodic::AutocleanInterval "7";
"""

    target_auto_upgrades_path = os.path.join(libcalamares.globalstorage.value("rootMountPoint"),
                                            "etc/apt/apt.conf.d/20auto-upgrades")

    with open(target_auto_upgrades_path, 'w') as f:
        f.write(auto_upgrades_content)

    # Enable unattended-upgrades
    check_target_env_call(["systemctl", "enable", "unattended-upgrades"])

def secure_ssh():
    """Configure SSH security"""

    libcalamares.utils.debug("Securing SSH configuration")

    ssh_config_path = os.path.join(libcalamares.globalstorage.value("rootMountPoint"),
                                  "etc/ssh/sshd_config")

    if os.path.exists(ssh_config_path):
        # Create backup
        shutil.copy2(ssh_config_path, f"{ssh_config_path}.bak")

        # Modify SSH config
        ssh_config = """# Z-Forge secured SSH configuration
Protocol 2
PermitRootLogin prohibit-password
PasswordAuthentication yes
ChallengeResponseAuthentication no
UsePAM yes
X11Forwarding no
PrintMotd no
AcceptEnv LANG LC_*
Subsystem sftp /usr/lib/openssh/sftp-server
"""

        with open(ssh_config_path, 'w') as f:
            f.write(ssh_config)

        # Enable SSH service
        check_target_env_call(["systemctl", "enable", "ssh"])

def create_shortcuts():
    """Create desktop shortcuts for common tasks"""

    libcalamares.utils.debug("Creating shortcuts")

    shortcuts = {
        "proxmox-web.desktop": {
            "name": "Proxmox Web Interface",
            "exec": "xdg-open https://localhost:8006",
            "icon": "proxmox-logo",
            "comment": "Open Proxmox VE web interface"
        },
        "zfs-status.desktop": {
            "name": "ZFS Pool Status",
            "exec": "x-terminal-emulator -e 'zpool status; read -p \"Press Enter to close...\" dummy'",
            "icon": "utilities-terminal",
            "comment": "Check ZFS pool status"
        },
        "recovery-tool.desktop": {
            "name": "Z-Forge Recovery",
            "exec": "x-terminal-emulator -e '/root/zforge-recovery/recovery.sh'",
            "icon": "system-software-install",
            "comment": "Launch Z-Forge recovery tool"
        }
    }

    # Create desktop directory if it doesn't exist
    target_desktop_dir = os.path.join(libcalamares.globalstorage.value("rootMountPoint"), "root/Desktop")
    os.makedirs(target_desktop_dir, exist_ok=True)

    # Create shortcuts
    for filename, shortcut in shortcuts.items():
        shortcut_path = os.path.join(target_desktop_dir, filename)

        shortcut_content = f"""[Desktop Entry]
Type=Application
Name={shortcut['name']}
Exec={shortcut['exec']}
Icon={shortcut['icon']}
Comment={shortcut['comment']}
Terminal=false
Categories=System;
"""

        with open(shortcut_path, 'w') as f:
            f.write(shortcut_content)

        os.chmod(shortcut_path, 0o755)

def cleanup_installation():
    """Final cleanup of installation"""

    libcalamares.utils.debug("Performing final cleanup")

    # Remove temporary files
    temp_paths = [
        "tmp/*",
        "var/tmp/*",
        "var/cache/apt/archives/*.deb"
    ]

    for path in temp_paths:
        full_path = os.path.join(libcalamares.globalstorage.value("rootMountPoint"), path)
        try:
            os.system(f"rm -rf {full_path}")
        except Exception as e:
            libcalamares.utils.debug(f"Error cleaning {path}: {str(e)}")

    # Configure final boot message
    motd_path = os.path.join(libcalamares.globalstorage.value("rootMountPoint"), "etc/motd")

    motd_content = """
=======================================================================
                       Z-FORGE PROXMOX VE
=======================================================================

Your Proxmox VE system is ready to use!

Web interface: https://localhost:8006 (or https://<server-ip>:8006)

Documentation can be found at:
  * /root/POST_INSTALL.md - Post-installation guide
  * /root/installation-logs - Installation logs

For recovery options, run: /root/zforge-recovery/recovery.sh

=======================================================================
"""

    with open(motd_path, 'w') as f:
        f.write(motd_content)
