"""
Calamares Install Prebuilt Module

Installs prebuilt Calamares installer packages
"""

import os
import shutil
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional
import logging


class CalamaresInstallPrebuilt:
    """Install prebuilt Calamares packages"""
    
    def __init__(self, workspace: Path, config: Dict[str, Any]):
        self.workspace = workspace
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)
        self.chroot_path = workspace / "chroot"
        self.packages_dir = self.config.get('packages_dir', 'prebuilt_packages/calamares')
        
    def execute(self, resume_data: Optional[Dict] = None, lockfile: Optional[Any] = None) -> Dict:
        """Install Calamares packages in chroot"""
        try:
            self.logger.info("Installing prebuilt Calamares installer...")
            
            # Check packages directory
            # packages_dir is relative to chroot
            chroot_pkg_path = self.chroot_path / self.packages_dir
            
            if not chroot_pkg_path.exists():
                self.logger.warning(f"Calamares package directory not found: {chroot_pkg_path}")
                return self._install_from_repository()
                
            # List packages
            packages = list(chroot_pkg_path.glob("*.deb"))
            if not packages:
                self.logger.warning("No Calamares packages found")
                return self._install_from_repository()
                
            self.logger.info(f"Found {len(packages)} Calamares packages")
            
            # Install Calamares packages
            installed_count = 0
            for pkg in packages:
                self.logger.info(f"Installing {pkg.name}...")
                install_cmd = f"dpkg -i {pkg_path}/{pkg.name}"
                if self._run_in_chroot(install_cmd):
                    installed_count += 1
                
            # Fix dependencies
            self.logger.info("Fixing dependencies...")
            self._run_in_chroot("apt-get -f install -y")
            
            # Configure Calamares
            self._configure_calamares()
            
            # Copy Z-FORGE modules
            self._install_zforge_modules()
            
            # Verify installation
            verify_cmd = "which calamares"
            output = self._run_in_chroot_output(verify_cmd)
            
            if output and 'calamares' in output:
                self.logger.info("Calamares installed successfully")
                return {
                    'status': 'success',
                    'packages_installed': installed_count,
                    'total_packages': len(packages),
                    'calamares_path': output
                }
            else:
                self.logger.error("Calamares not properly installed")
                return {
                    'status': 'error',
                    'error': 'Calamares not properly installed',
                    'module': self.__class__.__name__
                }
                
        except Exception as e:
            self.logger.error(f"Failed to install Calamares: {e}")
            return {
                'status': 'error',
                'error': str(e),
                'module': self.__class__.__name__
            }
            
    def _run_in_chroot(self, command: str) -> bool:
        """Run command in chroot environment"""
        try:
            full_cmd = f"chroot {self.chroot_path} /bin/bash -c '{command}'"
            result = subprocess.run(full_cmd, shell=True, capture_output=True, text=True)
            if result.returncode != 0:
                self.logger.warning(f"Command failed: {command}")
                return False
            return True
        except Exception as e:
            self.logger.error(f"Failed to run command in chroot: {e}")
            return False
            
    def _run_in_chroot_output(self, command: str) -> str:
        """Run command in chroot and return output"""
        try:
            full_cmd = f"chroot {self.chroot_path} /bin/bash -c '{command}'"
            result = subprocess.run(full_cmd, shell=True, capture_output=True, text=True)
            return result.stdout.strip() if result.returncode == 0 else ""
        except Exception as e:
            self.logger.error(f"Failed to run command in chroot: {e}")
            return ""
            
    def _install_from_repository(self) -> Dict:
        """Fallback: Install from repository"""
        try:
            self.logger.info("Installing Calamares from repository...")
            
            # Install Calamares and dependencies
            install_cmd = """
                apt-get update
                apt-get install -y calamares calamares-settings-debian \
                    qml-module-qtquick2 qml-module-qtquick-controls \
                    qml-module-qtquick-controls2 qml-module-qtquick-window2 \
                    qml-module-qtquick-layouts qml-module-qt-labs-platform
            """
            
            if self._run_in_chroot(install_cmd):
                return {
                    'status': 'success',
                    'installation_method': 'repository',
                    'packages_installed': 8
                }
            else:
                return {
                    'status': 'error',
                    'error': 'Failed to install from repository',
                    'module': self.__class__.__name__
                }
            
        except Exception as e:
            self.logger.error(f"Failed to install from repository: {e}")
            return {
                'status': 'error',
                'error': str(e),
                'module': self.__class__.__name__
            }
            
    def _configure_calamares(self):
        """Configure Calamares for Z-FORGE"""
        try:
            self.logger.info("Configuring Calamares...")
            
            # Create config directory
            config_dir = self.chroot_path / "etc/calamares"
            config_dir.mkdir(parents=True, exist_ok=True)
            
            # Copy Z-FORGE configuration if available
            project_calamares = Path(__file__).parent.parent.parent / "calamares"
            if project_calamares.exists():
                # Copy settings.conf
                settings_src = project_calamares / "settings.conf"
                if settings_src.exists():
                    shutil.copy2(settings_src, config_dir / "settings.conf")
                    
                # Copy branding
                branding_src = project_calamares / "branding"
                if branding_src.exists():
                    branding_dst = config_dir / "branding"
                    if branding_dst.exists():
                        shutil.rmtree(branding_dst)
                    shutil.copytree(branding_src, branding_dst)
                    
            # Create desktop entry
            desktop_entry = """[Desktop Entry]
Type=Application
Version=1.0
Name=Install Z-FORGE
Comment=Install Z-FORGE Linux with ZFS
Exec=sudo -E calamares
Icon=calamares
Terminal=false
StartupNotify=true
Categories=Qt;System;
X-AppStream-Ignore=true
"""
            
            desktop_dir = self.chroot_path / "usr/share/applications"
            desktop_dir.mkdir(parents=True, exist_ok=True)
            (desktop_dir / "calamares.desktop").write_text(desktop_entry)
            
            self.logger.info("Calamares configured")
            
        except Exception as e:
            self.logger.warning(f"Failed to configure Calamares: {e}")
            
    def _install_zforge_modules(self):
        """Install Z-FORGE specific Calamares modules"""
        try:
            self.logger.info("Installing Z-FORGE Calamares modules...")
            
            # Source and destination for modules
            modules_src = Path(__file__).parent.parent.parent / "calamares/modules"
            modules_dst = self.chroot_path / "usr/lib/calamares/modules"
            
            if not modules_src.exists():
                self.logger.warning("Z-FORGE Calamares modules not found")
                return
                
            modules_dst.mkdir(parents=True, exist_ok=True)
            
            # Copy each module
            for module_dir in modules_src.iterdir():
                if module_dir.is_dir():
                    module_name = module_dir.name
                    self.logger.info(f"Installing module: {module_name}")
                    
                    dst_module = modules_dst / module_name
                    if dst_module.exists():
                        shutil.rmtree(dst_module)
                    shutil.copytree(module_dir, dst_module)
                    
                    # Make main.py executable
                    main_py = dst_module / "main.py"
                    if main_py.exists():
                        main_py.chmod(0o755)
                        
            self.logger.info("Z-FORGE modules installed")
            
        except Exception as e:
            self.logger.warning(f"Failed to install Z-FORGE modules: {e}")
            
    def validate_config(self) -> bool:
        """Validate module configuration"""
        return True