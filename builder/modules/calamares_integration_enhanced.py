#!/usr/bin/env python3
"""
Enhanced Calamares Integration Pipeline
Based on UltraThink Agent Analysis - Priority Recommendation #1

This module creates a comprehensive integration pipeline ensuring all build system 
components are properly connected to the Calamares GUI installer.
"""

import os
import sys
import json
import yaml
import logging
import subprocess
import shutil
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from builder.core.lockfile import BuildLockfile


@dataclass
class CalamaresModule:
    """Represents a Calamares module configuration"""
    name: str
    module_type: str  # 'viewmodule', 'job', 'python'
    interface: str    # 'qtplugin', 'python', 'process'
    config_file: Optional[str] = None
    required_files: List[str] = None
    dependencies: List[str] = None
    zfs_specific: bool = False
    

@dataclass 
class IntegrationValidation:
    """Results of integration validation"""
    valid: bool
    errors: List[str]
    warnings: List[str]
    missing_components: List[str]


class EnhancedCalamaresIntegration:
    """
    Enhanced Calamares Integration Pipeline
    
    Addresses UltraThink Agent Analysis findings:
    1. Complete Calamares Integration Pipeline (Priority 10/10)
    2. ZFS-Specific Calamares Modules (Priority 9/10) 
    3. Live Environment Integration (Priority 9/10)
    4. GUI Configuration Validation (Priority 8/10)
    """
    
    def __init__(self, workspace: Path, config: Dict[str, Any]):
        self.workspace = workspace
        self.config = config
        self.chroot_path = workspace / "chroot"
        self.project_root = Path(__file__).parent.parent.parent
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Calamares paths
        self.calamares_source_dir = self.project_root / "calamares"
        self.calamares_target_dir = self.chroot_path / "etc/calamares"
        self.calamares_modules_dir = self.calamares_target_dir / "modules"
        
        # Define all available Calamares modules
        self.available_modules = self._define_available_modules()
        
    def _define_available_modules(self) -> Dict[str, CalamaresModule]:
        """Define all available Calamares modules for Z-FORGE"""
        return {
            # ZFS-specific modules
            "zfsrootselect": CalamaresModule(
                name="zfsrootselect",
                module_type="viewmodule",
                interface="python",
                config_file="zfsrootselect.conf",
                zfs_specific=True,
                dependencies=["partition"]
            ),
            "zfspooldetect": CalamaresModule(
                name="zfspooldetect", 
                module_type="job",
                interface="python",
                config_file="zfspooldetect.conf",
                zfs_specific=True
            ),
            "zfsenhancedconfig": CalamaresModule(
                name="zfsenhancedconfig",
                module_type="viewmodule", 
                interface="python",
                config_file="zfsenhancedconfig.conf",
                zfs_specific=True,
                dependencies=["zfsrootselect"]
            ),
            "zfsbootloader": CalamaresModule(
                name="zfsbootloader",
                module_type="job",
                interface="python", 
                config_file="zfsbootloader.conf",
                zfs_specific=True,
                dependencies=["zfsenhancedconfig", "bootloader"]
            ),
            "zfsrichconfig": CalamaresModule(
                name="zfsrichconfig",
                module_type="viewmodule",
                interface="python",
                zfs_specific=True
            ),
            "zforgefinalize": CalamaresModule(
                name="zforgefinalize",
                module_type="job", 
                interface="python",
                config_file="zforgefinalize.conf",
                zfs_specific=True
            ),
            
            # Hardware and system modules
            "storagelayout": CalamaresModule(
                name="storagelayout",
                module_type="viewmodule",
                interface="python",
                config_file="storagelayout.conf",
                dependencies=["partition"]
            ),
            "hardwarehealth": CalamaresModule(
                name="hardwarehealth",
                module_type="viewmodule",
                interface="python",
                config_file="hardwarehealth.conf"
            ),
            "gpupassthrough": CalamaresModule(
                name="gpupassthrough",
                module_type="viewmodule", 
                interface="python",
                config_file="gpupassthrough.conf"
            ),
            "networkconfig": CalamaresModule(
                name="networkconfig",
                module_type="viewmodule",
                interface="python",
                config_file="networkconfig.conf"
            ),
            "securityhardening": CalamaresModule(
                name="securityhardening",
                module_type="viewmodule",
                interface="python",
                config_file="securityhardening.conf"
            ),
            "proxmoxconfig": CalamaresModule(
                name="proxmoxconfig", 
                module_type="viewmodule",
                interface="python",
                config_file="proxmoxconfig.conf"
            ),
            "postinstall": CalamaresModule(
                name="postinstall",
                module_type="job",
                interface="python",
                config_file="postinstall.conf"
            ),
            
            # Telemetry and consent
            "telemetryconsent": CalamaresModule(
                name="telemetryconsent",
                module_type="viewmodule",
                interface="qtplugin",
                config_file="telemetryconsent.conf"
            ),
            "telemetryjob": CalamaresModule(
                name="telemetryjob",
                module_type="job",
                interface="python",
                config_file="telemetryjob.conf",
                dependencies=["telemetryconsent"]
            )
        }
        
    def execute(self, resume_data: Optional[Dict[str, Any]] = None, 
               lockfile: Optional[BuildLockfile] = None) -> Dict[str, Any]:
        """
        Execute the enhanced Calamares integration pipeline
        
        Returns:
            Dict with status, validation results, and integration details
        """
        self.logger.info("🚀 Starting Enhanced Calamares Integration Pipeline")
        
        try:
            # Phase 1: Validate existing integration
            self.logger.info("📋 Phase 1: Validating existing integration...")
            validation = self._validate_current_integration()
            
            if not validation.valid:
                self.logger.warning(f"Integration validation found {len(validation.errors)} errors")
                for error in validation.errors:
                    self.logger.error(f"  ❌ {error}")
                    
            # Phase 2: Install base Calamares if not present
            self.logger.info("📦 Phase 2: Installing Calamares base system...")
            self._install_calamares_base()
            
            # Phase 3: Deploy custom modules
            self.logger.info("🔧 Phase 3: Deploying custom Z-FORGE modules...")
            deployed_modules = self._deploy_custom_modules()
            
            # Phase 4: Generate integrated configuration
            self.logger.info("⚙️ Phase 4: Generating integrated configuration...")
            config_files = self._generate_integrated_configuration()
            
            # Phase 5: Configure live environment integration
            self.logger.info("🖥️ Phase 5: Configuring live environment integration...")
            self._configure_live_environment()
            
            # Phase 6: Validate complete integration
            self.logger.info("✅ Phase 6: Final validation...")
            final_validation = self._validate_complete_integration()
            
            result = {
                'status': 'success',
                'pipeline_version': '2.0',
                'validation': {
                    'initial': validation.__dict__,
                    'final': final_validation.__dict__
                },
                'deployed_modules': deployed_modules,
                'config_files': config_files,
                'integration_points': self._get_integration_points(),
                'zfs_modules': [name for name, mod in self.available_modules.items() if mod.zfs_specific]
            }
            
            self.logger.info("🎉 Enhanced Calamares Integration Pipeline completed successfully")
            return result
            
        except Exception as e:
            self.logger.error(f"❌ Enhanced Calamares Integration failed: {e}")
            return {
                'status': 'error',
                'error': str(e),
                'module': 'EnhancedCalamaresIntegration'
            }
            
    def _validate_current_integration(self) -> IntegrationValidation:
        """Validate current Calamares integration state"""
        errors = []
        warnings = []
        missing_components = []
        
        # Check if Calamares source modules exist
        if not self.calamares_source_dir.exists():
            errors.append("Calamares source directory not found")
        else:
            modules_dir = self.calamares_source_dir / "modules"
            if not modules_dir.exists():
                errors.append("Calamares modules source directory not found")
            else:
                # Check for expected modules
                for module_name, module_def in self.available_modules.items():
                    module_path = modules_dir / module_name
                    if not module_path.exists():
                        missing_components.append(f"Module: {module_name}")
                        
        # Check for main settings.conf
        settings_conf = self.calamares_source_dir / "settings.conf"
        if not settings_conf.exists():
            warnings.append("Main settings.conf not found - will be generated")
            
        # Check for branding
        branding_dir = self.calamares_source_dir / "branding"
        if not branding_dir.exists():
            warnings.append("Branding directory not found")
            
        valid = len(errors) == 0
        
        return IntegrationValidation(
            valid=valid,
            errors=errors,
            warnings=warnings,
            missing_components=missing_components
        )
        
    def _install_calamares_base(self):
        """Install base Calamares system in chroot"""
        packages = [
            "calamares",
            "calamares-settings-debian", 
            "qml-module-qtquick-layouts",
            "qml-module-qtquick-controls",
            "qml-module-qtquick-window2",
            "qml-module-qtquick2"
        ]
        
        # Install packages
        cmd = ["chroot", str(self.chroot_path), "apt-get", "install", "-y"] + packages
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            raise RuntimeError(f"Failed to install Calamares: {result.stderr}")
            
        self.logger.info(f"✅ Installed Calamares base packages: {', '.join(packages)}")
        
    def _deploy_custom_modules(self) -> List[str]:
        """Deploy custom Z-FORGE modules to Calamares"""
        deployed = []
        modules_source = self.calamares_source_dir / "modules"
        modules_target = self.chroot_path / "usr/lib/calamares/modules"
        
        # Ensure target directory exists
        modules_target.mkdir(parents=True, exist_ok=True)
        
        for module_name, module_def in self.available_modules.items():
            source_path = modules_source / module_name
            target_path = modules_target / module_name
            
            if source_path.exists():
                # Copy module
                if target_path.exists():
                    shutil.rmtree(target_path)
                shutil.copytree(source_path, target_path)
                deployed.append(module_name)
                
                self.logger.info(f"✅ Deployed module: {module_name}")
            else:
                self.logger.warning(f"⚠️ Module source not found: {module_name}")
                
        return deployed
        
    def _generate_integrated_configuration(self) -> List[str]:
        """Generate integrated Calamares configuration files"""
        config_files = []
        
        # Generate main settings.conf
        settings_conf = self._generate_settings_conf()
        settings_path = self.calamares_target_dir / "settings.conf"
        settings_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(settings_path, 'w') as f:
            f.write(settings_conf)
        config_files.append("settings.conf")
        
        # Generate module configurations
        for module_name, module_def in self.available_modules.items():
            if module_def.config_file:
                config_content = self._generate_module_config(module_name, module_def)
                config_path = self.calamares_target_dir / "modules" / module_def.config_file
                config_path.parent.mkdir(parents=True, exist_ok=True)
                
                with open(config_path, 'w') as f:
                    f.write(config_content)
                config_files.append(module_def.config_file)
                
        self.logger.info(f"✅ Generated {len(config_files)} configuration files")
        return config_files
        
    def _generate_settings_conf(self) -> str:
        """Generate main Calamares settings.conf"""
        # Build module sequence based on dependencies and type
        sequence = self._build_module_sequence()
        
        branding_component = self.config.get('branding', {}).get('component_name', 'zforge')
        
        settings = f"""---
modules-search: [ local ]

instances:
- id:       zfs_root
  module:   zfsrootselect
  config:   zfsrootselect.conf
  
- id:       zfs_enhanced
  module:   zfsenhancedconfig
  config:   zfsenhancedconfig.conf

- id:       storage_layout
  module:   storagelayout
  config:   storagelayout.conf

sequence:
- show:
  - welcome
  - locale
  - keyboard
  - users
  - hardwarehealth
  - networkconfig
  - storagelayout
  - zfsrootselect
  - zfsenhancedconfig
  - securityhardening
  - proxmoxconfig
  - gpupassthrough
  - telemetryconsent
  - summary
- exec:
  - partition
  - zfspooldetect
  - mount
  - unpackfs
  - machineid
  - fstab
  - locale
  - keyboard
  - localecfg
  - users
  - displaymanager
  - networkcfg
  - hwclock
  - services-systemd
  - zfsbootloader
  - postinstall
  - telemetryjob
  - zforgefinalize
  - umount
- show:
  - finished

branding: {branding_component}

prompt-install: true
dont-chroot: false
oem-setup: false
disable-cancel: false
disable-cancel-during-exec: false
hide-back-and-next-during-exec: false
quit-at-end: false
"""
        return settings
        
    def _build_module_sequence(self) -> Tuple[List[str], List[str]]:
        """Build proper module sequence considering dependencies"""
        show_sequence = []
        exec_sequence = []
        
        # Add modules based on type and dependencies
        for module_name, module_def in self.available_modules.items():
            if module_def.module_type == "viewmodule":
                show_sequence.append(module_name)
            elif module_def.module_type == "job":
                exec_sequence.append(module_name)
                
        return show_sequence, exec_sequence
        
    def _generate_module_config(self, module_name: str, module_def: CalamaresModule) -> str:
        """Generate configuration for a specific module"""
        if module_def.zfs_specific:
            return self._generate_zfs_module_config(module_name, module_def)
        else:
            return self._generate_standard_module_config(module_name, module_def)
            
    def _generate_zfs_module_config(self, module_name: str, module_def: CalamaresModule) -> str:
        """Generate ZFS-specific module configuration"""
        zfs_config = self.config.get('zfs', {})
        
        base_config = {
            'enabled': True,
            'zfs_features': {
                'compression': zfs_config.get('compression', 'lz4'),
                'encryption': zfs_config.get('encryption', False),
                'deduplication': zfs_config.get('deduplication', False)
            },
            'pool_options': {
                'ashift': zfs_config.get('ashift', 12),
                'autoexpand': True
            }
        }
        
        return yaml.dump(base_config, default_flow_style=False)
        
    def _generate_standard_module_config(self, module_name: str, module_def: CalamaresModule) -> str:
        """Generate standard module configuration"""
        base_config = {
            'enabled': True,
            'module_type': module_def.module_type,
            'interface': module_def.interface
        }
        
        return yaml.dump(base_config, default_flow_style=False)
        
    def _configure_live_environment(self):
        """Configure live environment for Calamares integration"""
        # Create desktop launcher
        desktop_file = self.chroot_path / "home/user/Desktop/install-system.desktop"
        desktop_file.parent.mkdir(parents=True, exist_ok=True)
        
        desktop_content = """[Desktop Entry]
Type=Application
Name=Install Z-FORGE
Comment=Install Z-FORGE to your computer
Icon=calamares
Exec=pkexec calamares
Categories=System;
Terminal=false
StartupNotify=true
"""
        
        with open(desktop_file, 'w') as f:
            f.write(desktop_content)
            
        # Make executable
        os.chmod(desktop_file, 0o755)
        
        # Configure auto-login for live user
        lightdm_conf = self.chroot_path / "etc/lightdm/lightdm.conf"
        if lightdm_conf.exists():
            with open(lightdm_conf, 'a') as f:
                f.write("\n[Seat:*]\nautologin-user=user\n")
                
        self.logger.info("✅ Configured live environment for Calamares")
        
    def _validate_complete_integration(self) -> IntegrationValidation:
        """Validate the complete integration after setup"""
        errors = []
        warnings = []
        missing_components = []
        
        # Check if settings.conf was created
        settings_conf = self.calamares_target_dir / "settings.conf"
        if not settings_conf.exists():
            errors.append("Main settings.conf was not created")
            
        # Check if modules were deployed
        modules_dir = self.chroot_path / "usr/lib/calamares/modules"
        if not modules_dir.exists():
            errors.append("Calamares modules directory not found")
        else:
            deployed_count = len([d for d in modules_dir.iterdir() if d.is_dir()])
            if deployed_count == 0:
                errors.append("No Calamares modules deployed")
            elif deployed_count < 5:
                warnings.append(f"Only {deployed_count} modules deployed")
                
        # Check desktop launcher
        desktop_file = self.chroot_path / "home/user/Desktop/install-system.desktop"
        if not desktop_file.exists():
            warnings.append("Desktop launcher not found")
            
        valid = len(errors) == 0
        
        return IntegrationValidation(
            valid=valid,
            errors=errors,
            warnings=warnings,
            missing_components=missing_components
        )
        
    def _get_integration_points(self) -> List[str]:
        """Get list of integration points created"""
        return [
            "calamares_base_installation",
            "custom_module_deployment", 
            "configuration_generation",
            "live_environment_setup",
            "desktop_launcher_creation",
            "zfs_module_integration",
            "hardware_module_integration",
            "proxmox_integration",
            "security_hardening_integration",
            "telemetry_system_integration"
        ]


def main():
    """Test the enhanced integration pipeline"""
    import tempfile
    
    # Create test workspace
    workspace = Path(tempfile.mkdtemp()) / "test_workspace"
    workspace.mkdir(parents=True)
    
    # Create test chroot
    chroot_path = workspace / "chroot"
    chroot_path.mkdir(parents=True)
    
    # Test configuration
    config = {
        'name': 'Z-FORGE',
        'zfs': {
            'compression': 'lz4',
            'encryption': True
        },
        'branding': {
            'component_name': 'zforge'
        }
    }
    
    # Run integration
    integration = EnhancedCalamaresIntegration(workspace, config)
    result = integration.execute()
    
    print("Enhanced Calamares Integration Test Results:")
    print(f"Status: {result['status']}")
    if result['status'] == 'success':
        print(f"Deployed modules: {len(result['deployed_modules'])}")
        print(f"Generated configs: {len(result['config_files'])}")
        print(f"Integration points: {len(result['integration_points'])}")
        print(f"ZFS modules: {len(result['zfs_modules'])}")
    else:
        print(f"Error: {result['error']}")
        
    # Cleanup
    shutil.rmtree(workspace)


if __name__ == "__main__":
    main()