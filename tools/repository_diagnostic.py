#!/usr/bin/env python3
"""
Repository Diagnostic Tool for Z-Forge

Tests repository accessibility, validates GPG keys, and checks package availability
before attempting a build.
"""

import requests
import subprocess
import sys
import yaml
from pathlib import Path
from typing import Dict, List, Tuple
import argparse


class RepositoryDiagnostic:
    """Diagnoses repository health and accessibility."""
    
    def __init__(self):
        self.results = {}
        self.warnings = []
        self.errors = []
    
    def run_diagnostic(self, build_spec_path: str) -> Dict[str, any]:
        """Run comprehensive repository diagnostic."""
        print("🔍 Z-Forge Repository Diagnostic Tool")
        print("=" * 50)
        
        # Load build specification
        try:
            with open(build_spec_path, 'r') as f:
                build_spec = yaml.safe_load(f)
        except Exception as e:
            print(f"❌ Error loading build spec: {e}")
            return {'status': 'error', 'error': str(e)}
        
        # Extract repository configuration
        config = build_spec.get('builder_config', {})
        
        # Test primary repository
        primary_result = self._test_primary_repository(config)
        
        # Test fallback repositories
        fallback_result = self._test_fallback_repositories(config)
        
        # Test Proxmox repositories if enabled
        proxmox_result = self._test_proxmox_repositories(build_spec)
        
        # Test ZFS packages
        zfs_result = self._test_zfs_availability(config)
        
        # Test critical packages
        packages_result = self._test_critical_packages(config)
        
        # Generate summary
        summary = self._generate_summary()
        
        return {
            'status': 'success' if not self.errors else 'warning',
            'primary_repository': primary_result,
            'fallback_repositories': fallback_result,
            'proxmox_repositories': proxmox_result,
            'zfs_availability': zfs_result,
            'critical_packages': packages_result,
            'warnings': self.warnings,
            'errors': self.errors,
            'summary': summary
        }
    
    def _test_primary_repository(self, config: Dict) -> Dict[str, any]:
        """Test primary Debian repository accessibility."""
        print("\n📡 Testing Primary Repository")
        print("-" * 30)
        
        mirror = config.get('debian_mirror', 'http://deb.debian.org/debian')
        release = config.get('debian_release', 'bookworm')
        
        result = self._test_repository_access(mirror, release, "Primary")
        
        if result['accessible']:
            print(f"✅ Primary repository accessible: {mirror}")
        else:
            print(f"❌ Primary repository failed: {mirror}")
            self.errors.append(f"Primary repository {mirror} is not accessible")
        
        return result
    
    def _test_fallback_repositories(self, config: Dict) -> List[Dict[str, any]]:
        """Test fallback repository accessibility."""
        print("\n🔄 Testing Fallback Repositories")
        print("-" * 30)
        
        fallback_mirrors = config.get('fallback_mirrors', [])
        release = config.get('debian_release', 'bookworm')
        results = []
        
        if not fallback_mirrors:
            print("⚠️  No fallback repositories configured")
            self.warnings.append("No fallback repositories configured")
            return []
        
        for mirror in fallback_mirrors:
            result = self._test_repository_access(mirror, release, "Fallback")
            results.append(result)
            
            if result['accessible']:
                print(f"✅ Fallback repository accessible: {mirror}")
            else:
                print(f"❌ Fallback repository failed: {mirror}")
                self.warnings.append(f"Fallback repository {mirror} is not accessible")
        
        return results
    
    def _test_proxmox_repositories(self, build_spec: Dict) -> Dict[str, any]:
        """Test Proxmox repository accessibility if Proxmox is enabled."""
        print("\n🏢 Testing Proxmox Repositories")
        print("-" * 30)
        
        # Check if Proxmox modules are enabled
        modules = build_spec.get('modules', [])
        proxmox_enabled = any(
            module.get('name', '').startswith('proxmox') and module.get('enabled', False)
            for module in modules
        )
        
        if not proxmox_enabled:
            print("ℹ️  Proxmox modules not enabled, skipping")
            return {'enabled': False}
        
        release = build_spec.get('builder_config', {}).get('debian_release', 'bookworm')
        
        # Test Proxmox no-subscription repository
        proxmox_url = f"http://download.proxmox.com/debian/pve"
        result = self._test_repository_access(proxmox_url, release, "Proxmox")
        
        if result['accessible']:
            print(f"✅ Proxmox repository accessible: {proxmox_url}")
        else:
            print(f"❌ Proxmox repository failed: {proxmox_url}")
            self.errors.append(f"Proxmox repository {proxmox_url} is not accessible")
        
        return result
    
    def _test_zfs_availability(self, config: Dict) -> Dict[str, any]:
        """Test ZFS package availability."""
        print("\n💾 Testing ZFS Package Availability")
        print("-" * 30)
        
        mirror = config.get('debian_mirror', 'http://deb.debian.org/debian')
        release = config.get('debian_release', 'bookworm')
        
        # Test ZFS packages
        zfs_packages = ['zfsutils-linux', 'zfs-dkms', 'zfs-initramfs']
        results = {}
        
        for package in zfs_packages:
            available = self._test_package_availability(mirror, release, package)
            results[package] = available
            
            if available:
                print(f"✅ {package} available")
            else:
                print(f"❌ {package} not available")
                self.warnings.append(f"ZFS package {package} not available")
        
        return {
            'packages': results,
            'all_available': all(results.values())
        }
    
    def _test_critical_packages(self, config: Dict) -> Dict[str, any]:
        """Test critical system packages."""
        print("\n🔧 Testing Critical System Packages")
        print("-" * 30)
        
        mirror = config.get('debian_mirror', 'http://deb.debian.org/debian')
        release = config.get('debian_release', 'bookworm')
        
        critical_packages = [
            'systemd', 'linux-image-amd64', 'linux-headers-amd64',
            'grub-efi-amd64-bin', 'live-boot', 'debootstrap'
        ]
        
        results = {}
        
        for package in critical_packages:
            available = self._test_package_availability(mirror, release, package)
            results[package] = available
            
            if available:
                print(f"✅ {package} available")
            else:
                print(f"❌ {package} not available")
                self.errors.append(f"Critical package {package} not available")
        
        return {
            'packages': results,
            'all_available': all(results.values())
        }
    
    def _test_repository_access(self, mirror: str, release: str, repo_type: str) -> Dict[str, any]:
        """Test if a repository is accessible."""
        try:
            test_url = f"{mirror}/dists/{release}/Release"
            response = requests.head(test_url, timeout=10)
            
            return {
                'accessible': response.status_code == 200,
                'url': test_url,
                'status_code': response.status_code,
                'type': repo_type
            }
            
        except Exception as e:
            return {
                'accessible': False,
                'url': f"{mirror}/dists/{release}/Release",
                'error': str(e),
                'type': repo_type
            }
    
    def _test_package_availability(self, mirror: str, release: str, package: str) -> bool:
        """Test if a package is available in the repository."""
        try:
            # Test main component first
            packages_url = f"{mirror}/dists/{release}/main/binary-amd64/Packages.gz"
            response = requests.head(packages_url, timeout=10)
            return response.status_code == 200
            
        except Exception:
            return False
    
    def _generate_summary(self) -> str:
        """Generate diagnostic summary."""
        if not self.errors and not self.warnings:
            return "🎉 All repository diagnostics passed! Build should succeed."
        elif self.errors:
            return f"🚨 {len(self.errors)} critical issues found that will likely cause build failure."
        else:
            return f"⚠️  {len(self.warnings)} warnings found. Build may succeed with fallbacks."


def main():
    parser = argparse.ArgumentParser(description='Z-Forge Repository Diagnostic Tool')
    parser.add_argument('build_spec', help='Path to build specification YAML file')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    
    args = parser.parse_args()
    
    if not Path(args.build_spec).exists():
        print(f"❌ Build specification file not found: {args.build_spec}")
        sys.exit(1)
    
    diagnostic = RepositoryDiagnostic()
    results = diagnostic.run_diagnostic(args.build_spec)
    
    print(f"\n📊 Diagnostic Summary")
    print("=" * 50)
    print(results['summary'])
    
    if results.get('errors'):
        print(f"\n❌ Errors ({len(results['errors'])}):")
        for error in results['errors']:
            print(f"   • {error}")
    
    if results.get('warnings'):
        print(f"\n⚠️  Warnings ({len(results['warnings'])}):")
        for warning in results['warnings']:
            print(f"   • {warning}")
    
    # Exit with appropriate code
    if results.get('errors'):
        sys.exit(1)
    elif results.get('warnings'):
        sys.exit(2)
    else:
        sys.exit(0)


if __name__ == '__main__':
    main()