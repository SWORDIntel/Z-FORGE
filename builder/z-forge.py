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
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
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
    # Parse command line arguments first
    parser = argparse.ArgumentParser(
        description='Z-FORGE V3 Builder - Universal Proxmox VE Bootstrap System',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Build with default universal configuration
  %(prog)s
  
  # Build with specific build spec
  %(prog)s --build-spec build_spec.yml
  
  # Resume interrupted build
  %(prog)s --resume
  
  # Build for specific hardware
  %(prog)s --build-spec config/t30/t30_build_spec.yml
        """
    )
    
    parser.add_argument('--build-spec', type=str, default='build_spec.yml',
                       help='Path to build specification YAML file (default: build_spec.yml)')
    parser.add_argument('--resume', action='store_true',
                       help='Resume a previously interrupted build')
    parser.add_argument('--lockfile', type=str, default='build_spec.lock',
                       help='Path to lockfile for resuming builds (default: build_spec.lock)')
    parser.add_argument('--interactive', action='store_true',
                       help='Use interactive terminal UI mode (not recommended)')
    parser.add_argument('--verify-iso', type=str,
                       help='Verify an existing ISO file')
    parser.add_argument('--debug', action='store_true',
                       help='Enable debug logging')
    parser.add_argument('--auto-detect', action='store_true', default=True,
                       help='Enable automatic hardware detection (default: enabled)')
    
    args = parser.parse_args()
    
    # Configure logging
    log_level = logging.DEBUG if args.debug else logging.INFO
    logging.basicConfig(level=log_level, format='%(asctime)s - %(levelname)s - %(message)s')
    
    # If interactive mode requested, use TUI
    if args.interactive and not args.resume and not args.verify_iso:
        ui = TerminalUI()
        
        # Display welcome banner
        ui.display_banner("""
        ╔══════════════════════════════════════════╗
        ║          Z-FORGE V3 BUILDER              ║
        ║    Universal Proxmox VE Bootstrap        ║
        ║      With Rich ZFS Configuration         ║
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
    else:
        # Command line mode
        if args.verify_iso:
            verify_existing_iso({'iso_path': args.verify_iso, 'build_spec': args.build_spec})
        elif args.resume:
            execute_resume_build({'lockfile': args.lockfile, 'build_spec': args.build_spec})
        else:
            # New build with build spec
            execute_new_build({
                'config_file': args.build_spec,
                'auto_detect': args.auto_detect,
                'debug': args.debug
            })

def execute_new_build(options: Dict):
    """Execute a fresh build from scratch"""
    # Load or create configuration
    config_path = options.get('config_file', 'build_spec.yml')
    if not Path(config_path).exists():
        print(f"[!] Build spec not found: {config_path}")
        print(f"[+] Creating default configuration...")
        create_default_config(config_path)
    
    print("\n" + "="*60)
    print("Z-FORGE V3 Universal Builder")
    print("="*60)
    print(f"[+] Build Spec: {config_path}")
    print(f"[+] Auto-detect: {'Enabled' if options.get('auto_detect', True) else 'Disabled'}")
    
    # Load and display key features from config
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    
    print("\n[+] Build Features:")
    print(f"    - Debian Release: {config['builder_config'].get('debian_release', 'trixie')}")
    print(f"    - ZFS Version: {config['zfs_config'].get('version', '2.3.3')}")
    print(f"    - Hardware Profiles: 19 (Dell, HP, Supermicro, etc.)")
    print(f"    - RAID Controllers: ZFS IT/HBA mode enforced")
    print(f"    - Rich ZFS Config: Boot pools, data pools, datasets")
    print(f"    - Compression: Hardware-aware auto-tuning")
    print(f"    - Optimization: Safe -O2 for all hardware")
    
    # Ask about encryption if interactive and not specified
    if options.get('interactive') and 'encryption' not in options:
        ui = TerminalUI()
        encryption_options = ZForgeEncryptionOptions()
        encryption_config = ui.configure_encryption(encryption_options)
        options['encryption'] = encryption_config
    
    print("\n[+] Starting build process...")
    
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
        
        # Print feature summary
        print("\n[+] ISO Features:")
        print("    - Universal hardware detection")
        print("    - ZFS 2.3.3 with native encryption")
        print("    - Rich GUI configuration in Calamares")
        print("    - Hardware-optimized compression")
        print("    - OpenCore for legacy NVMe boot")
        
        # Print encryption notice if enabled
        if config['zfs_config'].get('enable_encryption', True):
            print("\n[+] Full Disk Encryption is available")
            print("[+] The installer will offer encryption during setup")
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
    
    # Initialize builder with the same config file
    config_file = options.get('build_spec', 'build_spec.yml')
    builder = ZForgeBuilder(config_file)
    
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
        
    # Initialize builder with default config
    config_file = options.get('build_spec', 'build_spec.yml')
    builder = ZForgeBuilder(config_file)
    
    # Verify ISO (if method exists)
    if hasattr(builder, 'verify_iso'):
        result = builder.verify_iso(iso_path)
    else:
        print(f"[!] ISO verification not implemented yet")
        sys.exit(1)
    
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
    """Create default build_spec.yml configuration with all current features"""
    default_config = {
        'builder_config': {
            'debian_release': 'trixie',  # Testing for better hardware support
            'kernel_version': 'latest',  
            'output_iso_name': 'zforge-universal-proxmox-v3.iso',
            'enable_debug': True,
            'workspace_path': '/tmp/zforge_workspace',
            'cache_packages': True,
            'auto_detect_hardware': True,  # Universal build by default
            'safe_optimization': '-O2'  # Safe optimization for all hardware
        },
        'proxmox_config': {
            'version': 'latest',
            'minimal_install': True,
            'build_from_source': False,
            'include_packages': [
                'proxmox-ve',
                'pve-kernel-6.8',
                'zfs-dkms',
                'zfsutils-linux',
                'pve-zsync',
                # Hardware support packages
                'ipmitool', 'openipmi', 'lm-sensors',
                'nvme-cli', 'smartmontools', 'ethtool',
                'fio', 'mdadm', 'snmp',
                # CPU microcode
                'intel-microcode', 'amd64-microcode',
                'thermald', 'powertop', 'i7z',
                # RAID tools
                'megacli', 'megactl', 'megaraid-status',
                'storcli', 'sas2ircu', 'perccli', 'ssacli', 'arcconf'
            ]
        },
        'zfs_config': {
            'version': '2.3.3',  # Specific version
            'repository': 'https://github.com/openzfs/zfs.git',
            'build_from_source': True,
            'build_flags': ['-O2'],  # Safe optimization
            'enable_encryption': True,
            'compression': {
                'default': 'lz4',
                'algorithm': 'auto'  # Hardware-aware selection
            },
            'encryption': {
                'default_enabled': True,
                'default_algorithm': 'aes-256-gcm',
                'pbkdf_iterations': 350000,
                'prompt_during_install': True
            }
        },
        'bootloader_config': {
            'primary': 'zfsbootmenu',
            'enable_isolinux': True,  # For legacy BIOS
            'enable_opencore': True,
            'opencore_flexible': True,  # vFlash, USB, secondary drives
            'opencore_drivers': ['NvmExpressDxe.efi', 'OpenRuntime.efi'],
            'encryption_support': True
        },
        'hardware_detection': {
            'enabled': True,
            'database_path': 'builder/modules/hardware_db.py',
            'profiles': [
                'dell_servers', 'hp_servers', 'supermicro_servers',
                'workstations', 'storage_systems', 'raid_controllers'
            ],
            'enforce_zfs_mode': True  # Force IT/HBA mode for RAID controllers
        },
        'modules': [
            # Phase 0: Detection and Setup
            {'name': 'WorkspaceSetup', 'enabled': True},
            {'name': 'GPGBypass', 'enabled': True},
            {'name': 'UniversalHardwareDetect', 'enabled': True},
            
            # Phase 1: Core Setup
            {'name': 'Debootstrap', 'enabled': True},
            
            # Phase 2: Core System
            {'name': 'KernelAcquisition', 'enabled': True},
            {'name': 'ZFSBuild', 'enabled': True},
            {'name': 'LiveEnvironment', 'enabled': True},
            
            # Phase 3: Boot Infrastructure
            {'name': 'DracutConfig', 'enabled': True},
            {'name': 'ZFSBootMenuInstall', 'enabled': True},
            {'name': 'BootloaderSetup', 'enabled': True},
            
            # Phase 4: System Integration
            {'name': 'ProxmoxIntegration', 'enabled': True},
            {'name': 'SecurityHardening', 'enabled': True},
            {'name': 'ZFSEncryption', 'enabled': True},
            {'name': 'OpenCoreNVME', 'enabled': True},
            
            # Phase 5: Installer Configuration
            {'name': 'CalamaresIntegration', 'enabled': True},
            {'name': 'ZFSCompressionOptimizer', 'enabled': True},
            {'name': 'HardwareProfilerIntegration', 'enabled': True},
            {'name': 'AutoOptimizer', 'enabled': True},
            
            # Phase 6: Finalization
            {'name': 'CleanupHandler', 'enabled': True},
            {'name': 'ISOGeneration', 'enabled': True}
        ],
        'calamares_config': {
            'sequence': [
                {
                    'show': [
                        'welcome',
                        'hardwaredetect',     # Hardware profile display
                        'telemetryconsent',
                        'locale',
                        'keyboard',
                        'raidcontroller',     # RAID controller configuration
                        'zfsrichconfig'       # Rich ZFS configuration
                    ]
                },
                {
                    'exec': [
                        'partition',
                        'mount',
                        'zfsrootselect',
                        'unpackfs',
                        'machineid',
                        'fstab',
                        'locale',
                        'keyboard',
                        'localecfg',
                        'users',
                        'displaymanager',
                        'networkcfg',
                        'securityhardening',
                        'hwclock',
                        'initramfscfg',
                        'initramfs',
                        'grubcfg',
                        'bootloader',
                        'opencoreinstall',
                        'umount',
                        'telemetryjob'
                    ]
                },
                {
                    'show': ['finished']
                }
            ]
        },
        'universal_config': {
            'detect_at_build': True,
            'detect_at_boot': True,
            'apply_optimal_settings': True,
            'use_hardware_db': True,
            'supported_vendors': [
                'Dell', 'HP/HPE', 'Lenovo', 'IBM', 'Supermicro',
                'Intel', 'AMD', 'ASUS', 'Gigabyte', 'MSI', 'ASRock'
            ],
            'unknown_hardware_mode': 'safe'
        }
    }
    
    with open(path, 'w') as f:
        yaml.dump(default_config, f, default_flow_style=False, sort_keys=False)
    
    print(f"[+] Created default configuration: {path}")
    print(f"[+] Configuration includes:")
    print(f"    - Universal hardware detection")
    print(f"    - Rich ZFS configuration with Calamares")
    print(f"    - 19 hardware profiles")
    print(f"    - Safe -O2 optimization")
    print(f"    - ZFS 2.3.3 from official repository")

if __name__ == "__main__":
    main()
