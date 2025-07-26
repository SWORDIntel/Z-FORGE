#!/usr/bin/env python3
"""
GPG Bypass Module for Z-Forge
Disables GPG verification for all repositories during build
"""

import subprocess
import logging
from pathlib import Path
from typing import Dict, Any, Optional


class GPGBypass:
    """Bypass GPG verification for build process"""
    
    def __init__(self, workspace: Path, config: Dict[str, Any]):
        self.workspace = workspace
        self.config = config
        self.chroot_path = workspace / "chroot"
        self.logger = logging.getLogger(self.__class__.__name__)
        
    def execute(self, resume_data: Optional[Dict[str, Any]] = None,
                lockfile: Optional[Any] = None) -> Dict[str, Any]:
        """Disable GPG verification"""
        self.logger.info("Configuring APT to bypass GPG verification...")
        
        try:
            # Create APT config to disable GPG checks
            self._create_apt_config()
            
            # Configure apt to trust all repositories
            self._configure_trusted_repos()
            
            # Disable apt-key warnings
            self._disable_apt_key_warnings()
            
            return {
                'status': 'success',
                'message': 'GPG verification bypassed successfully'
            }
            
        except Exception as e:
            self.logger.error(f"GPG bypass failed: {str(e)}")
            return {
                'status': 'error',
                'error': str(e)
            }
    
    def _create_apt_config(self):
        """Create APT configuration to disable GPG checks"""
        self.logger.info("Creating APT configuration for GPG bypass...")
        
        # Main APT config for GPG bypass
        apt_config = """// Z-Forge GPG Bypass Configuration
// WARNING: This disables security checks - use only for building!

// Disable GPG signature verification
APT::Get::AllowUnauthenticated "true";
Acquire::AllowInsecureRepositories "true";
Acquire::AllowDowngradeToInsecureRepositories "true";

// Disable validity checks
Acquire::Check-Valid-Until "false";

// Trust all sources
APT::Trusted "true";

// Disable apt-key warnings
APT::Key::Assert-Pubkey-Algo "false";

// Allow weak repositories
Acquire::AllowWeakRepositories "true";

// Disable release file verification
APT::Get::Assume-Yes "true";
Debug::Acquire::gpgv "true";
"""
        
        apt_conf_dir = self.chroot_path / "etc/apt/apt.conf.d"
        apt_conf_dir.mkdir(parents=True, exist_ok=True)
        
        gpg_bypass_conf = apt_conf_dir / "99-zforge-gpg-bypass"
        gpg_bypass_conf.write_text(apt_config)
        self.logger.info(f"Created {gpg_bypass_conf}")
        
        # Also create a preferences file
        apt_prefs = """Package: *
Pin: release *
Pin-Priority: 1001

Explanation: Trust all packages regardless of signature
"""
        
        apt_prefs_path = self.chroot_path / "etc/apt/preferences.d/99-trust-all"
        apt_prefs_path.parent.mkdir(parents=True, exist_ok=True)
        apt_prefs_path.write_text(apt_prefs)
        self.logger.info(f"Created {apt_prefs_path}")
    
    def _configure_trusted_repos(self):
        """Configure all repositories as trusted"""
        self.logger.info("Configuring repositories as trusted...")
        
        # Update sources.list to add trusted=yes
        sources_list = self.chroot_path / "etc/apt/sources.list"
        if sources_list.exists():
            content = sources_list.read_text()
            
            # Add trusted=yes to all deb lines that don't have it
            lines = []
            for line in content.splitlines():
                if line.strip().startswith('deb ') and '[' not in line:
                    # Add trusted=yes
                    parts = line.split(None, 1)
                    if len(parts) == 2:
                        line = f"{parts[0]} [trusted=yes] {parts[1]}"
                elif line.strip().startswith('deb ') and 'trusted=yes' not in line:
                    # Add trusted=yes to existing options
                    line = line.replace('[', '[trusted=yes ')
                lines.append(line)
            
            sources_list.write_text('\n'.join(lines))
            self.logger.info("Updated sources.list with trusted=yes")
        
        # Update all files in sources.list.d
        sources_list_d = self.chroot_path / "etc/apt/sources.list.d"
        if sources_list_d.exists():
            for source_file in sources_list_d.glob("*.list"):
                content = source_file.read_text()
                lines = []
                
                for line in content.splitlines():
                    if line.strip().startswith('deb ') and '[' not in line:
                        parts = line.split(None, 1)
                        if len(parts) == 2:
                            line = f"{parts[0]} [trusted=yes] {parts[1]}"
                    elif line.strip().startswith('deb ') and 'trusted=yes' not in line:
                        line = line.replace('[', '[trusted=yes ')
                    lines.append(line)
                
                source_file.write_text('\n'.join(lines))
                self.logger.info(f"Updated {source_file.name} with trusted=yes")
    
    def _disable_apt_key_warnings(self):
        """Disable apt-key deprecation warnings"""
        self.logger.info("Disabling apt-key warnings...")
        
        # Create wrapper script for apt-key
        apt_key_wrapper = self.chroot_path / "usr/local/bin/apt-key"
        apt_key_wrapper.parent.mkdir(parents=True, exist_ok=True)
        
        wrapper_content = """#!/bin/bash
# Z-Forge apt-key wrapper - suppresses warnings
export APT_KEY_DONT_WARN_ON_DANGEROUS_USAGE=1
/usr/bin/apt-key "$@" 2>&1 | grep -v "Warning: apt-key" || true
"""
        
        apt_key_wrapper.write_text(wrapper_content)
        apt_key_wrapper.chmod(0o755)
        
        # Create environment file
        env_file = self.chroot_path / "etc/environment.d/99-apt-key.conf"
        env_file.parent.mkdir(parents=True, exist_ok=True)
        env_file.write_text("APT_KEY_DONT_WARN_ON_DANGEROUS_USAGE=1\n")
        
        self.logger.info("APT key warnings disabled")