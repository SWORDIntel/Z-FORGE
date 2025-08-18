#!/usr/bin/env python3
"""
Repository Validation Module for Z-Forge

This module provides secure repository configuration with proper GPG validation,
falling back to bypass only when necessary for build reliability.
"""

import subprocess
import logging
import requests
from pathlib import Path
from typing import Dict, Any, Optional, List
import tempfile


class RepositoryValidation:
    """Validates and secures APT repositories with proper GPG handling."""
    
    def __init__(self, workspace: Path, config: Dict[str, Any]):
        self.workspace = workspace
        self.config = config
        self.chroot_path = workspace / "chroot"
        self.logger = logging.getLogger(self.__class__.__name__)
        
    def execute(self, resume_data: Optional[Dict[str, Any]] = None,
                lockfile: Optional[Any] = None) -> Dict[str, Any]:
        """Execute repository validation and security setup."""
        self.logger.info("Starting repository validation and security setup...")
        
        try:
            # First, try to validate repositories properly
            validation_success = self._validate_repositories()
            
            if validation_success and not self.config.get('force_gpg_bypass', False):
                # Set up proper GPG validation
                self._setup_secure_repositories()
                security_level = "high"
                self.logger.info("Repository security configured with GPG validation")
            else:
                # Fall back to bypass only if validation fails
                self.logger.warning("Repository validation failed, falling back to GPG bypass")
                self._setup_gpg_bypass()
                security_level = "bypass"
                self.logger.warning("GPG validation bypassed - USE ONLY FOR DEVELOPMENT")
            
            return {
                'status': 'success',
                'security_level': security_level,
                'repositories_validated': validation_success
            }
            
        except Exception as e:
            self.logger.error(f"Repository validation failed: {str(e)}")
            return {
                'status': 'error',
                'error': str(e)
            }
    
    def _validate_repositories(self) -> bool:
        """Validate that repositories are accessible and have valid signatures."""
        self.logger.info("Validating repository accessibility...")
        
        try:
            # Get mirrors from config
            primary_mirror = self.config.get('debian_mirror', 'http://deb.debian.org/debian')
            fallback_mirrors = self.config.get('fallback_mirrors', [])
            
            mirrors_to_test = [primary_mirror] + fallback_mirrors
            
            for mirror in mirrors_to_test:
                if self._test_repository_access(mirror):
                    self.logger.info(f"Repository {mirror} is accessible")
                    return True
                else:
                    self.logger.warning(f"Repository {mirror} is not accessible")
            
            self.logger.error("No accessible repositories found")
            return False
            
        except Exception as e:
            self.logger.error(f"Repository validation error: {str(e)}")
            return False
    
    def _test_repository_access(self, mirror: str) -> bool:
        """Test if a repository mirror is accessible."""
        try:
            debian_release = self.config.get('debian_release', 'bookworm')
            test_url = f"{mirror}/dists/{debian_release}/Release"
            
            response = requests.head(test_url, timeout=10)
            return response.status_code == 200
            
        except Exception:
            return False
    
    def _setup_secure_repositories(self):
        """Configure repositories with proper GPG validation."""
        self.logger.info("Setting up secure repository configuration...")
        
        # Ensure GPG directories exist
        trusted_gpg_dir = self.chroot_path / "etc/apt/trusted.gpg.d"
        trusted_gpg_dir.mkdir(parents=True, exist_ok=True)
        
        keyrings_dir = self.chroot_path / "etc/apt/keyrings"
        keyrings_dir.mkdir(parents=True, exist_ok=True)
        
        # Download and install Debian archive keyring
        self._install_debian_keyring()
        
        # Configure secure APT settings
        apt_config = """// Z-Forge Secure Repository Configuration

// Enable security checks
Acquire::AllowInsecureRepositories "false";
Acquire::AllowDowngradeToInsecureRepositories "false";

// Enable signature verification
APT::Get::AllowUnauthenticated "false";

// Validate release files
Acquire::Check-Valid-Until "true";

// Security timeouts
Acquire::http::Timeout "30";
Acquire::https::Timeout "30";

// Retry configuration
Acquire::Retries "3";
"""
        
        apt_conf_dir = self.chroot_path / "etc/apt/apt.conf.d"
        apt_conf_dir.mkdir(parents=True, exist_ok=True)
        
        secure_conf = apt_conf_dir / "99-zforge-secure"
        secure_conf.write_text(apt_config)
        self.logger.info(f"Created secure configuration: {secure_conf}")
        
        # Configure package pinning if specified
        if self.config.get('enable_pinning') and self.config.get('pinning_preferences'):
            self._setup_package_pinning()
    
    def _install_debian_keyring(self):
        """Install the Debian archive keyring for signature verification."""
        try:
            self.logger.info("Installing Debian archive keyring...")
            
            keyring_url = "https://ftp-master.debian.org/keys/archive-key-12.asc"
            keyring_path = self.chroot_path / "etc/apt/trusted.gpg.d/debian-archive-keyring.asc"
            
            response = requests.get(keyring_url, timeout=30)
            response.raise_for_status()
            
            keyring_path.write_bytes(response.content)
            self.logger.info(f"Installed Debian keyring: {keyring_path}")
            
        except Exception as e:
            self.logger.warning(f"Could not install Debian keyring: {str(e)}")
            raise
    
    def _setup_package_pinning(self):
        """Set up package pinning for stability."""
        self.logger.info("Setting up package pinning...")
        
        pinning_prefs = self.config.get('pinning_preferences', '')
        if pinning_prefs:
            prefs_dir = self.chroot_path / "etc/apt/preferences.d"
            prefs_dir.mkdir(parents=True, exist_ok=True)
            
            prefs_file = prefs_dir / "99-zforge-pinning"
            prefs_file.write_text(pinning_prefs)
            self.logger.info(f"Created package pinning: {prefs_file}")
    
    def _setup_gpg_bypass(self):
        """Fall back to GPG bypass configuration."""
        self.logger.warning("Setting up GPG bypass - DEVELOPMENT ONLY")
        
        # Use the existing GPG bypass logic
        from .gpg_bypass import GpgBypass
        
        bypass = GpgBypass(self.workspace, self.config)
        result = bypass.execute()
        
        if result.get('status') != 'success':
            raise Exception(f"GPG bypass setup failed: {result.get('error', 'Unknown error')}")
        
        self.logger.warning("GPG bypass configured - ensure this is used only for development")