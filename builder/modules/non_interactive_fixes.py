#!/usr/bin/env python3
"""
Non-Interactive Installation Fixes Module for Z-FORGE
Handles common issues that require user interaction during package installation
"""

import os
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional
import logging

class NonInteractiveFixes:
    """Applies fixes for common non-interactive installation issues"""
    
    def __init__(self, workspace: Path, config: Dict):
        self.workspace = workspace
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.chroot_path = workspace / "chroot"
        
    def execute(self, resume_data: Optional[Dict] = None, lockfile: Optional[Any] = None) -> Dict:
        """Apply all non-interactive fixes"""
        try:
            self.logger.info("Applying non-interactive installation fixes...")
            
            # Apply all fixes
            self._configure_debconf()
            self._configure_apt()
            self._setup_policy_rc()
            self._configure_grub()
            self._configure_postfix()
            self._configure_tzdata()
            self._configure_keyboard()
            self._configure_console_setup()
            self._configure_openssh()
            self._configure_mysql()
            self._configure_gdm_lightdm()
            self._fix_service_starts()
            self._configure_unattended_upgrades()
            
            return {
                'status': 'success',
                'fixes_applied': [
                    'debconf', 'apt', 'policy-rc', 'grub', 'postfix',
                    'tzdata', 'keyboard', 'console', 'ssh', 'mysql',
                    'display-manager', 'services', 'unattended-upgrades'
                ]
            }
            
        except Exception as e:
            self.logger.error(f"Failed to apply non-interactive fixes: {e}")
            return {
                'status': 'error',
                'error': str(e),
                'module': self.__class__.__name__
            }
    
    def _run_chroot_command(self, command, check=True):
        """Run command in chroot"""
        full_cmd = ["chroot", str(self.chroot_path)] + command
        return subprocess.run(full_cmd, check=check, capture_output=True, text=True)
    
    def _configure_debconf(self):
        """Configure debconf for non-interactive mode"""
        self.logger.info("Configuring debconf for non-interactive mode...")
        
        # Set frontend to noninteractive
        debconf_config = """
# Debconf configuration for non-interactive installation
debconf debconf/frontend select Noninteractive
debconf debconf/priority select critical
"""
        
        debconf_file = self.chroot_path / "tmp" / "debconf.conf"
        with open(debconf_file, 'w') as f:
            f.write(debconf_config)
        
        # Apply configuration
        self._run_chroot_command([
            "debconf-set-selections", "/tmp/debconf.conf"
        ], check=False)
        
        # Set environment variable
        os.environ['DEBIAN_FRONTEND'] = 'noninteractive'
        
    def _configure_apt(self):
        """Configure APT for non-interactive use"""
        self.logger.info("Configuring APT for non-interactive mode...")
        
        apt_conf = """
// Non-interactive APT configuration
APT::Get::Assume-Yes "true";
APT::Get::allow-unauthenticated "false";
APT::Get::allow-downgrades "false";
APT::Get::allow-remove-essential "false";
APT::Get::allow-change-held-packages "false";

// Disable interactive prompts
DPkg::Options {
   "--force-confdef";
   "--force-confold";
   "--force-confnew";
}

// Disable progress bars that can hang
Dpkg::Progress-Fancy "false";
"""
        
        apt_conf_file = self.chroot_path / "etc" / "apt" / "apt.conf.d" / "99noninteractive"
        apt_conf_file.parent.mkdir(parents=True, exist_ok=True)
        with open(apt_conf_file, 'w') as f:
            f.write(apt_conf)
    
    def _setup_policy_rc(self):
        """Create policy-rc.d to prevent services from starting during installation"""
        self.logger.info("Setting up policy-rc.d to prevent service starts...")
        
        policy_rc = self.chroot_path / "usr" / "sbin" / "policy-rc.d"
        policy_rc.parent.mkdir(parents=True, exist_ok=True)
        
        with open(policy_rc, 'w') as f:
            f.write("""#!/bin/sh
# Prevent services from starting during installation
exit 101
""")
        
        os.chmod(policy_rc, 0o755)
    
    def _configure_grub(self):
        """Pre-configure GRUB to avoid prompts"""
        self.logger.info("Pre-configuring GRUB...")
        
        grub_config = """
grub-pc grub-pc/install_devices string /dev/sda
grub-pc grub-pc/install_devices_empty boolean false
grub-pc grub-pc/install_devices_failed boolean false
grub-pc grub-pc/chainload_from_menu.lst boolean true
grub-pc grub-pc/kopt_extracted boolean false
grub-pc grub-pc/postrm_purge_boot_grub boolean false
grub-pc grub2/force_efi_extra_removable boolean false
grub-pc grub2/linux_cmdline string quiet splash
grub-pc grub2/linux_cmdline_default string quiet splash
"""
        
        grub_file = self.chroot_path / "tmp" / "grub.conf"
        with open(grub_file, 'w') as f:
            f.write(grub_config)
        
        self._run_chroot_command([
            "debconf-set-selections", "/tmp/grub.conf"
        ], check=False)
    
    def _configure_postfix(self):
        """Pre-configure postfix to avoid prompts"""
        self.logger.info("Pre-configuring postfix...")
        
        postfix_config = """
postfix postfix/main_mailer_type select No configuration
postfix postfix/mailname string localhost
postfix postfix/destinations string localhost
"""
        
        postfix_file = self.chroot_path / "tmp" / "postfix.conf"
        with open(postfix_file, 'w') as f:
            f.write(postfix_config)
        
        self._run_chroot_command([
            "debconf-set-selections", "/tmp/postfix.conf"
        ], check=False)
    
    def _configure_tzdata(self):
        """Pre-configure timezone data"""
        self.logger.info("Pre-configuring timezone...")
        
        # Set timezone to UTC by default
        tzdata_config = """
tzdata tzdata/Areas select Etc
tzdata tzdata/Zones/Etc select UTC
"""
        
        tz_file = self.chroot_path / "tmp" / "tzdata.conf"
        with open(tz_file, 'w') as f:
            f.write(tzdata_config)
        
        self._run_chroot_command([
            "debconf-set-selections", "/tmp/tzdata.conf"
        ], check=False)
        
        # Also create the timezone file
        tz_link = self.chroot_path / "etc" / "localtime"
        if tz_link.exists():
            tz_link.unlink()
        
        # Create symlink
        self._run_chroot_command([
            "ln", "-sf", "/usr/share/zoneinfo/UTC", "/etc/localtime"
        ], check=False)
    
    def _configure_keyboard(self):
        """Pre-configure keyboard layout"""
        self.logger.info("Pre-configuring keyboard...")
        
        keyboard_config = """
keyboard-configuration keyboard-configuration/model select Generic 105-key PC (intl.)
keyboard-configuration keyboard-configuration/layout select English (US)
keyboard-configuration keyboard-configuration/variant select English (US)
keyboard-configuration keyboard-configuration/modelcode string pc105
keyboard-configuration keyboard-configuration/layoutcode string us
keyboard-configuration keyboard-configuration/variantcode string
keyboard-configuration keyboard-configuration/optionscode string
"""
        
        kb_file = self.chroot_path / "tmp" / "keyboard.conf"
        with open(kb_file, 'w') as f:
            f.write(keyboard_config)
        
        self._run_chroot_command([
            "debconf-set-selections", "/tmp/keyboard.conf"
        ], check=False)
    
    def _configure_console_setup(self):
        """Pre-configure console setup"""
        self.logger.info("Pre-configuring console...")
        
        console_config = """
console-setup console-setup/charmap47 select UTF-8
console-setup console-setup/codeset47 select Guess optimal character set
console-setup console-setup/fontface47 select TerminusBold
console-setup console-setup/fontsize-fb47 select 16
"""
        
        console_file = self.chroot_path / "tmp" / "console.conf"
        with open(console_file, 'w') as f:
            f.write(console_config)
        
        self._run_chroot_command([
            "debconf-set-selections", "/tmp/console.conf"
        ], check=False)
    
    def _configure_openssh(self):
        """Pre-configure OpenSSH server"""
        self.logger.info("Pre-configuring OpenSSH...")
        
        ssh_config = """
openssh-server openssh-server/permit-root-login boolean false
openssh-server openssh-server/password-authentication boolean true
"""
        
        ssh_file = self.chroot_path / "tmp" / "ssh.conf"
        with open(ssh_file, 'w') as f:
            f.write(ssh_config)
        
        self._run_chroot_command([
            "debconf-set-selections", "/tmp/ssh.conf"
        ], check=False)
    
    def _configure_mysql(self):
        """Pre-configure MySQL/MariaDB"""
        self.logger.info("Pre-configuring MySQL/MariaDB...")
        
        mysql_config = """
mysql-server mysql-server/root_password password
mysql-server mysql-server/root_password_again password
mariadb-server mysql-server/root_password password
mariadb-server mysql-server/root_password_again password
"""
        
        mysql_file = self.chroot_path / "tmp" / "mysql.conf"
        with open(mysql_file, 'w') as f:
            f.write(mysql_config)
        
        self._run_chroot_command([
            "debconf-set-selections", "/tmp/mysql.conf"
        ], check=False)
    
    def _configure_gdm_lightdm(self):
        """Pre-configure display managers"""
        self.logger.info("Pre-configuring display managers...")
        
        dm_config = """
gdm3 gdm3/daemon_name string /usr/sbin/gdm3
lightdm lightdm/daemon_name string /usr/sbin/lightdm
sddm sddm/daemon_name string /usr/sbin/sddm
"""
        
        dm_file = self.chroot_path / "tmp" / "dm.conf"
        with open(dm_file, 'w') as f:
            f.write(dm_config)
        
        self._run_chroot_command([
            "debconf-set-selections", "/tmp/dm.conf"
        ], check=False)
        
        # Set default display manager
        default_dm = self.chroot_path / "etc" / "X11" / "default-display-manager"
        default_dm.parent.mkdir(parents=True, exist_ok=True)
        with open(default_dm, 'w') as f:
            f.write("/usr/sbin/sddm\n")
    
    def _fix_service_starts(self):
        """Fix common service start issues"""
        self.logger.info("Fixing service start issues...")
        
        # Disable automatic service starts
        systemctl_override = self.chroot_path / "usr" / "bin" / "systemctl"
        if not systemctl_override.exists():
            # Create a dummy systemctl during build
            with open(systemctl_override, 'w') as f:
                f.write("""#!/bin/sh
# Dummy systemctl during build
exit 0
""")
            os.chmod(systemctl_override, 0o755)
    
    def _configure_unattended_upgrades(self):
        """Configure unattended upgrades to not prompt"""
        self.logger.info("Configuring unattended-upgrades...")
        
        unattended_config = """
unattended-upgrades unattended-upgrades/enable_auto_updates boolean false
"""
        
        unattended_file = self.chroot_path / "tmp" / "unattended.conf"
        with open(unattended_file, 'w') as f:
            f.write(unattended_config)
        
        self._run_chroot_command([
            "debconf-set-selections", "/tmp/unattended.conf"
        ], check=False)