#!/usr/bin/env python3
# z-forge/builder/z_forge.py - Main entry point

"""
Z-Forge V3 Builder
Project: Z-FORGE
Classification: TECHNICAL IMPLEMENTATION
Purpose: Bootstrap minimal Proxmox VE with latest kernel on ZFS
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
        
    # Initialize builder
    builder = ZForgeBuilder(config_path)
    
    # Create build lockfile
    lockfile = BuildLockfile(Path("build_spec.lock"))
    
    # Execute build pipeline
    result = builder.execute_pipeline(lockfile=lockfile)
    
    if result['status'] == 'success':
        print(f"\n[+] Build completed successfully!")
        print(f"[+] ISO location: {result['iso_path']}")
        print(f"[+] Build log: {result['log_path']}")
        print(f"[+] Lockfile: {result['lockfile_path']}")
    else:
        print(f"\n[!] Build failed: {result['error']}")
        print(f"[!] Check log for details: {result['log_path']}")
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
            'enable_encryption': True,
            'default_compression': 'lz4'
        },
        'bootloader_config': {
            'primary': 'zfsbootmenu',
            'enable_opencore': True,
            'opencore_drivers': ['NvmExpressDxe.efi', 'OpenRuntime.efi']
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
            {'name': 'ISOGeneration', 'enabled': True}
        ]
    }
    
    with open(path, 'w') as f:
        yaml.dump(default_config, f, default_flow_style=False, sort_keys=False)
        
    print(f"[+] Created default configuration: {path}")

if __name__ == "__main__":
    main()
