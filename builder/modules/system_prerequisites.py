#!/usr/bin/env python3
"""
System Prerequisites Check Module for Z-FORGE
Ensures the build environment meets all requirements before starting
"""

import os
import subprocess
import shutil
from pathlib import Path
from typing import Dict, Any, Optional, List
import logging
import psutil

class SystemPrerequisites:
    """Check and ensure system meets build requirements"""
    
    def __init__(self, workspace: Path, config: Dict):
        self.workspace = workspace
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.min_disk_gb = 20
        self.min_memory_gb = 4
        
    def execute(self, resume_data: Optional[Dict] = None, lockfile: Optional[Any] = None) -> Dict:
        """Run all prerequisite checks"""
        try:
            self.logger.info("Checking system prerequisites...")
            
            checks = {
                'sudo_access': self._check_sudo_access(),
                'disk_space': self._check_disk_space(),
                'memory': self._check_memory(),
                'network': self._check_network(),
                'required_commands': self._check_required_commands(),
                'kernel_modules': self._check_kernel_modules(),
                'cpu_features': self._check_cpu_features()
            }
            
            failed_checks = [k for k, v in checks.items() if not v['passed']]
            
            if failed_checks:
                self.logger.error(f"Failed prerequisite checks: {', '.join(failed_checks)}")
                return {
                    'status': 'error',
                    'failed_checks': failed_checks,
                    'details': checks
                }
            
            self.logger.info("All system prerequisites passed!")
            return {
                'status': 'success',
                'checks': checks
            }
            
        except Exception as e:
            self.logger.error(f"Failed to check prerequisites: {e}")
            return {
                'status': 'error',
                'error': str(e),
                'module': self.__class__.__name__
            }
    
    def _check_sudo_access(self) -> Dict[str, Any]:
        """Check if we have passwordless sudo or cached credentials"""
        try:
            result = subprocess.run(
                ['sudo', '-n', 'true'],
                capture_output=True,
                timeout=5
            )
            return {
                'passed': result.returncode == 0,
                'message': 'Sudo access available' if result.returncode == 0 else 'Sudo requires password'
            }
        except Exception as e:
            return {'passed': False, 'message': f'Sudo check failed: {e}'}
    
    def _check_disk_space(self) -> Dict[str, Any]:
        """Check available disk space"""
        try:
            # Check workspace parent directory
            if self.workspace.exists():
                check_path = self.workspace
            else:
                check_path = self.workspace.parent
                
            stat = os.statvfs(check_path)
            free_gb = (stat.f_bavail * stat.f_frsize) / (1024**3)
            
            return {
                'passed': free_gb >= self.min_disk_gb,
                'message': f'Available: {free_gb:.1f}GB (required: {self.min_disk_gb}GB)',
                'free_gb': free_gb
            }
        except Exception as e:
            return {'passed': False, 'message': f'Disk check failed: {e}'}
    
    def _check_memory(self) -> Dict[str, Any]:
        """Check available memory"""
        try:
            mem = psutil.virtual_memory()
            total_gb = mem.total / (1024**3)
            available_gb = mem.available / (1024**3)
            
            return {
                'passed': total_gb >= self.min_memory_gb,
                'message': f'Total: {total_gb:.1f}GB, Available: {available_gb:.1f}GB',
                'total_gb': total_gb,
                'available_gb': available_gb
            }
        except Exception as e:
            return {'passed': False, 'message': f'Memory check failed: {e}'}
    
    def _check_network(self) -> Dict[str, Any]:
        """Check network connectivity"""
        test_hosts = [
            ('deb.debian.org', 'Debian repository'),
            ('github.com', 'GitHub'),
            ('kernel.org', 'Kernel.org')
        ]
        
        failed = []
        for host, name in test_hosts:
            try:
                result = subprocess.run(
                    ['ping', '-c', '1', '-W', '2', host],
                    capture_output=True,
                    timeout=5
                )
                if result.returncode != 0:
                    failed.append(name)
            except:
                failed.append(name)
        
        return {
            'passed': len(failed) == 0,
            'message': 'Network connectivity OK' if not failed else f'Cannot reach: {", ".join(failed)}',
            'failed_hosts': failed
        }
    
    def _check_required_commands(self) -> Dict[str, Any]:
        """Check for required commands"""
        required = [
            'debootstrap', 'mkisofs', 'xorriso', 'mksquashfs',
            'git', 'wget', 'curl', 'gpg', 'gcc', 'make'
        ]
        
        missing = []
        for cmd in required:
            if not shutil.which(cmd):
                missing.append(cmd)
        
        return {
            'passed': len(missing) == 0,
            'message': 'All commands available' if not missing else f'Missing: {", ".join(missing)}',
            'missing_commands': missing
        }
    
    def _check_kernel_modules(self) -> Dict[str, Any]:
        """Check for required kernel modules"""
        modules = ['loop', 'squashfs', 'overlay']
        missing = []
        
        for module in modules:
            try:
                result = subprocess.run(
                    ['modprobe', '-n', module],
                    capture_output=True
                )
                if result.returncode != 0:
                    missing.append(module)
            except:
                missing.append(module)
        
        return {
            'passed': len(missing) == 0,
            'message': 'Kernel modules OK' if not missing else f'Missing modules: {", ".join(missing)}',
            'missing_modules': missing
        }
    
    def _check_cpu_features(self) -> Dict[str, Any]:
        """Check CPU features for optimization"""
        features = {
            'aes': False,
            'avx': False,
            'avx2': False,
            'avx512': False
        }
        
        try:
            cpuinfo = Path('/proc/cpuinfo').read_text()
            if 'aes' in cpuinfo:
                features['aes'] = True
            if 'avx' in cpuinfo and 'avx2' not in cpuinfo:
                features['avx'] = True
            if 'avx2' in cpuinfo:
                features['avx2'] = True
            if 'avx512' in cpuinfo:
                features['avx512'] = True
                
            return {
                'passed': True,
                'message': f'CPU features detected',
                'features': features
            }
        except Exception as e:
            return {
                'passed': True,  # Not critical
                'message': f'Could not detect CPU features: {e}',
                'features': features
            }