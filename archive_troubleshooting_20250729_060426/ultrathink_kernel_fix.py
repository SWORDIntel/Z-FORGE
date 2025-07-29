#!/usr/bin/env python3
"""
UltraThink Multi-Agent System for Z-FORGE Kernel/ZFS Installation Fix

This system deploys multiple specialized agents to comprehensively solve
the kernel and ZFS installation issues through parallel analysis and
multiple solution strategies.
"""

import subprocess
import os
import sys
import time
import json
import logging
import threading
import queue
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Tuple, Optional
import multiprocessing
from concurrent.futures import ThreadPoolExecutor, as_completed

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - [%(agent)s] %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'/opt/github/Z-FORGE/ultrathink_fix_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'),
        logging.StreamHandler()
    ]
)

class BaseAgent:
    """Base class for all UltraThink agents"""
    
    def __init__(self, name: str, chroot_path: str = "/tmp/zforge_workspace/chroot"):
        self.name = name
        self.chroot_path = Path(chroot_path)
        self.logger = logging.LoggerAdapter(logging.getLogger(), {'agent': name})
        self.results = {}
        
    def execute(self) -> Dict[str, Any]:
        """Execute agent's primary task"""
        raise NotImplementedError
        
    def run_command(self, cmd: List[str], check: bool = False) -> subprocess.CompletedProcess:
        """Run a command and return result"""
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=check)
            return result
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Command failed: {' '.join(cmd)}")
            self.logger.error(f"Error: {e.stderr}")
            return e
            
    def chroot_command(self, cmd: List[str], check: bool = False) -> subprocess.CompletedProcess:
        """Run command in chroot"""
        full_cmd = ['sudo', 'chroot', str(self.chroot_path)] + cmd
        return self.run_command(full_cmd, check)

class DiagnosticAgent(BaseAgent):
    """Agent that performs comprehensive system diagnosis"""
    
    def execute(self) -> Dict[str, Any]:
        self.logger.info("Starting comprehensive diagnosis")
        
        diagnosis = {
            'timestamp': datetime.now().isoformat(),
            'chroot_exists': self.chroot_path.exists(),
            'debian_version': self._get_debian_version(),
            'apt_sources': self._analyze_apt_sources(),
            'kernel_status': self._check_kernel_status(),
            'dpkg_status': self._check_dpkg_status(),
            'zfs_status': self._check_zfs_status(),
            'problems_found': []
        }
        
        # Analyze problems
        if diagnosis['debian_version']['codename'] != 'trixie':
            diagnosis['problems_found'].append('Not running Trixie')
            
        if '6.1.' in str(diagnosis['kernel_status'].get('available_kernel', '')):
            diagnosis['problems_found'].append('Wrong kernel version available (Bookworm kernel)')
            
        if diagnosis['dpkg_status']['has_errors']:
            diagnosis['problems_found'].append('DPKG database has errors')
            
        if not diagnosis['apt_sources']['has_contrib']:
            diagnosis['problems_found'].append('APT sources missing contrib repository')
            
        self.results = diagnosis
        return diagnosis
        
    def _get_debian_version(self) -> Dict[str, str]:
        """Get Debian version information"""
        version_info = {'codename': 'unknown', 'version': 'unknown'}
        
        os_release = self.chroot_path / 'etc/os-release'
        if os_release.exists():
            try:
                with open(os_release, 'r') as f:
                    for line in f:
                        if 'VERSION_CODENAME=' in line:
                            version_info['codename'] = line.split('=')[1].strip().strip('"')
                        elif 'VERSION_ID=' in line:
                            version_info['version'] = line.split('=')[1].strip().strip('"')
            except Exception as e:
                self.logger.error(f"Error reading os-release: {e}")
                
        return version_info
        
    def _analyze_apt_sources(self) -> Dict[str, Any]:
        """Analyze APT sources configuration"""
        sources_info = {
            'configured': False,
            'has_contrib': False,
            'using_testing': False,
            'sources': []
        }
        
        sources_list = self.chroot_path / 'etc/apt/sources.list'
        if sources_list.exists():
            try:
                with open(sources_list, 'r') as f:
                    content = f.read()
                    sources_info['configured'] = True
                    sources_info['has_contrib'] = 'contrib' in content
                    sources_info['using_testing'] = 'testing' in content or 'trixie' in content
                    sources_info['sources'] = content.split('\n')[:5]  # First 5 lines
            except Exception as e:
                self.logger.error(f"Error reading sources.list: {e}")
                
        return sources_info
        
    def _check_kernel_status(self) -> Dict[str, Any]:
        """Check kernel installation status"""
        kernel_info = {
            'installed_kernels': [],
            'available_kernel': None,
            'has_headers': False
        }
        
        # Check installed kernels
        result = self.chroot_command(['dpkg', '-l'], check=False)
        if result.returncode == 0:
            for line in result.stdout.split('\n'):
                if 'linux-image-' in line and line.startswith('ii'):
                    kernel_info['installed_kernels'].append(line.split()[1])
                if 'linux-headers-' in line and line.startswith('ii'):
                    kernel_info['has_headers'] = True
                    
        # Check available kernel
        result = self.chroot_command(['apt-cache', 'policy', 'linux-image-amd64'], check=False)
        if result.returncode == 0:
            for line in result.stdout.split('\n'):
                if 'Candidate:' in line:
                    kernel_info['available_kernel'] = line.split(':')[1].strip()
                    break
                    
        return kernel_info
        
    def _check_dpkg_status(self) -> Dict[str, bool]:
        """Check DPKG database status"""
        result = self.chroot_command(['dpkg', '--audit'], check=False)
        return {
            'has_errors': result.returncode != 0,
            'error_output': result.stderr if result.returncode != 0 else None
        }
        
    def _check_zfs_status(self) -> Dict[str, Any]:
        """Check ZFS installation status"""
        zfs_info = {'installed': False, 'packages': [], 'dkms_status': None}
        
        result = self.chroot_command(['dpkg', '-l'], check=False)
        if result.returncode == 0:
            for line in result.stdout.split('\n'):
                if 'zfs' in line and line.startswith('ii'):
                    zfs_info['installed'] = True
                    zfs_info['packages'].append(line.split()[1])
                    
        # Check DKMS
        result = self.chroot_command(['dkms', 'status'], check=False)
        if result.returncode == 0:
            zfs_info['dkms_status'] = result.stdout.strip()
            
        return zfs_info

class RepairAgent(BaseAgent):
    """Agent that repairs DPKG and APT issues"""
    
    def execute(self) -> Dict[str, Any]:
        self.logger.info("Starting system repair")
        
        repair_results = {
            'dpkg_fixed': False,
            'apt_fixed': False,
            'locks_removed': False,
            'actions_taken': []
        }
        
        # Fix DPKG
        self.logger.info("Fixing DPKG database...")
        result = self.chroot_command(['dpkg', '--configure', '-a'], check=False)
        if result.returncode == 0:
            repair_results['dpkg_fixed'] = True
            repair_results['actions_taken'].append('Configured pending packages')
            
        # Fix broken packages
        result = self.chroot_command(['apt-get', 'install', '-f', '-y'], check=False)
        if result.returncode == 0:
            repair_results['apt_fixed'] = True
            repair_results['actions_taken'].append('Fixed broken dependencies')
            
        # Remove locks
        lock_files = [
            self.chroot_path / 'var/lib/dpkg/lock',
            self.chroot_path / 'var/lib/dpkg/lock-frontend',
            self.chroot_path / 'var/cache/apt/archives/lock',
            self.chroot_path / 'var/lib/apt/lists/lock'
        ]
        
        for lock_file in lock_files:
            if lock_file.exists():
                try:
                    self.run_command(['sudo', 'rm', '-f', str(lock_file)])
                    repair_results['locks_removed'] = True
                    repair_results['actions_taken'].append(f'Removed lock: {lock_file.name}')
                except Exception as e:
                    self.logger.error(f"Failed to remove lock {lock_file}: {e}")
                    
        self.results = repair_results
        return repair_results

class RepositoryFixAgent(BaseAgent):
    """Agent that fixes APT repository configuration"""
    
    def execute(self) -> Dict[str, Any]:
        self.logger.info("Fixing APT repositories for Trixie")
        
        fix_results = {
            'sources_updated': False,
            'cache_cleared': False,
            'index_updated': False,
            'kernel_available': None
        }
        
        # Update sources.list
        sources_content = """# Debian Testing (Trixie) repositories
deb http://deb.debian.org/debian testing main contrib non-free-firmware
deb-src http://deb.debian.org/debian testing main contrib non-free-firmware

deb http://deb.debian.org/debian-security testing-security main contrib non-free-firmware
deb-src http://deb.debian.org/debian-security testing-security main contrib non-free-firmware

# Explicitly use trixie
deb http://deb.debian.org/debian trixie main contrib non-free-firmware
deb-src http://deb.debian.org/debian trixie main contrib non-free-firmware
"""
        
        # Write sources.list
        try:
            import tempfile
            with tempfile.NamedTemporaryFile(mode='w', delete=False) as tmp:
                tmp.write(sources_content)
                tmp_path = tmp.name
                
            self.run_command(['sudo', 'cp', tmp_path, str(self.chroot_path / 'etc/apt/sources.list')], check=True)
            Path(tmp_path).unlink()
            fix_results['sources_updated'] = True
            self.logger.info("Sources.list updated successfully")
        except Exception as e:
            self.logger.error(f"Failed to update sources.list: {e}")
            
        # Clear cache
        self.logger.info("Clearing APT cache...")
        self.chroot_command(['apt-get', 'clean'])
        self.run_command(['sudo', 'rm', '-rf', str(self.chroot_path / 'var/lib/apt/lists/*')])
        fix_results['cache_cleared'] = True
        
        # Update index
        self.logger.info("Updating package index...")
        result = self.chroot_command(['apt-get', 'update'], check=False)
        if result.returncode == 0:
            fix_results['index_updated'] = True
            
            # Check available kernel
            result = self.chroot_command(['apt-cache', 'search', '^linux-image-6.12'], check=False)
            if result.returncode == 0 and result.stdout:
                fix_results['kernel_available'] = '6.12.x kernel found'
            else:
                fix_results['kernel_available'] = 'No 6.12.x kernel found'
                
        self.results = fix_results
        return fix_results

class KernelInstallAgent(BaseAgent):
    """Agent that installs the correct kernel with multiple strategies"""
    
    def __init__(self, name: str, strategy: str, chroot_path: str = "/tmp/zforge_workspace/chroot"):
        super().__init__(name, chroot_path)
        self.strategy = strategy
        
    def execute(self) -> Dict[str, Any]:
        self.logger.info(f"Installing kernel using strategy: {self.strategy}")
        
        install_results = {
            'strategy': self.strategy,
            'success': False,
            'kernel_installed': None,
            'error': None
        }
        
        try:
            if self.strategy == 'specific_612':
                # Try specific 6.12 kernel
                result = self.chroot_command([
                    'apt-get', 'install', '-y',
                    'linux-image-6.12.38+deb13-amd64',
                    'linux-headers-6.12.38+deb13-amd64',
                    'build-essential', 'dkms'
                ], check=False)
                
                if result.returncode == 0:
                    install_results['success'] = True
                    install_results['kernel_installed'] = '6.12.38+deb13-amd64'
                else:
                    install_results['error'] = result.stderr
                    
            elif self.strategy == 'metapackage':
                # Try metapackage
                result = self.chroot_command([
                    'apt-get', 'install', '-y',
                    'linux-image-amd64',
                    'linux-headers-amd64',
                    'build-essential', 'dkms'
                ], check=False)
                
                if result.returncode == 0:
                    install_results['success'] = True
                    install_results['kernel_installed'] = 'metapackage'
                else:
                    install_results['error'] = result.stderr
                    
            elif self.strategy == 'latest_available':
                # Find and install latest available
                search_result = self.chroot_command(['apt-cache', 'search', '^linux-image-[0-9]'], check=False)
                if search_result.returncode == 0:
                    kernels = [line.split()[0] for line in search_result.stdout.split('\n') 
                              if line and 'dbg' not in line and 'cloud' not in line]
                    
                    if kernels:
                        latest = sorted(kernels)[-1]
                        version = latest.replace('linux-image-', '')
                        
                        result = self.chroot_command([
                            'apt-get', 'install', '-y',
                            latest,
                            f'linux-headers-{version}',
                            'build-essential', 'dkms'
                        ], check=False)
                        
                        if result.returncode == 0:
                            install_results['success'] = True
                            install_results['kernel_installed'] = version
                        else:
                            install_results['error'] = result.stderr
                            
        except Exception as e:
            install_results['error'] = str(e)
            
        self.results = install_results
        return install_results

class ZFSInstallAgent(BaseAgent):
    """Agent that installs ZFS packages"""
    
    def execute(self) -> Dict[str, Any]:
        self.logger.info("Installing ZFS packages")
        
        zfs_results = {
            'success': False,
            'packages_installed': [],
            'dkms_built': False,
            'error': None
        }
        
        # Remove conflicting packages
        self.chroot_command(['apt-get', 'remove', '-y', 'zfs-initramfs'], check=False)
        
        # Install ZFS packages
        packages = ['zfsutils-linux', 'zfs-dkms']
        result = self.chroot_command(['apt-get', 'install', '-y'] + packages, check=False)
        
        if result.returncode == 0:
            zfs_results['success'] = True
            zfs_results['packages_installed'] = packages
            
            # Try dracut support
            result = self.chroot_command(['apt-get', 'install', '-y', 'zfs-dracut'], check=False)
            if result.returncode == 0:
                zfs_results['packages_installed'].append('zfs-dracut')
                
            # Check DKMS build
            result = self.chroot_command(['dkms', 'status'], check=False)
            if result.returncode == 0 and 'zfs' in result.stdout:
                zfs_results['dkms_built'] = True
        else:
            zfs_results['error'] = result.stderr
            
        self.results = zfs_results
        return zfs_results

class VerificationAgent(BaseAgent):
    """Agent that verifies the fix was successful"""
    
    def execute(self) -> Dict[str, Any]:
        self.logger.info("Verifying system state")
        
        verification = {
            'kernel_correct': False,
            'zfs_ready': False,
            'system_healthy': False,
            'details': {}
        }
        
        # Check kernel
        result = self.chroot_command(['uname', '-r'], check=False)
        if result.returncode == 0:
            kernel_version = result.stdout.strip()
            verification['details']['running_kernel'] = kernel_version
            
        # Check installed kernels
        result = self.chroot_command(['dpkg', '-l'], check=False)
        if result.returncode == 0:
            for line in result.stdout.split('\n'):
                if 'linux-image-6.12' in line and line.startswith('ii'):
                    verification['kernel_correct'] = True
                    verification['details']['correct_kernel_installed'] = True
                    break
                    
        # Check ZFS
        result = self.chroot_command(['which', 'zfs'], check=False)
        if result.returncode == 0:
            verification['zfs_ready'] = True
            
        # Overall health
        verification['system_healthy'] = verification['kernel_correct'] and verification['zfs_ready']
        
        self.results = verification
        return verification

class UltraThinkCoordinator:
    """Main coordinator for the UltraThink multi-agent system"""
    
    def __init__(self):
        self.logger = logging.LoggerAdapter(logging.getLogger(), {'agent': 'Coordinator'})
        self.agents = []
        self.results = {}
        
    def deploy_agents(self):
        """Deploy all agents and coordinate their actions"""
        self.logger.info("=== UltraThink Multi-Agent System Starting ===")
        
        # Phase 1: Diagnosis
        self.logger.info("Phase 1: Comprehensive Diagnosis")
        diagnostic_agent = DiagnosticAgent("DiagnosticAgent")
        diagnosis = diagnostic_agent.execute()
        self.results['diagnosis'] = diagnosis
        
        self.logger.info(f"Problems found: {diagnosis['problems_found']}")
        
        # Phase 2: Repair
        self.logger.info("Phase 2: System Repair")
        repair_agent = RepairAgent("RepairAgent")
        repair_results = repair_agent.execute()
        self.results['repair'] = repair_results
        
        # Phase 3: Fix Repositories
        self.logger.info("Phase 3: Repository Configuration")
        repo_agent = RepositoryFixAgent("RepositoryAgent")
        repo_results = repo_agent.execute()
        self.results['repository'] = repo_results
        
        # Phase 4: Parallel Kernel Installation
        self.logger.info("Phase 4: Parallel Kernel Installation Strategies")
        kernel_strategies = ['specific_612', 'metapackage', 'latest_available']
        kernel_results = {}
        
        with ThreadPoolExecutor(max_workers=3) as executor:
            future_to_strategy = {
                executor.submit(
                    KernelInstallAgent(f"KernelAgent-{strategy}", strategy).execute
                ): strategy 
                for strategy in kernel_strategies
            }
            
            for future in as_completed(future_to_strategy):
                strategy = future_to_strategy[future]
                try:
                    result = future.result()
                    kernel_results[strategy] = result
                    if result['success']:
                        self.logger.info(f"Kernel installation succeeded with strategy: {strategy}")
                        break
                except Exception as e:
                    self.logger.error(f"Strategy {strategy} failed: {e}")
                    
        self.results['kernel_installation'] = kernel_results
        
        # Phase 5: ZFS Installation
        self.logger.info("Phase 5: ZFS Installation")
        zfs_agent = ZFSInstallAgent("ZFSAgent")
        zfs_results = zfs_agent.execute()
        self.results['zfs'] = zfs_results
        
        # Phase 6: Verification
        self.logger.info("Phase 6: System Verification")
        verify_agent = VerificationAgent("VerificationAgent")
        verification = verify_agent.execute()
        self.results['verification'] = verification
        
        # Generate report
        self._generate_report()
        
    def _generate_report(self):
        """Generate comprehensive report"""
        self.logger.info("\n=== UltraThink Multi-Agent System Report ===")
        
        # Success status
        success = self.results.get('verification', {}).get('system_healthy', False)
        
        if success:
            self.logger.info("✅ SYSTEM SUCCESSFULLY FIXED!")
        else:
            self.logger.info("❌ SYSTEM STILL HAS ISSUES")
            
        # Detailed results
        self.logger.info("\nDetailed Results:")
        
        # Diagnosis
        diagnosis = self.results.get('diagnosis', {})
        self.logger.info(f"\n1. Diagnosis:")
        self.logger.info(f"   - Debian Version: {diagnosis.get('debian_version', {}).get('codename', 'unknown')}")
        self.logger.info(f"   - Problems Found: {diagnosis.get('problems_found', [])}")
        
        # Repair
        repair = self.results.get('repair', {})
        self.logger.info(f"\n2. Repair Actions:")
        for action in repair.get('actions_taken', []):
            self.logger.info(f"   - {action}")
            
        # Repository
        repo = self.results.get('repository', {})
        self.logger.info(f"\n3. Repository Fix:")
        self.logger.info(f"   - Sources Updated: {repo.get('sources_updated', False)}")
        self.logger.info(f"   - Kernel Available: {repo.get('kernel_available', 'unknown')}")
        
        # Kernel
        kernel = self.results.get('kernel_installation', {})
        self.logger.info(f"\n4. Kernel Installation:")
        for strategy, result in kernel.items():
            if result.get('success'):
                self.logger.info(f"   - Success with {strategy}: {result.get('kernel_installed')}")
                break
        else:
            self.logger.info(f"   - All strategies failed")
            
        # ZFS
        zfs = self.results.get('zfs', {})
        self.logger.info(f"\n5. ZFS Installation:")
        self.logger.info(f"   - Success: {zfs.get('success', False)}")
        self.logger.info(f"   - Packages: {zfs.get('packages_installed', [])}")
        
        # Verification
        verify = self.results.get('verification', {})
        self.logger.info(f"\n6. Final Verification:")
        self.logger.info(f"   - Kernel Correct: {verify.get('kernel_correct', False)}")
        self.logger.info(f"   - ZFS Ready: {verify.get('zfs_ready', False)}")
        self.logger.info(f"   - System Healthy: {verify.get('system_healthy', False)}")
        
        # Save results to JSON
        results_file = f'/opt/github/Z-FORGE/ultrathink_results_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
        with open(results_file, 'w') as f:
            json.dump(self.results, f, indent=2, default=str)
        self.logger.info(f"\nFull results saved to: {results_file}")
        
        # Next steps if failed
        if not success:
            self.logger.info("\n⚠️  Manual intervention may be required:")
            self.logger.info("1. Check the log file for detailed errors")
            self.logger.info("2. Verify chroot environment exists and is accessible")
            self.logger.info("3. Ensure you have sudo privileges")
            self.logger.info("4. Try running individual fix scripts manually")

def main():
    """Main entry point"""
    print("╔═══════════════════════════════════════════════════════════╗")
    print("║          UltraThink Multi-Agent System v1.0               ║")
    print("║     Comprehensive Z-FORGE Kernel/ZFS Fix Solution         ║")
    print("╚═══════════════════════════════════════════════════════════╝")
    print()
    
    # Check prerequisites
    chroot_path = Path("/tmp/zforge_workspace/chroot")
    if not chroot_path.exists():
        print("❌ ERROR: Chroot environment not found at", chroot_path)
        print("Please ensure Z-FORGE build has created the chroot.")
        sys.exit(1)
        
    # Check sudo
    if os.geteuid() != 0:
        print("❌ ERROR: This script must be run with sudo")
        print("Please run: sudo python3", sys.argv[0])
        sys.exit(1)
        
    # Deploy the multi-agent system
    coordinator = UltraThinkCoordinator()
    
    try:
        coordinator.deploy_agents()
    except KeyboardInterrupt:
        print("\n⚠️  Process interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
        
    # Check final status
    if coordinator.results.get('verification', {}).get('system_healthy', False):
        print("\n✅ SUCCESS: System has been fixed!")
        sys.exit(0)
    else:
        print("\n❌ FAILED: Manual intervention required")
        sys.exit(1)

if __name__ == "__main__":
    main()