#!/usr/bin/env python3
# z-forge/builder/z_forge.py - Main entry point
"""
Z-Forge V3 Builder
Project: Z-FORGE
Classification: TECHNICAL IMPLEMENTATION
Purpose: Bootstrap minimal Proxmox VE with latest kernel on ZFS with Full Disk Encryption support
"""
import sys
import os
import yaml
import logging
import argparse
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional

# Add builder modules to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from core.builder import ZForgeBuilder
from core.config import BuildConfig
from core.lockfile import BuildLockfile
from utils.terminal_ui import TerminalUI
from utils.encryption import EncryptionManager

class ZForgeEncryptionOptions:
    """Class to handle ZFS encryption options"""
    
    def __init__(self):
        self.algorithms = [
            "aes-256-gcm",    # Best performance on modern CPUs with AES-NI
            "aes-256-ccm",    # Alternative AES mode
            "chacha20-poly1305"  # Better for CPUs without AES-NI
        ]
        self.default_algorithm = "aes-256-gcm"
        self.default_pbkdf_iterations = 350000  # Higher iteration count for better security
    
    def get_algorithm_info(self):
        """Return information about encryption algorithms"""
        return {
            "aes-256-gcm": {
                "description": "AES-GCM 256-bit (Recommended for CPUs with AES-NI)",
                "performance": "Excellent on modern hardware",
                "security": "Very High"
            },
            "aes-256-ccm": {
                "description": "AES-CCM 256-bit",
                "performance": "Good on modern hardware",
                "security": "Very High"
            },
            "chacha20-poly1305": {
                "description": "ChaCha20-Poly1305 (Recommended for CPUs without AES-NI)",
                "performance": "Better on older hardware",
                "security": "Very High"
            }
        }

def main():
    """Main entry point for Z-Forge builder"""
    # Set up terminal UI instead of argparse for options
    ui = TerminalUI()
    
    # Display welcome banner
    ui.display_banner("""
    ╔══════════════════════════════════════════╗
    ║          Z-FORGE V3 BUILDER              ║
    ║    Proxmox VE Bootstrap System           ║
    ║         [ARCHITECT APPROVED]             ║
    ╚══════════════════════════════════════════╝
    """)
    
    # Get build options through TUI
    build_options = ui.get_build_options()
    
    if build_options['action'] == 'new_build':
        execute_new_build(build_options)
    elif build_options['action'] == 'resume_build':
        execute_resume_build(build_options)
    elif build_options['action'] == 'verify_iso':
        verify_existing_iso(build_options)

def execute_new_build(options: Dict):
    """Execute a fresh build from scratch"""
    # Load or create configuration
    config_path = options.get('config_file', 'build_spec.yml')
    if not Path(config_path).exists():
        create_default_config(config_path)
    
    # Ask about encryption if not specified in options
    if 'encryption' not in options:
        ui = TerminalUI()
        encryption_options = ZForgeEncryptionOptions()
        encryption_config = ui.configure_encryption(encryption_options)
        options['encryption'] = encryption_config
    
    # Initialize builder
    builder = ZForgeBuilder(config_path)
    
    # Update build config with encryption settings
    if options.get('encryption', {}).get('enabled', False):
        builder.update_encryption_settings(options['encryption'])
    
    # Create build lockfile
    lockfile = BuildLockfile(Path("build_spec.lock"))
    
    # Execute build pipeline
    result = builder.execute_pipeline(lockfile=lockfile)
    
    if result['status'] == 'success':
        print(f"\n[+] Build completed successfully!")
        print(f"[+] ISO location: {result['iso_path']}")
        print(f"[+] Build log: {result['log_path']}")
        print(f"[+] Lockfile: {result['lockfile_path']}")
        
        # Print encryption notice if enabled
        if options.get('encryption', {}).get('enabled', False):
            print("\n[+] Full Disk Encryption is enabled in this build")
            print("[+] The installer will prompt for encryption settings during installation")
    else:
        print(f"\n[!] Build failed: {result['error']}")
        print(f"[!] Check log for details: {result['log_path']}")
        sys.exit(1)

def execute_resume_build(options: Dict):
    """Resume a previous build from lockfile"""
    lockfile_path = options.get('lockfile', 'build_spec.lock')
    if not Path(lockfile_path).exists():
        print(f"[!] Lockfile not found: {lockfile_path}")
        sys.exit(1)
        
    # Load lockfile
    lockfile = BuildLockfile(Path(lockfile_path))
    
    # Initialize builder from lockfile
    builder = ZForgeBuilder.from_lockfile(lockfile)
    
    # Resume build pipeline
    result = builder.execute_pipeline(lockfile=lockfile, resume=True)
    
    if result['status'] == 'success':
        print(f"\n[+] Build resumed and completed successfully!")
        print(f"[+] ISO location: {result['iso_path']}")
        print(f"[+] Build log: {result['log_path']}")
        print(f"[+] Lockfile: {result['lockfile_path']}")
    else:
        print(f"\n[!] Build failed: {result['error']}")
        print(f"[!] Check log for details: {result['log_path']}")
        sys.exit(1)

def verify_existing_iso(options: Dict):
    """Verify an existing ISO file"""
    iso_path = options.get('iso_path')
    if not iso_path or not Path(iso_path).exists():
        print(f"[!] ISO file not found: {iso_path}")
        sys.exit(1)
        
    # Initialize builder for verification only
    builder = ZForgeBuilder(None, verification_mode=True)
    
    # Verify ISO
    result = builder.verify_iso(iso_path)
    
    if result['status'] == 'success':
        print(f"\n[+] ISO verification successful!")
        print(f"[+] ISO: {iso_path}")
        print(f"[+] Verification report: {result['report_path']}")
        
        # Display encryption status if available
        if result.get('encryption_enabled') is not None:
            status = "ENABLED" if result['encryption_enabled'] else "DISABLED"
            print(f"[+] Full Disk Encryption: {status}")
    else:
        print(f"\n[!] ISO verification failed: {result['error']}")
        sys.exit(1)

def create_default_config(path: str):
    """Create default build_spec.yml configuration"""
    default_config = {
        'builder_config': {
            'debian_release': 'bookworm',
            'kernel_version': 'latest',  # Will fetch latest stable
            'output_iso_name': 'zforge-proxmox-v3.iso',
            'enable_debug': True,
            'workspace_path': '/tmp/zforge_workspace',
            'cache_packages': True
        },
        'proxmox_config': {
            'version': 'latest',  # Will use latest PVE 8.x
            'minimal_install': True,
            'include_packages': [
                'proxmox-ve',
                'proxmox-kernel-6.8',  # Latest kernel series
                'zfs-dkms',
                'zfsutils-linux',
                'pve-zsync'
            ]
        },
        'zfs_config': {
            'version': 'latest',  # Latest OpenZFS
            'build_from_source': True,
            'enable_encryption': True,  # Enable ZFS native encryption
            'default_compression': 'lz4',
            'encryption': {
                'default_enabled': True,
                'default_algorithm': 'aes-256-gcm',
                'pbkdf_iterations': 350000,
                'prompt_during_install': True
            }
        },
        'bootloader_config': {
            'primary': 'zfsbootmenu',
            'enable_opencore': True,
            'opencore_drivers': ['NvmExpressDxe.efi', 'OpenRuntime.efi'],
            'encryption_support': True  # Enable bootloader encryption support
        },
        'modules': [
            {'name': 'WorkspaceSetup', 'enabled': True},
            {'name': 'Debootstrap', 'enabled': True},
            {'name': 'KernelAcquisition', 'enabled': True},
            {'name': 'ZFSBuild', 'enabled': True},
            {'name': 'ProxmoxIntegration', 'enabled': True},
            {'name': 'BootloaderSetup', 'enabled': True},
            {'name': 'CalamaresIntegration', 'enabled': True},
            {'name': 'SecurityHardening', 'enabled': True},
            {'name': 'EncryptionSupport', 'enabled': True},  # New module for encryption
            {'name': 'ISOGeneration', 'enabled': True}
        ],
        'calamares_config': {
            'modules': [
                'welcome',
                'locale',
                'keyboard',
                'partition',
                'zfsrootselect',  # Our custom ZFS module with encryption
                'users',
                'summary',
                'install',
                'finished'
            ]
        }
    }
    
    with open(path, 'w') as f:
        yaml.dump(default_config, f, default_flow_style=False, sort_keys=False)
    
    print(f"[+] Created default configuration: {path}")

if __name__ == "__main__":
    main()
